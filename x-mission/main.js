'use strict';
const {app, BrowserWindow, ipcMain} = require('electron');
const path = require('node:path');
let windowRef;

function createWindow() {
  windowRef = new BrowserWindow({
    width: 1200, height: 780, minWidth: 680, minHeight: 400,
    frame: false, backgroundColor: '#ffffff', title: 'YEON X Mission',
    webPreferences: {preload: path.join(__dirname, 'preload.js'), contextIsolation: true, nodeIntegration: false, sandbox: true}
  });
  windowRef.loadFile('index.html');
}
app.whenReady().then(() => {
  ipcMain.on('close-window', event => BrowserWindow.fromWebContents(event.sender)?.close());
  ipcMain.on('minimize-window', event => BrowserWindow.fromWebContents(event.sender)?.minimize());
  ipcMain.on('toggle-maximize-window', event => {
    const win = BrowserWindow.fromWebContents(event.sender);
    if (win) win.isMaximized() ? win.unmaximize() : win.maximize();
  });
  createWindow();
  app.on('activate', () => {if (BrowserWindow.getAllWindows().length === 0) createWindow();});
});
app.on('window-all-closed', () => {if (process.platform !== 'darwin') app.quit();});
