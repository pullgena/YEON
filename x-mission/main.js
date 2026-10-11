'use strict';
const {app, BrowserWindow, ipcMain} = require('electron');
const path = require('node:path');
let windowRef;
let allowExit = false;
function createWindow() {
  windowRef = new BrowserWindow({
    width: 1200, height: 780, minWidth: 680, minHeight: 400,
    frame: false, backgroundColor: '#ffffff', title: 'YEON X Mission',
    webPreferences: {preload: path.join(__dirname, 'preload.js'), contextIsolation: true, nodeIntegration: false, sandbox: true}
  });
  windowRef.loadFile('index.html');
  windowRef.webContents.on('before-input-event', (event, input) => {
    if (input.type === 'keyDown' && input.control && input.shift && input.key.toLowerCase() === 'q') {
      event.preventDefault();
      allowExit = true;
      windowRef.close();
    }
  });
  windowRef.on('close', event => {
    if (!allowExit && !windowRef.isDestroyed()) {
      event.preventDefault();
      windowRef.webContents.send('show-mission');
      if (windowRef.isMinimized()) windowRef.restore();
      windowRef.focus();
    }
  });
}
app.whenReady().then(() => {
  ipcMain.on('minimize-window', event => BrowserWindow.fromWebContents(event.sender)?.minimize());
  ipcMain.on('toggle-maximize-window', event => {
    const win = BrowserWindow.fromWebContents(event.sender);
    if (win) win.isMaximized() ? win.unmaximize() : win.maximize();
  });
  createWindow();
  app.on('activate', () => {if (BrowserWindow.getAllWindows().length === 0) createWindow();});
});
app.on('window-all-closed', () => {if (process.platform !== 'darwin') app.quit();});
