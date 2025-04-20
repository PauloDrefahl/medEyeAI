import time
import cv2
import torch
import threading
import queue
from transformers import CLIPProcessor, CLIPModel

# ─── 1) Configuration ────────────────────────────────────────────────
DEVICE          = "mps" if torch.backends.mps.is_available() else "cpu"
MODEL_NAME      = "laion/CLIP-ViT-H-14-laion2B-s32B-b79K"
UPDATE_INTERVAL = 3               # seconds between inferences
INPUT_SIZE      = (224, 224)        # CLIP’s expected input size
THRESHOLD       = 0.20              # cosine‑sim cutoff for fallback
FALLBACK_LABEL  = "unrecognized action"
LOG_FILE        = "log.txt"

# ─── 2) Load CLIP + processor ────────────────────────────────────────
model     = CLIPModel.from_pretrained(MODEL_NAME).to(DEVICE)
processor = CLIPProcessor.from_pretrained(MODEL_NAME)

# ─── 3) Labels ───────────────────────────────────────────────────────
labels = [
    "Physician placing defibrillator paddles on chest",
    "Physician leaning over and checking neck pulse",
    "Physician performing chest compressions with both hands",
    "Physician inserting IV needle in patient’s arm",
    "Physician placing mask over patient face and squeezing bag"
]


# Precompute & normalize text embeddings once
with torch.no_grad():
    txt_inputs = processor(text=labels, return_tensors="pt", padding=True).to(DEVICE)
    text_embs  = model.get_text_features(**txt_inputs)
    text_embs  = text_embs / text_embs.norm(p=2, dim=-1, keepdim=True)

# ─── 4) Threaded inference setup ──────────────────────────────────────
frame_q = queue.Queue(maxsize=1)
desc_q  = queue.Queue(maxsize=1)
stop_ev = threading.Event()

def inference_worker():
    while not stop_ev.is_set():
        try:
            frame = frame_q.get(timeout=0.1)
        except queue.Empty:
            continue

        # Downsample & convert to RGB
        small = cv2.resize(frame, INPUT_SIZE, interpolation=cv2.INTER_AREA)
        rgb   = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)

        # zero‑shot CLIP
        inputs = processor(images=rgb, return_tensors="pt").to(DEVICE)
        with torch.no_grad():
            img_emb = model.get_image_features(**inputs)
            img_emb = img_emb / img_emb.norm(p=2, dim=-1, keepdim=True)
            sims    = (img_emb @ text_embs.T).squeeze(0)

            best_idx = sims.argmax().item()
            max_sim  = sims[best_idx].item()

            # debug: print out which label and its similarity
            print(f"[DEBUG] best='{labels[best_idx]}', sim={max_sim:.3f}")

            desc = labels[best_idx] if max_sim >= THRESHOLD else FALLBACK_LABEL

        # update latest description
        if not desc_q.empty():
            try: desc_q.get_nowait()
            except queue.Empty: pass
        desc_q.put(desc)

thread = threading.Thread(target=inference_worker, daemon=True)
thread.start()

# ─── 5) Main capture loop ────────────────────────────────────────────
cap          = cv2.VideoCapture(0)
last_push    = 0.0
current_desc = FALLBACK_LABEL
start_time   = time.time()

# Clear previous log
open(LOG_FILE, "w").close()

if not cap.isOpened():
    raise RuntimeError("Cannot open camera")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    now = time.time()
    # throttle inference submits
    if now - last_push > UPDATE_INTERVAL and frame_q.empty():
        frame_q.put(frame)
        last_push = now

    # fetch new desc if available
    try:
        current_desc = desc_q.get_nowait()

        # log if not fallback
        if current_desc != FALLBACK_LABEL:
            elapsed = time.time() - start_time
            with open(LOG_FILE, "a") as f:
                f.write(f"{elapsed:.1f}s: {current_desc}\n")

    except queue.Empty:
        pass

    # overlay & display
    cv2.putText(frame, current_desc, (10,30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                (255,255,255), 2, cv2.LINE_AA)
    cv2.imshow("MedEye by Paulo Drefahl", frame)

    if cv2.waitKey(1) & 0xFF in (27, ord('q')):
        break

# ─── 6) Cleanup ──────────────────────────────────────────────────────
stop_ev.set()
thread.join()
cap.release()
cv2.destroyAllWindows()
