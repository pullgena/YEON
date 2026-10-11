const {app,BrowserWindow,dialog}=require('electron');
const fs=require('node:fs'),path=require('node:path');
let win;
function configPath(){return path.join(app.getPath('userData'),'config.json')}
async function chooseServer(){
 let configured=process.env.YEON_SERVER_URL||'';
 try{configured=configured||JSON.parse(fs.readFileSync(configPath(),'utf8')).serverUrl}catch{}
 if(!configured){const result=await dialog.showMessageBox({type:'info',title:'YEON 서버 연결',message:'YEON 메신저 서버 주소가 필요합니다.',detail:'현재 공개 서버는 아직 운영되지 않습니다. 관리자가 서버를 배포한 후 서버 주소(HTTPS)를 설정하세요.\n\n설정 파일: %APPDATA%\\YEON\\config.json',buttons:['확인']});return null}
 let address;try{address=new URL(configured)}catch{return null}
 if(!['https:','http:'].includes(address.protocol))return null;
 if(address.protocol==='http:'&&!['localhost','127.0.0.1'].includes(address.hostname))return null;
 return address.origin
}
app.whenReady().then(async()=>{
 const server=await chooseServer();
 win=new BrowserWindow({width:1280,height:820,minWidth:760,minHeight:540,title:'YEON Messenger',backgroundColor:'#202127',webPreferences:{nodeIntegration:false,contextIsolation:true,sandbox:true}});
 if(!server){win.loadURL('data:text/html;charset=utf-8,'+encodeURIComponent('<html lang="ko"><meta charset="utf-8"><body style="font:16px system-ui;background:#202127;color:white;padding:65px"><h1>✦ YEON 메신저</h1><p>채팅 서버 연결이 필요합니다.</p><p>%APPDATA%/YEON/config.json 파일을 만들고 다음과 같이 입력하세요.</p><pre>{ "serverUrl": "https://your-yeon-server.example" }</pre><p>서버 운영자가 제공한 실제 주소로 변경한 뒤 앱을 다시 실행하세요.</p></body></html>'));return}
 win.webContents.setWindowOpenHandler(()=>({action:'deny'}));
 win.webContents.on('will-navigate',(event,target)=>{if(!target.startsWith(server+'/'))event.preventDefault()});
 win.loadURL(server+'/');
});
app.on('window-all-closed',()=>app.quit());
