// YEON — dependency-free real-time chat server (Node.js 20+)
const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const PORT = Number(process.env.PORT || 3000);
const DATA_FILE = path.join(__dirname, 'data.json');
const initial = { servers: [
  {id:'lounge', name:'YEON 라운지', icon:'Y', channels:[{id:'general',name:'일반'},{id:'introduce',name:'자기소개'},{id:'ideas',name:'아이디어'}]},
  {id:'games', name:'게임 모임', icon:'🎮', channels:[{id:'game-chat',name:'게임 채팅'},{id:'party',name:'파티 모집'}]}
], messages: [] };
let db = initial;
try { const v=JSON.parse(fs.readFileSync(DATA_FILE,'utf8')); if(Array.isArray(v.servers)&&Array.isArray(v.messages))db=v; } catch {}
const clients = new Set();
const online = new Map();
function save(){const tmp=DATA_FILE+'.tmp';fs.writeFileSync(tmp,JSON.stringify(db,null,2));fs.renameSync(tmp,DATA_FILE)}
function send(res,code,obj){res.writeHead(code,{'content-type':'application/json; charset=utf-8','cache-control':'no-store'});res.end(JSON.stringify(obj))}
function broadcast(event,data){for(const res of clients){try{res.write('event: '+event+'\ndata: '+JSON.stringify(data)+'\n\n')}catch{clients.delete(res)}}}
function snapshot(){return {servers:db.servers,messages:db.messages.slice(-500),online:[...online.values()]}}
function clean(s,max=80){return String(s||'').trim().slice(0,max)}
function publicFile(res){fs.readFile(path.join(__dirname,'index.html'),(err,buf)=>{if(err){res.writeHead(500);res.end('Server error')}else{res.writeHead(200,{'content-type':'text/html; charset=utf-8','cache-control':'no-cache','x-content-type-options':'nosniff'});res.end(buf)}})}
const server=http.createServer((req,res)=>{
 const pathname=new URL(req.url,'http://localhost').pathname;
 if(req.method==='GET'&&(pathname==='/'||pathname==='/index.html'))return publicFile(res);
 if(req.method==='GET'&&pathname==='/api/state')return send(res,200,snapshot());
 if(req.method==='GET'&&pathname==='/api/events'){
  res.writeHead(200,{'content-type':'text/event-stream; charset=utf-8','cache-control':'no-cache','connection':'keep-alive','x-accel-buffering':'no'});
  res.write(': connected\n\n');clients.add(res);req.on('close',()=>clients.delete(res));return;
 }
 if(req.method!=='POST'||!['/api/message','/api/channel','/api/server','/api/presence'].includes(pathname))return send(res,404,{error:'찾을 수 없습니다.'});
 let raw='';req.on('data',chunk=>{raw+=chunk;if(raw.length>12000)req.destroy()});
 req.on('end',()=>{let body;try{body=JSON.parse(raw)}catch{return send(res,400,{error:'잘못된 요청입니다.'})}
  if(pathname==='/api/message'){
   const serverId=clean(body.serverId,50),channelId=clean(body.channelId,50);
   if(!db.servers.some(s=>s.id===serverId&&s.channels.some(c=>c.id===channelId)))return send(res,400,{error:'채널이 없습니다.'});
   const author=clean(body.author,24)||'익명',text=clean(body.text,2000);
   if(!text)return send(res,400,{error:'내용을 입력해 주세요.'});
   const msg={id:crypto.randomUUID(),serverId,channelId,author,text,time:new Date().toISOString()};
   db.messages.push(msg);db.messages=db.messages.slice(-3000);save();broadcast('message',msg);return send(res,201,msg);
  }
  if(pathname==='/api/channel'){
   const server=db.servers.find(s=>s.id===clean(body.serverId,50));if(!server)return send(res,404,{error:'서버가 없습니다.'});
   const name=clean(body.name,30);if(!name)return send(res,400,{error:'채널 이름을 입력해 주세요.'});
   const channel={id:crypto.randomUUID(),name};server.channels.push(channel);save();broadcast('state',snapshot());return send(res,201,channel);
  }
  if(pathname==='/api/server'){
   const name=clean(body.name,36);if(!name)return send(res,400,{error:'서버 이름을 입력해 주세요.'});
   const s={id:crypto.randomUUID(),name,icon:name[0].toUpperCase(),channels:[{id:crypto.randomUUID(),name:'일반'}]};
   db.servers.push(s);save();broadcast('state',snapshot());return send(res,201,s);
  }
  const id=clean(body.id,80),name=clean(body.name,24);
  if(!id)return send(res,400,{error:'사용자 ID가 필요합니다.'});
  if(body.leave)online.delete(id);else online.set(id,{id,name:name||'익명',time:Date.now()});
  broadcast('online',[...online.values()]);return send(res,200,{ok:true});
 });
});
setInterval(()=>{for(const [id,user]of online)if(Date.now()-user.time>45000)online.delete(id);broadcast('online',[...online.values()])},15000).unref();
server.listen(PORT,()=>console.log('YEON running at http://localhost:'+PORT));
