/****************************************************************
 * main.js — Electron main process
 ****************************************************************/

const path = require('path');
const fs   = require('fs');
const { app, BrowserWindow, ipcMain } = require('electron');
const { spawn } = require('child_process');

/* ─── 0. DEV HOT-RELOAD (ignore runtime logs) ─────────────── */
require('electron-reload')(
  __dirname,
  {
    electron: require(path.join(__dirname, 'node_modules', 'electron')),
    watchRenderer: true,

    // ⬇️  Stop reloads when backend writes to the log
    ignored: [
      /log\.txt$/,            // root-level log
      /backend\/.*\.log$/,    // any *.log inside backend/
    ]
  }
);

/* ─── GLOBAL STATE ────────────────────────────────────────── */
let loginWin   = null;
let dashWin    = null;
let pyProc     = null;
let logWatcher = null;
let logOffset  = 0;
const logPath  = path.join(__dirname, 'log.txt');

/* ─── 1. CREATE LOGIN WINDOW ──────────────────────────────── */
function createLoginWindow () {
  loginWin = new BrowserWindow({
    width: 600,
    height: 400,
    resizable: false,
    webPreferences: { nodeIntegration: true, contextIsolation: false }
  });

  loginWin.loadFile('renderer/login.html');

  ipcMain.once('login-success', () => {
    loginWin.close();
    createDashboardWindow();
  });
}

/* ─── 2. CREATE DASHBOARD WINDOW ──────────────────────────── */
function createDashboardWindow () {
  dashWin = new BrowserWindow({
    width: 1400,
    height: 900,
    x: 100,
    y: 50,
    webPreferences: { nodeIntegration: true, contextIsolation: false }
  });

  dashWin.loadFile('renderer/index.html');
}

/* ─── 3. APP READY ───────────────────────────────────────── */
app.whenReady().then(createLoginWindow);

/* ─── 4. BACKEND CONTROL ─────────────────────────────────── */
ipcMain.on('start-backend', () => {
  if (pyProc) return;                       // Already running?

  fs.writeFileSync(logPath, '');            // Clear previous logs
  logOffset = 0;

  pyProc = spawn('python3', ['backend/test.py'], { cwd: __dirname });

  pyProc.on('spawn', () => {
    // Small delay so the Python app is really up
    setTimeout(() => dashWin.webContents.send('backend-started'), 800);
  });

  pyProc.on('exit', () => { pyProc = null; });

  logWatcher = fs.watchFile(
    logPath,
    { interval: 500 },
    (curr, prev) => {
      if (curr.size <= prev.size) return;   // Nothing new
      const stream = fs.createReadStream(logPath, { start: logOffset, end: curr.size });
      let buf = '';
      stream.on('data', chunk => (buf += chunk.toString()));
      stream.on('end', () => {
        logOffset = curr.size;
        buf.split('\n')
           .filter(Boolean)
           .forEach(line => dashWin.webContents.send('log-update', line));
      });
    }
  );
});

ipcMain.on('stop-backend', () => {
  if (pyProc) { pyProc.kill('SIGTERM'); pyProc = null; }
  if (logWatcher) { fs.unwatchFile(logPath); logWatcher = null; }
});

/* ─── 5. CLEAN-UP ON EXIT ───────────────────────────────── */
app.on('window-all-closed', () => {
  if (pyProc) pyProc.kill();
  if (logWatcher) fs.unwatchFile(logPath);
  if (process.platform !== 'darwin') app.quit();
});
