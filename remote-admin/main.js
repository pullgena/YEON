'use strict';
const {app, BrowserWindow, ipcMain, Menu, Tray, session, desktopCapturer} = require('electron');
const path = require('node:path');
const fs = require('node:fs');
const {parseTarget} = require('./target');
const {cleanList, remember, forget} = require('./computers');
const {FocusSender, send, cookieForSession} = require('./focus_transport');

const VERSION = '1.3.4';
let dashboard = null;
let remote = null;
let tray = null;
let currentAddress = '';
let status = '대기 중';
let focusSender = null;
let quitting = false;
let computers = [];

function configPath() {return path.join(app.getPath('userData'), 'managed-computers.json');}
function loadComputers() {
  try {computers = cleanList(JSON.parse(fs.readFileSync(configPath(), 'utf8')));} catch {computers = [];}
}
function saveComputers() {
  try {
    fs.mkdirSync(path.dirname(configPath()), {recursive:true});
    fs.writeFileSync(configPath(), JSON.stringify(computers), {encoding:'utf8', mode:0o600});
  } catch { /* A read-only profile must not prevent screen sharing. */ }
}
function emitStatus() {
  if (dashboard && !dashboard.isDestroyed()) {
    dashboard.webContents.send('yeon-admin:status-event', {
      status, address:currentAddress, connected:!!remote && !remote.isDestroyed(),
      computers:computers.map(({address,name}) => ({address,name}))
    });
  }
  if (tray && !tray.isDestroyed()) tray.setToolTip(`YEON 원격 조정 관리자 · ${status}`.slice(0, 125));
}
function setStatus(value) {status = value; emitStatus();}
function rememberAddress(address, name) {
  computers = remember(computers, address, name);
  saveComputers();
  emitStatus();
}
function showDashboard() {
  if (!dashboard || dashboard.isDestroyed()) createDashboard();
  dashboard.show();
  if (dashboard.isMinimized()) dashboard.restore();
  dashboard.focus();
}
function showRemote() {
  if (remote && !remote.isDestroyed()) {remote.show();remote.focus();}
  else showDashboard();
}
function closeRemote() {
  if (currentAddress) {
    const address = currentAddress;
    void cookieForSession(session.defaultSession, address)
      .then(cookie => send(address, '/api/control', {cookie, bytes:Buffer.from('{"enabled":false}')}))
      .catch(() => {});
  }
  if (focusSender) void focusSender.stop();
  const opened = remote;
  remote = null;
  currentAddress = '';
  if (opened && !opened.isDestroyed()) opened.close();
  setStatus('연결 종료됨');
}

function openController(address) {
  const safeAddress = parseTarget(address);
  if (safeAddress === currentAddress && remote && !remote.isDestroyed()) {
    showRemote();
    return {ok:true,address:safeAddress};
  }
  closeRemote();
  currentAddress = safeAddress;
  rememberAddress(safeAddress);
  remote = new BrowserWindow({
    width:1360, height:850, minWidth:800, minHeight:550,
    title:`YEON 원격 조정 · ${new URL(safeAddress).host}`,
    autoHideMenuBar:true, backgroundColor:'#0b1020', show:false,
    webPreferences:{
      nodeIntegration:false, contextIsolation:true, sandbox:true,
      webSecurity:true, devTools:false, javascript:true, webviewTag:false
    }
  });
  const opened = remote;
  const allowedOrigin = new URL(safeAddress).origin;
  opened.webContents.setWindowOpenHandler(() => ({action:'deny'}));
  opened.webContents.on('will-navigate', (event,dest) => {
    try {if (new URL(dest).origin !== allowedOrigin) event.preventDefault();}
    catch {event.preventDefault();}
  });
  opened.webContents.on('will-redirect', (event,dest) => {
    try {if (new URL(dest).origin !== allowedOrigin) event.preventDefault();}
    catch {event.preventDefault();}
  });
  opened.webContents.on('did-finish-load', () => {
    if (remote === opened) setStatus('대상 PC 화면 열림 · 8자리 접속 코드를 입력하세요');
  });
  opened.on('closed', () => {
    if (remote !== opened) return;
    closeRemote();
  });
  opened.once('ready-to-show', () => opened.show());
  opened.show();
  setStatus('관리 대상 PC 연결 중…');
  opened.loadURL(safeAddress).catch(() => {
    if (remote !== opened) return;
    closeRemote();
    setStatus('연결 실패 · 관리 대상 PC에서 공유 시작을 눌렀는지 확인하세요');
  });
  return {ok:true,address:safeAddress};
}

