'use strict';
const {app, BrowserWindow, ipcMain, Menu, session, desktopCapturer} = require('electron');
const path = require('node:path');
const {parseTarget} = require('./target');
const {FocusSender, send, cookieForSession} = require('./focus_transport');

let dashboard = null;
let remote = null;
let currentAddress = '';
let status = '대기 중';
let focusSender = null;

function emitStatus() {
  if (dashboard && !dashboard.isDestroyed()) {
    dashboard.webContents.send('yeon-admin:status-event', {
      status, address: currentAddress, connected: !!remote && !remote.isDestroyed()
    });
  }
}
function setStatus(value) {status = value; emitStatus();}

function closeRemote() {
  if (focusSender) void focusSender.stop();
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
    title: 'YEON 원격 조정 - 관리자 v1.3.1',
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
  dashboard.on('closed', () => {if(focusSender) void focusSender.stop(); dashboard = null; closeRemote();});
}

app.whenReady().then(() => {
  Menu.setApplicationMenu(null);
  session.defaultSession.setPermissionRequestHandler((_wc, _permission, callback) => callback(false));
  focusSender = new FocusSender({
    electronSession: session.defaultSession, desktopCapturer,
    onStatus: (message) => setStatus(message)
  });
  ipcMain.handle('yeon-admin:focus-start', async (event) => {
    if (event.sender !== dashboard?.webContents) return {ok:false, error:'잘못된 요청입니다.'};
    if (!currentAddress) return {ok:false,error:'먼저 관리 대상 PC에 연결하세요.'};
    if (focusSender.active) return {ok:false,error:'이미 집중 화면을 전송하고 있습니다.'};
    const address = currentAddress;
    // Do not hold up the user-interface response for a full streaming session.
    void focusSender.start(address).catch(error => setStatus(`집중 모드: ${error.message}`));
    return {ok:true};
  });
  ipcMain.handle('yeon-admin:focus-stop', async event => {
    if (event.sender !== dashboard?.webContents) return {ok:false};
    await focusSender.stop(); setStatus('집중 화면 전송 종료됨');
    return {ok:true};
  });
  ipcMain.handle('yeon-admin:control-permission', async event => {
    if (event.sender !== dashboard?.webContents || !currentAddress) return {ok:false};
    try {
      const cookie = await cookieForSession(session.defaultSession, currentAddress);
      const info = await send(currentAddress, '/api/status', {method:'GET', cookie});
      return {ok:true, enabled:info.remoteControlEnabled === true};
    } catch { return {ok:false}; }
  });
  ipcMain.handle('yeon-admin:remote-mode', async event => {
    if (event.sender !== dashboard?.webContents) return {ok:false};
    if (!currentAddress) return {ok:false,error:'관리 대상 PC에 먼저 연결하세요.'};
    await focusSender.stop();
    try {
      const cookie = await cookieForSession(session.defaultSession, currentAddress);
      const info = await send(currentAddress, '/api/status', {method:'GET', cookie});
      if (!info.remoteControlEnabled) return {ok:false,error:'관리 대상 PC에서 원격 제어가 OFF입니다. 관리 대상에서 ON으로 변경하세요.'};
    } catch (error) { return {ok:false,error:error.message}; }
    if (remote && !remote.isDestroyed()) {remote.show();remote.focus();}
    setStatus('원격 제어 ON · 관리 대상 PC에서 허용함');
    return {ok:true};
  });
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
