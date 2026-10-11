'use strict';
const {app,BrowserWindow,ipcMain,net,shell}=require('electron');
const fs=require('node:fs'),path=require('node:path');
let win,localServer=null,baseURL=null,mode=null,checkTimer=null,checking=false;
const configFile=()=>path.join(app.getPath('userData'),'config.json');
function loadConfig(){try{return JSON.parse(fs.readFileSync(configFile(),'utf8'))}catch{return {}}}
function saveConfig(update){fs.mkdirSync(path.dirname(configFile()),{recursive:true});fs.writeFileSync(configFile(),JSON.stringify({...loadConfig(),...update},null,2))}
function normalizeUrl(value){
 try{const u=new URL(value);if(u.username||u.password||u.search||u.hash)return null;
 if(u.protocol!=='https:'&&!(u.protocol==='http:'&&['localhost','127.0.0.1'].includes(u.hostname)))return null;
 return u.origin}catch{return null}
}
const css=`*{box-sizing:border-box}body{margin:0;min-height:100vh;display:grid;place-items:center;background:#202127;color:#f6f6fc;font:16px system-ui,"Malgun Gothic",sans-serif}.panel{width:min(590px,92vw);text-align:center}h1{font-size:32px;margin:10px 0}p{color:#b8b9ca;line-height:1.6}button,input{font:inherit;border-radius:10px;padding:13px;border:0}button{background:#5865f2;color:white;font-weight:700;cursor:pointer;margin:6px;min-width:220px}button.secondary{background:#3e4050}input{width:100%;background:#12131a;border:1px solid #55596b;color:white;margin:10px 0}small{display:block;color:#aaaec1;margin:12px}#error{color:#ff9d9d}`;
const html=(content)=>'data:text/html;charset=utf-8,'+encodeURIComponent('<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>'+css+'</style>'+content+'</html>');
const selection=()=>html(`<div class="panel"><div style="font-size:52px;color:#9c96ff">✦</div><h1>YEON 메신저</h1><p>Veylo 서버 코드를 입력하면 채팅 화면으로 이동합니다.</p><input id="serverCode" type="password" placeholder="서버 코드를 입력해 주세요" autocomplete="off" aria-label="서버 코드"><button id="enter">메인 화면으로 이동</button><button id="view" class="secondary">서버 코드 보기 (Veylo 웹사이트)</button><p style="font-size:13px;color:#c0a882">*주의: 현재는 내 컴퓨터에 저장되는 시험용 채팅이며 다른 사람과 같이 있지 못함</p><p id="error" role="alert"></p></div><script>
const entry=document.getElementById('serverCode'), error=document.getElementById('error'), go=document.getElementById('enter');
async function submit(){go.disabled=true;error.textContent='';try{const result=await window.yeon.enterCode(entry.value);if(result?.error){error.textContent=result.error;go.disabled=false;}}catch(e){error.textContent='연결에 실패했습니다.';go.disabled=false}}
go.onclick=submit;
entry.onkeydown=e=>{if(e.key==='Enter')submit()};
document.getElementById('view').onclick=async()=>{try{await window.yeon.openVeylo()}catch{error.textContent='웹사이트를 열지 못했습니다.'}};
</script>`);
const offline=()=>html(`<div class="panel"><div style="font-size:100px">🌐<span style="color:#ff7171;margin-left:-35px">✕</span></div><h1>와이파이가 없습니다.</h1><p>인터넷 또는 채팅 서버에 연결할 수 없습니다.<br>공용 서버 주소와 연결 상태를 확인해 주세요.</p><button id="wifi">와이파이 설정하러 가기</button><button class="secondary" id="retry">다시 연결</button><button class="secondary" id="switch">서버 선택</button></div><script>document.getElementById('wifi').onclick=()=>window.yeon.openWifi();document.getElementById('retry').onclick=()=>window.yeon.retry();document.getElementById('switch').onclick=()=>window.yeon.showServers();</script>`);
function showSelection(){mode=null;baseURL=null;clearInterval(checkTimer);win.loadURL(selection())}
function showOffline(){if(win&&!win.isDestroyed()&&!win.webContents.getURL().startsWith('data:text/html'))win.loadURL(offline())}
async function ensureLocal(){
 if(localServer?.listening)return 'http://127.0.0.1:'+localServer.address().port;
 if(!localServer){process.env.YEON_DATA_FILE=path.join(app.getPath('userData'),'local-chat-data.json');localServer=require('./server')}
 if(!localServer.listening)await new Promise((resolve,reject)=>{const onError=e=>reject(e);localServer.once('error',onError);localServer.listen(0,'127.0.0.1',()=>{localServer.removeListener('error',onError);resolve()})});
 return 'http://127.0.0.1:'+localServer.address().port;
}
async function connect(choice,address){
 if(choice==='local'){baseURL=await ensureLocal();mode='local';saveConfig({mode:'local'})}
 else{
 const url=normalizeUrl(address);if(!url)return {error:'올바른 HTTPS 서버 주소를 입력하세요.'};
 baseURL=url;mode='cloud';saveConfig({mode:'cloud',serverUrl:url})
 }
 await check(true);clearInterval(checkTimer);checkTimer=setInterval(()=>check(false),10000);return {ok:true};
}
async function check(force=false){
 if(!baseURL||checking||!win||win.isDestroyed())return;
 checking=true;
 try{
  const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),4000);
  const response=await net.fetch(baseURL+'/api/health',{signal:controller.signal,cache:'no-store'}).finally(()=>clearTimeout(timeout));
  if(!response.ok)throw Error('Server unavailable');
  if(force||win.webContents.getURL().startsWith('data:text/html'))await win.loadURL(baseURL+'/');
 }catch{showOffline();if(force)await win.loadURL(offline())}finally{checking=false}
}
ipcMain.handle('choose-mode',async(_e,choice,address)=>{try{return await connect(choice,address)}catch(e){return {error:e.message}}});
ipcMain.on('yeon-window-double-click-quit',event=>{if(win&&event.sender===win.webContents)app.quit()});
ipcMain.handle('show-servers',()=>showSelection());
ipcMain.handle('enter-code',async(_event,code)=>{if(code!=='Veylo@Xk#Qp')return {error:'서버 코드가 올바르지 않습니다.'};try{const local=await ensureLocal();baseURL=local;mode='local';await check(true);return {ok:true}}catch(error){return {error:'채팅 화면을 시작하지 못했습니다: '+error.message}}});
ipcMain.handle('open-veylo',()=>shell.openPath(path.join(__dirname,'veylo','index.html')));
ipcMain.handle('retry-connection',()=>check(true));
ipcMain.handle('open-wifi-settings',()=>shell.openExternal(process.platform==='win32'?'ms-settings:network-wifi':'https://support.microsoft.com/windows'));
app.whenReady().then(async()=>{
 win=new BrowserWindow({width:1280,height:820,minWidth:760,minHeight:540,title:'YEON Messenger',backgroundColor:'#202127',webPreferences:{contextIsolation:true,nodeIntegration:false,sandbox:true,preload:path.join(__dirname,'preload.js')}});
 win.webContents.setWindowOpenHandler(()=>({action:'deny'}));
 win.webContents.on('will-navigate',(e,target)=>{if(!target.startsWith('data:text/html')&&!(baseURL&&target.startsWith(baseURL+'/')))e.preventDefault()});
 win.webContents.on('did-fail-load',(_e,_code,_desc,url,isMainFrame)=>{if(isMainFrame&&baseURL&&url.startsWith(baseURL))showOffline()});
 showSelection();
});
app.on('before-quit',()=>{clearInterval(checkTimer);localServer?.close()});
app.on('window-all-closed',()=>app.quit());