function createDashboard() {
  dashboard = new BrowserWindow({
    width:1010,height:740,minWidth:770,minHeight:640,
    title:`YEON 원격 조정 - 관리자 v${VERSION}`,
    backgroundColor:'#0b1020',autoHideMenuBar:true,
    webPreferences:{preload:path.join(__dirname,'preload.js'),nodeIntegration:false,
      contextIsolation:true,sandbox:true,webSecurity:true,devTools:false}
  });
  dashboard.webContents.setWindowOpenHandler(() => ({action:'deny'}));
  dashboard.webContents.on('will-navigate', event => event.preventDefault());
  dashboard.loadFile(path.join(__dirname,'index.html'));
  dashboard.on('close', event => {
    if (!quitting && tray && !tray.isDestroyed()) {
      event.preventDefault(); dashboard.hide();
    }
  });
  dashboard.on('closed', () => {dashboard = null;});
}
function updateTrayMenu() {
  if (!tray || tray.isDestroyed()) return;
  tray.setContextMenu(Menu.buildFromTemplate([
    {label:'관리자 창 열기',click:showDashboard},
    {label:'연결된 컴퓨터 화면 열기',enabled:!!currentAddress,click:showRemote},
    {label:'집중 화면 전송 중지',enabled:!!focusSender?.active,click:()=>{void focusSender.stop();}},
    {label:'현재 원격 연결 종료',enabled:!!currentAddress,click:closeRemote},
    {type:'separator'},
    {label:'YEON 원격 조정 완전 종료',click:quitApp}
  ]));
}
function quitApp() {
  if (quitting) return;
  quitting = true;
  closeRemote();
  if (tray && !tray.isDestroyed()) tray.destroy();
  tray = null;
  app.quit();
}
async function updateComputerName() {
  const address = currentAddress;
  if (!address) return;
  try {
    const cookie = await cookieForSession(session.defaultSession, address);
    const info = await send(address, '/api/status', {method:'GET',cookie});
    if (currentAddress !== address || !info.authorized) return;
    if (typeof info.computerName === 'string' && info.computerName.trim() &&
        computers.find(item => item.address === address)?.name !== info.computerName.trim())
      rememberAddress(address, info.computerName);
  } catch { /* Not authenticated yet, or offline: retain last known computer name. */ }
}

