const { ipcRenderer } = require('electron')

document.getElementById('loginBtn').onclick = () => {
  // Validate form if needed
  ipcRenderer.send('login-success')
}

document.getElementById('loginBtn').addEventListener('click', () => {
  const user = document.getElementById('username').value.trim()
  const pass = document.getElementById('password').value.trim()
  const error = document.getElementById('error')

  // Simple login check (for demo purposes)
  if (user === "admin" && pass === "admin") {
    window.location = "index.html"
  } else {
    error.textContent = "Invalid credentials. Please try again."
  }
})
