const { ipcRenderer } = require('electron')

const startBtn = document.getElementById('start')
const stopBtn = document.getElementById('stop')
const logoutBtn = document.getElementById('logoutBtn')
const logBox = document.getElementById('logBox')
const recordingStatus = document.getElementById('recordingStatus')
const timerDisplay = document.getElementById('timer')

let timerInterval = null
let startTime = null

startBtn.onclick = () => {
  ipcRenderer.send('start-backend')
}

ipcRenderer.on('backend-started', () => {
  clearLogDisplay()
  updateRecordingStatus(true)
  startTimer()
})

stopBtn.onclick = () => {
  ipcRenderer.send('stop-backend')
  updateRecordingStatus(false)
  stopTimer()
}

logoutBtn.onclick = () => {
  window.location.href = 'login.html'
}

ipcRenderer.on('log-update', (_, data) => {
  const span = document.createElement('span')
  span.classList.add('new-entry')
  span.textContent = data
  logBox.appendChild(span)
  logBox.appendChild(document.createElement('br'))
  logBox.scrollTop = logBox.scrollHeight
})


function clearLogDisplay() {
  logBox.textContent = ''
  timerDisplay.textContent = '00:00'
}

function updateRecordingStatus(running) {
  recordingStatus.textContent = running ? '🔴 Recording in progress' : '⏹ Not recording'
}

function startTimer() {
  startTime = Date.now()
  clearInterval(timerInterval)

  timerInterval = setInterval(() => {
    const elapsed = Math.floor((Date.now() - startTime) / 1000)
    const minutes = String(Math.floor(elapsed / 60)).padStart(2, '0')
    const seconds = String(elapsed % 60).padStart(2, '0')
    timerDisplay.textContent = `${minutes}:${seconds}`
  }, 1000)
}

function stopTimer() {
  clearInterval(timerInterval)
  timerDisplay.textContent = '00:00'
}
