'use strict';
const {app, BrowserWindow, ipcMain, Menu, session} = require('electron');
const path = require('node:path');
const {parseTarget} = require('./target');

let dashboard = null;
let remote = null;
let currentAddress = '';
let status = '대기 중';

function emitStatus() {
  if (dashboard && !dashboard.isDestroyed()) {
    dashboard.webContents.send('yeon-admin:status-event', {
      status, address: currentAddress, connected: !!remote && !remote.isDestroyed()
    });
  }
}
function setStatus(value) {status = value; emitStatus();}

function closeRemote() {
  if (remote && !remote.isDestroyed()) remote.close();
  remote = null;
  currentAddress = '';
  setStatus('연결 종료됨');
}

function openController(address) {
  const safeAddress = parseTarget(address);
  closeRemote();
  currentAddress = safeAddress;
  remote = new BrowserWindow({
    width: 1360, height: 850, minWidth: 800, minHeight: 550,
    title: `YEON 원격 조정 · 관리자 · ${new URL(safeAddress).host}`,
    autoHideMenuBar: true,
    backgroundColor: '#0b1020',
    show: false,
    webPreferences: {
      nodeIntegration: false, contextIsolation: true, sandbox: true,
      webSecurity: true, devTools: false,
      javascript: true, webviewTag: false
    }
  });
  const opened = remote;
  const allowedOrigin = new URL(safeAddress).origin;

  // All web code is untrusted. It never receives Electron / OS APIs.
  opened.webContents.setWindowOpenHandler(() => ({action: 'deny'}));
  opened.webContents.on('will-navigate', (event, dest) => {
    try {
      if (new URL(dest).origin !== allowedOrigin) event.preventDefault();
    } catch { event.preventDefault(); }
  });
  opened.webContents.on('will-redirect', (event, dest) => {
    try {
      if (new URL(dest).origin !== allowedOrigin) event.preventDefault();
    } catch { event.preventDefault(); }
  });
  opened.webContents.on('did-finish-load', () => {
    if (remote === opened) setStatus('관리 대상 화면 열림 · 접속 코드를 입력하세요');
  });
  opened.on('closed', () => {
    if (remote !== opened) return;
    remote = null;
    currentAddress = '';
    setStatus('연결 종료됨');
  });
  opened.once('ready-to-show', () => opened.show());
  opened.show();
  setStatus('관리 대상 PC 연결 중…');

  opened.loadURL(safeAddress).catch(err => {
    if (remote !== opened) return;
    // The host must have explicitly started screen sharing before connection.
    opened.close();
    setStatus('연결 실패 · 관리 대상 PC에서 공유 시작을 눌렀는지 확인하세요');
  });
  return {ok: true, address: safeAddress};
}

function createDashboard() {
  dashboard = new BrowserWindow({
    width: 720, height: 700, minWidth: 590, minHeight: 580,
    title: 'YEON 원격 조정 - 관리자 v1.1.0',
    backgroundColor: '#0b1020',
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false, contextIsolation: true,
      sandbox: true, webSecurity: true, devTools: false
    }
  });
  dashboard.webContents.setWindowOpenHandler(() => ({action: 'deny'}));
  dashboard.webContents.on('will-navigate', (event) => event.preventDefault());
  dashboard.loadFile(path.join(__dirname, 'index.html'));
  dashboard.on('closed', () => {dashboard = null; closeRemote();});
}

app.whenReady().then(() => {
  Menu.setApplicationMenu(null);
  session.defaultSession.setPermissionRequestHandler((_wc, _permission, callback) => callback(false));
  ipcMain.handle('yeon-admin:connect', (_event, address) => {
    if (!_event.sender || _event.sender !== dashboard?.webContents) return {ok: false, error: '잘못된 요청입니다.'};
    try {return openController(address);}
    catch (err) {return {ok: false, error: err.message};}
  });
  ipcMain.handle('yeon-admin:disconnect', event => {
    if (event.sender !== dashboard?.webContents) return {ok:false};
    closeRemote(); return {ok: true};
  });
  ipcMain.handle('yeon-admin:status', event => {
    if (event.sender !== dashboard?.webContents) return null;
    return {status, address: currentAddress, connected: !!remote && !remote.isDestroyed()};
  });
  // Launching the EXE immediately opens the administrator software.
  createDashboard();
  app.on('activate', () => {if (BrowserWindow.getAllWindows().length === 0) createDashboard();});
});
app.on('window-all-closed', () => {if (process.platform !== 'darwin') app.quit();});
