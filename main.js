require('electron-reload')(__dirname, {
    electron: require(`${__dirname}/node_modules/electron`),
    watchRenderer: true
  })
  
  const { app, BrowserWindow, ipcMain } = require('electron')
  const path = require('path')
  const fs = require('fs')
  const { spawn } = require('child_process')
  
  let win = null
  let pyProc = null
  let logWatcher = null
  let logOffset = 0
  
  function createWindow() {
    win = new BrowserWindow({
      width: 900,
      height: 900,
      webPreferences: {
        nodeIntegration: true,
        contextIsolation: false
      }
    })
  
    win.loadFile('renderer/login.html')
  }
  
  app.whenReady().then(createWindow)
  
  ipcMain.on('start-backend', () => {
    if (!pyProc) {
      const logPath = path.join(__dirname, 'log.txt')
      fs.writeFileSync(logPath, '') // Clear file
      logOffset = 0
  
      pyProc = spawn('python3', ['backend/medeye.py'], { cwd: __dirname })
  
      pyProc.on('spawn', () => {
        setTimeout(() => {
          win.webContents.send('backend-started') // Wait a moment for camera init
        }, 800) // Give the camera popup + Python init time
      })
  
      pyProc.on('exit', () => {
        pyProc = null
      })
  
      logWatcher = fs.watchFile(logPath, { interval: 500 }, (curr, prev) => {
        if (curr.size > prev.size) {
          const stream = fs.createReadStream(logPath, {
            start: logOffset,
            end: curr.size
          })
  
          let newData = ''
          stream.on('data', chunk => newData += chunk.toString())
          stream.on('end', () => {
            logOffset = curr.size
            const lines = newData.split('\n').filter(Boolean)
            lines.forEach(line => {
              win.webContents.send('log-update', line)
            })
          })
        }
      })
    }
  })
  
  ipcMain.on('stop-backend', () => {
    if (pyProc) {
      pyProc.kill('SIGTERM')
      pyProc = null
    }
  
    if (logWatcher) {
      fs.unwatchFile(path.join(__dirname, 'log.txt'))
      logWatcher = null
    }
  })
  
  app.on('window-all-closed', () => {
    if (pyProc) pyProc.kill()
    if (logWatcher) fs.unwatchFile(path.join(__dirname, 'log.txt'))
    if (process.platform !== 'darwin') app.quit()
  })
  