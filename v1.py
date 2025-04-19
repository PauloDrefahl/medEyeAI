import cv2
import torch
import threading
import queue
from transformers import CLIPProcessor, CLIPModel

# ─── Setup CLIP on MPS/CPU ───────────────────────────────────────────
device    = "mps" if torch.backends.mps.is_available() else "cpu"
model     = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").to(device)
processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")

# ─── Your three nearly‑identical labels ──────────────────────────────
labels = [
    "Physician administering defibrillation shock",
    "Physician checking patient pulse and responsiveness",
    "Physician performing chest compressions",
    "Physician staff establishing intravenous access",
    "Physician provider using bag valve mask ventilation",
    "None of the options"
]

# Precompute & normalize text features
with torch.no_grad():
    txt_feats = processor(text=labels, return_tensors="pt", padding=True).to(device)
    text_embs = model.get_text_features(**txt_feats)
    text_embs = text_embs / text_embs.norm(p=2, dim=-1, keepdim=True)

# ─── Queues & threading ─────────────────────────────────────────────
frame_q = queue.Queue(maxsize=1)
desc_q  = queue.Queue(maxsize=1)
stop_ev = threading.Event()

def inference_worker():
    while not stop_ev.is_set():
        try:
            frame = frame_q.get(timeout=0.1)
        except queue.Empty:
            continue

        # down to 224×224 & RGB
        small = cv2.resize(frame, (224, 224), interpolation=cv2.INTER_AREA)
        rgb   = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)

        inputs = processor(images=rgb, return_tensors="pt").to(device)
        with torch.no_grad():
            img_emb = model.get_image_features(**inputs)
            img_emb = img_emb / img_emb.norm(p=2, dim=-1, keepdim=True)
            sims    = (img_emb @ text_embs.T).squeeze(0)
            best    = sims.argmax().item()
            desc    = labels[best]

        if not desc_q.empty():
            desc_q.get()
        desc_q.put(desc)

thread = threading.Thread(target=inference_worker, daemon=True)
thread.start()

# ─── Main capture & display ─────────────────────────────────────────
cap         = cv2.VideoCapture(0)
description = labels[0]

if not cap.isOpened():
    raise RuntimeError("Cannot open camera")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    if frame_q.empty():
        frame_q.put(frame)

    try:
        description = desc_q.get_nowait()
    except queue.Empty:
        pass

    cv2.putText(frame, description, (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0,
                (255, 255, 255), 2, cv2.LINE_AA)
    cv2.imshow("Smooth Description Variations", frame)

    if cv2.waitKey(1) & 0xFF in (27, ord('q')):
        break

# ─── Cleanup ────────────────────────────────────────────────────────
stop_ev.set()
thread.join()
cap.release()
cv2.destroyAllWindows()
