'use strict';
const {app,BrowserWindow,ipcMain,shell}=require('electron');
const path=require('node:path');
let window,service;
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const page=`<!doctype html><html lang="ko"><meta charset="utf-8"><title>YEON Server Terminal</title><style>*{box-sizing:border-box}body{margin:0;background:#141620;color:#e7ecf8;font:14px system-ui,"Malgun Gothic",sans-serif;padding:28px}.headline{display:flex;justify-content:space-between;align-items:center}h1{font-size:24px;margin:0}.pill{background:#4a3038;color:#ff9d9d;padding:8px 12px;border-radius:20px}pre{background:#080c13;color:#9bebc5;border:1px solid #2f3649;border-radius:12px;min-height:240px;padding:18px;white-space:pre-wrap;overflow:auto;line-height:1.65}button{border:0;border-radius:8px;background:#5363ee;color:white;font:700 14px system-ui;padding:13px 17px;cursor:pointer;margin:8px 8px 8px 0}button.stop{background:#ba4757}button:disabled{opacity:.4;cursor:not-allowed}p{color:#b5bbcb}code{color:#a8d3ff}small{color:#9ca6bf}</style><div class="headline"><h1>✦ YEON Server Terminal</h1><span id="status" class="pill">서버 종료됨</span></div><p>프로그램 자체에서 채팅 서버를 실행합니다. Node.js를 따로 설치하지 않아도 됩니다.</p><button id="start">▶ 서버 시작</button><button id="stop" class="stop" disabled>■ 서버 종료</button><button id="browser" disabled>🌐 브라우저에서 열기</button><p>서버 주소: <code id="address">미실행</code></p><pre id="logs">[YEON] 실행 준비 완료.\n</pre><small>기본적으로 이 PC에서만 접속할 수 있습니다. 외부 접속은 별도 배포가 필요합니다.</small><script>
const $=id=>document.getElementById(id);
function log(line){$('logs').textContent+=line+'\n';$('logs').scrollTop=$('logs').scrollHeight}
async function refresh(){const s=await window.terminal.status();$('status').textContent=s.running?'서버 실행 중':'서버 종료됨';$('status').style.background=s.running?'#214c3b':'#4a3038';$('status').style.color=s.running?'#a2ffcc':'#ff9d9d';$('address').textContent=s.url||'미실행';$('start').disabled=s.running;$('stop').disabled=!s.running;$('browser').disabled=!s.running}
$('start').onclick=async()=>{try{const s=await window.terminal.start();log('[START] '+s.url);await refresh()}catch(e){log('[ERROR] '+e.message)}};
$('stop').onclick=async()=>{try{await window.terminal.stop();log('[STOP] 서버가 종료되었습니다.');await refresh()}catch(e){log('[ERROR] '+e.message)}};
$('browser').onclick=()=>window.terminal.open();refresh();
</script></html>`;
function status(){return {running:!!service?.listening,url:service?.listening?'http://127.0.0.1:'+service.address().port:null}}
ipcMain.handle('server-status',status);
ipcMain.handle('server-start',async()=>{
 if(service?.listening)return status();
 if(!service){process.env.YEON_DATA_FILE=path.join(app.getPath('userData'),'server-data.json');service=require('./server')}
 await new Promise((resolve,reject)=>{const onError=e=>reject(e);service.once('error',onError);service.listen(3000,'127.0.0.1',()=>{service.off('error',onError);resolve()})});
 return status()
});
ipcMain.handle('server-stop',async()=>{if(service?.listening)await new Promise((resolve,reject)=>service.close(e=>e?reject(e):resolve()));return status()});
ipcMain.handle('server-open',async()=>{if(service?.listening)await shell.openExternal(status().url)});
app.whenReady().then(()=>{window=new BrowserWindow({width:850,height:640,minWidth:650,minHeight:560,backgroundColor:'#141620',title:'YEON Server Terminal',webPreferences:{preload:path.join(__dirname,'server-preload.js'),contextIsolation:true,nodeIntegration:false,sandbox:true}});window.webContents.setWindowOpenHandler(()=>({action:'deny'}));window.loadURL('data:text/html;charset=utf-8,'+encodeURIComponent(page))});
app.on('window-all-closed',()=>app.quit());
