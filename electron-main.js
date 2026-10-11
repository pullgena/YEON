const {app,BrowserWindow,dialog,ipcMain,net,shell}=require('electron');
const fs=require('node:fs'),path=require('node:path');
let win,serverUrl=null,offline=false,timer,loaded=false;
function configPath(){return path.join(app.getPath('userData'),'config.json')}
function isSafeURL(value){try{const u=new URL(value);return u.protocol==='https:'||(u.protocol==='http:'&&['localhost','127.0.0.1'].includes(u.hostname))}catch{return false}}
async function chooseServer(){
 let configured=process.env.YEON_SERVER_URL||'';
 try{configured=configured||JSON.parse(fs.readFileSync(configPath(),'utf8')).serverUrl}catch{}
 if(!configured){await dialog.showMessageBox({title:'YEON 서버 연결',message:'채팅 서버 주소가 필요합니다.',detail:'%APPDATA%\\YEON\\config.json에 {"serverUrl":"https://your-server.example"} 형식으로 서버 주소를 지정해 주세요.',buttons:['확인']});return null}
 return isSafeURL(configured)?new URL(configured).origin:null;
}
const offlineHTML=`<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>*{box-sizing:border-box}body{margin:0;min-height:100vh;background:#202127;color:#f5f6fc;display:grid;place-items:center;text-align:center;font-family:system-ui,"Malgun Gothic",sans-serif}.globe{position:relative;margin:auto auto 25px;font-size:100px;line-height:1.2;color:#b6bbd1}.x{position:absolute;right:-12px;bottom:5px;font-size:51px;color:#fa6868;font-weight:900;text-shadow:0 1px 10px #0008}h1{font-size:36px;margin:0 0 12px}p{color:#aaaec3;font-size:16px;margin:0 0 28px}button{display:block;margin:12px auto 0;min-width:255px;padding:15px 20px;border:0;border-radius:10px;background:#5865f2;color:white;font-size:16px;font-weight:700;cursor:pointer}button.secondary{background:#37394a}small{display:block;color:#969bad;margin-top:28px}button:hover{filter:brightness(1.12)}</style><div><div class="globe" aria-label="인터넷 연결 없음">🌐<span class="x">✕</span></div><h1>와이파이가 없습니다.</h1><p>인터넷 연결을 확인한 후 다시 시도해 주세요.</p><button id="wifi">와이파이 설정하러 가기</button><button id="retry" class="secondary">다시 연결</button><small>Windows Wi-Fi 설정을 엽니다.</small></div><script>document.getElementById('wifi').onclick=()=>window.yeon.openWifi();document.getElementById('retry').onclick=()=>window.yeon.retry();<\/script></html>`;
function showOffline(){if(!win||win.isDestroyed()||offline)return;offline=true;win.loadURL('data:text/html;charset=utf-8,'+encodeURIComponent(offlineHTML))}
async function checkConnection(){
 if(!win||win.isDestroyed()||!serverUrl)return;
 if(!net.isOnline()){showOffline();return}
 try{const controller=new AbortController();const timeout=setTimeout(()=>controller.abort(),3500);
 const response=await net.fetch(serverUrl+'/api/health',{signal:controller.signal,cache:'no-store'}).finally(()=>clearTimeout(timeout));
 if(!response.ok)throw Error('서버에 연결할 수 없습니다.');
 if(offline||!loaded){offline=false;loaded=true;win.loadURL(serverUrl+'/')}
 }catch{showOffline()}
}
ipcMain.handle('open-wifi-settings',async()=>{if(process.platform==='win32')await shell.openExternal('ms-settings:network-wifi');else await shell.openExternal('https://support.microsoft.com/windows')});
ipcMain.handle('retry-connection',()=>checkConnection());
app.whenReady().then(async()=>{
 serverUrl=await chooseServer();
 win=new BrowserWindow({width:1280,height:820,minWidth:760,minHeight:540,title:'YEON Messenger',backgroundColor:'#202127',webPreferences:{nodeIntegration:false,contextIsolation:true,sandbox:true,preload:path.join(__dirname,'preload.js')}});
 if(!serverUrl){win.loadURL('data:text/html;charset=utf-8,'+encodeURIComponent('<html lang="ko"><meta charset="utf-8"><body style="font:16px system-ui;background:#202127;color:white;padding:65px"><h1>✦ YEON 메신저</h1><p>채팅 서버 주소를 설정해 주세요.</p><p>%APPDATA%/YEON/config.json: {"serverUrl":"https://your-server.example"}</p></body></html>'));return}
 win.webContents.setWindowOpenHandler(()=>({action:'deny'}));
 win.webContents.on('will-navigate',(event,target)=>{if(!target.startsWith(serverUrl+'/')&&!target.startsWith('data:text/html'))event.preventDefault()});
 win.webContents.on('did-fail-load',(event,code,desc,url,isMainFrame)=>{if(isMainFrame&&url.startsWith(serverUrl))showOffline()});
 await checkConnection();timer=setInterval(checkConnection,6000);
});
app.on('before-quit',()=>{if(timer)clearInterval(timer)});
app.on('window-all-closed',()=>app.quit());