if (!app.requestSingleInstanceLock()) {
  app.quit();
} else {
  app.on('second-instance', showDashboard);
  app.whenReady().then(() => {
    Menu.setApplicationMenu(null);
    loadComputers();
    session.defaultSession.setPermissionRequestHandler((_wc,_permission,callback)=>callback(false));
    tray = new Tray(path.join(__dirname,'assets','yeon-admin.ico'));
    tray.on('double-click', showDashboard);
    tray.on('click', showDashboard);
    focusSender = new FocusSender({electronSession:session.defaultSession,desktopCapturer,
      onStatus: message => {setStatus(message);updateTrayMenu();}});

    const valid = event => event.sender === dashboard?.webContents;
    ipcMain.handle('yeon-admin:focus-start',async event => {
      if (!valid(event)) return {ok:false,error:'잘못된 요청입니다.'};
      if (!currentAddress) return {ok:false,error:'먼저 대상 PC에 연결하세요.'};
      if (focusSender.active) return {ok:false,error:'이미 집중 화면 전송 중입니다.'};
      const address = currentAddress;
      void focusSender.start(address).catch(error => setStatus(`집중 모드: ${error.message}`))
        .finally(updateTrayMenu);
      updateTrayMenu();
      return {ok:true};
    });
    ipcMain.handle('yeon-admin:focus-stop',async event => {
      if (!valid(event)) return {ok:false};
      await focusSender.stop();setStatus('집중 화면 전송 종료됨');updateTrayMenu();return {ok:true};
    });
    ipcMain.handle('yeon-admin:control-permission',async event => {
      if (!valid(event) || !currentAddress) return {ok:false};
      try {
        const cookie=await cookieForSession(session.defaultSession,currentAddress);
        const info=await send(currentAddress,'/api/status',{method:'GET',cookie});
        return {ok:true,enabled:info.remoteControlEnabled===true};
      } catch {return {ok:false};}
    });
    ipcMain.handle('yeon-admin:control-set',async(event,enabled)=>{
      if (!valid(event)||!currentAddress) return {ok:false,error:'먼저 PC에 연결하세요.'};
      if(typeof enabled!=='boolean') return {ok:false,error:'ON/OFF 값을 확인하세요.'};
      try {
        const cookie=await cookieForSession(session.defaultSession,currentAddress);
        const info=await send(currentAddress,'/api/control',{
          cookie,bytes:Buffer.from(JSON.stringify({enabled}))
        });
        setStatus(enabled?'원격 제어 ON · 마우스·키보드 사용 가능':'원격 제어 OFF · 화면만 보기');
        return {ok:true,enabled:info.remoteControlEnabled===true};
      } catch(error){return {ok:false,error:error.message};}
    });
    ipcMain.handle('yeon-admin:remote-mode',async event=>{
      if(!valid(event))return {ok:false};
      if(!currentAddress)return {ok:false,error:'관리 대상 PC에 먼저 연결하세요.'};
      await focusSender.stop();
      try {
        const cookie=await cookieForSession(session.defaultSession,currentAddress);
        const info=await send(currentAddress,'/api/status',{method:'GET',cookie});
        if(!info.remoteControlEnabled)return {ok:false,error:'원격 제어 OFF입니다. 관리자에서 ON을 누르세요.'};
      } catch(error){return {ok:false,error:error.message};}
      showRemote();setStatus('원격 제어 창 열림');updateTrayMenu();return {ok:true};
    });
    ipcMain.handle('yeon-admin:connect',(event,address)=>{
      if(!valid(event))return {ok:false,error:'잘못된 요청입니다.'};
      try {const result=openController(address);updateTrayMenu();return result;}
      catch(error){return {ok:false,error:error.message};}
    });
    ipcMain.handle('yeon-admin:disconnect',event=>{
      if(!valid(event))return {ok:false};closeRemote();updateTrayMenu();return {ok:true};
    });
    ipcMain.handle('yeon-admin:computers',event=>valid(event)?computers:[]);
    ipcMain.handle('yeon-admin:computer-remove',(event,address)=>{
      if(!valid(event))return {ok:false};
      try {
        const safe=parseTarget(address);
        if(safe===currentAddress)closeRemote();
        computers=forget(computers,safe);saveComputers();emitStatus();updateTrayMenu();return {ok:true};
      } catch(error){return {ok:false,error:error.message};}
    });
    ipcMain.handle('yeon-admin:status',event=>valid(event)?{
      status,address:currentAddress,connected:!!remote&&!remote.isDestroyed(),computers
    }:null);
    createDashboard();
    updateTrayMenu();
    setInterval(()=>{if(currentAddress)void updateComputerName();updateTrayMenu();},3500).unref();
    app.on('activate', showDashboard);
  });
  app.on('window-all-closed', () => { /* Tray is the visible background control. */ });
}
