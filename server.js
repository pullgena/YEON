'use strict';
const http=require('node:http'),fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const port=Number(process.env.PORT||3000),file=process.env.YEON_DATA_FILE||path.resolve(process.cwd(),'yeon-data.json');
const seed={users:[],servers:[],channels:[],members:[],messages:[],friends:[],sessions:[]};
let db=seed;try{const parsed=JSON.parse(fs.readFileSync(file));for(const key of Object.keys(seed))if(Array.isArray(parsed[key]))db[key]=parsed[key]}catch{}
const streams=new Map();
const pendingSignups=new Map();
const emailRateLimit=new Map();
const uid=()=>crypto.randomUUID(),now=()=>new Date().toISOString(),safe=(v,max=64)=>String(v??'').trim().slice(0,max);
function persist(){fs.mkdirSync(path.dirname(file),{recursive:true});let temp=file+'.tmp';fs.writeFileSync(temp,JSON.stringify(db));fs.renameSync(temp,file)}
function json(res,status,data){res.writeHead(status,{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store','Access-Control-Allow-Origin':'*','Access-Control-Allow-Headers':'Content-Type, Authorization','Access-Control-Allow-Methods':'GET,POST,OPTIONS'});res.end(JSON.stringify(data))}
function auth(req,url){const token=(req.headers.authorization||'').replace(/^Bearer /,'')||url.searchParams.get('token');const session=db.sessions.find(s=>s.token===token);return session&&db.users.find(u=>u.id===session.userId)}
function publicUser(u){return {id:u.id,name:u.name}}
function member(id,serverId){return db.members.some(m=>m.userId===id&&m.serverId===serverId)}
function channels(id){return db.channels.filter(c=>member(id,c.serverId))}
function accessibleRoom(user,room){if(room.startsWith('dm:')){const pair=room.slice(3).split(':');return pair.length===2&&pair.includes(user.id)&&pair.every(id=>db.users.some(u=>u.id===id))}const c=db.channels.find(c=>c.id===room);return Boolean(c&&member(user.id,c.serverId))}
function emit(users,event,body){const payload='event: '+event+'\ndata: '+JSON.stringify(body)+'\n\n';for(const id of users){for(const stream of streams.get(id)||[])try{stream.write(payload)}catch{}}}
function emitAll(event,body){emit([...streams.keys()],event,body)}
function state(user){return {me:publicUser(user),users:db.users.filter(u=>u.id!==user.id).map(publicUser),servers:db.servers.filter(s=>member(user.id,s.id)),channels:channels(user.id),friends:db.friends.filter(f=>f.from===user.id||f.to===user.id),messages:db.messages.filter(m=>accessibleRoom(user,m.room)).slice(-1500)}}
const mime={'/':'text/html','/index.html':'text/html'};
function readBody(req){return new Promise((resolve,reject)=>{let data='';req.on('data',b=>{data+=b;if(data.length>25000){reject(Error('요청 크기 초과'));req.destroy()}});req.on('end',()=>{try{resolve(JSON.parse(data||'{}'))}catch{reject(Error('JSON 형식 오류'))}});req.on('error',reject)})}
const server=http.createServer(async(req,res)=>{
 const url=new URL(req.url,'http://localhost'),route=url.pathname;
 if(req.method==='OPTIONS'){res.writeHead(204,{'Access-Control-Allow-Origin':'*','Access-Control-Allow-Headers':'Content-Type, Authorization','Access-Control-Allow-Methods':'GET,POST,OPTIONS'});return res.end()}
 if(req.method==='GET'&&(route==='/'||route==='/index.html')){return fs.readFile(path.join(__dirname,'index.html'),(error,data)=>{if(error)return json(res,500,{error:'파일 로드 실패'});res.writeHead(200,{'Content-Type':'text/html; charset=utf-8','Cache-Control':'no-store'});res.end(data)})}
 if(route==='/api/health'&&req.method==='GET')return json(res,200,{ok:true,app:'YEON',version:'0.4.0'});
 try{
 const b=req.method==='POST'?await readBody(req):{};
 if(route==='/api/register'&&req.method==='POST')return json(res,410,{error:'이메일 인증을 거쳐 계정을 만들어 주세요.'});
 if(route==='/api/register/local'&&req.method==='POST'){
  const loopback=['127.0.0.1','::1','::ffff:127.0.0.1'];
  if(!loopback.includes(req.socket.remoteAddress)||!loopback.includes(req.socket.localAddress))return json(res,403,{error:'로컬 테스트 계정은 내 컴퓨터에서만 만들 수 있습니다.'});
  const name=safe(b.name,24),password=String(b.password||''),email=safe(b.email,254).toLowerCase();
  if(!/^[a-zA-Z0-9_가-힣]{2,24}$/.test(name)||password.length<8||password.length>128)return json(res,400,{error:'이름은 2~24자, 비밀번호는 8~128자로 입력해 주세요.'});
  if(!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email))return json(res,400,{error:'올바른 이메일 주소를 입력해 주세요.'});
  if(db.users.some(u=>u.name.toLowerCase()===name.toLowerCase()||u.email===email))return json(res,409,{error:'이미 등록된 이름 또는 이메일입니다.'});
  const salt=crypto.randomBytes(16).toString('hex'),hash=crypto.scryptSync(password,salt,64).toString('hex');
  const user={id:uid(),name,email,salt,hash,verified:false,localTest:true};
  db.users.push(user);const token=crypto.randomBytes(32).toString('hex');db.sessions.push({token,userId:user.id});persist();
  return json(res,201,{token,me:publicUser(user),warning:'이메일 인증을 하지 않은 로컬 테스트 계정입니다.'})
 }

 if(route==='/api/register/start'&&req.method==='POST'){
  const name=safe(b.name,24),password=String(b.password||''),email=safe(b.email,254).toLowerCase();
  if(!/^[a-zA-Z0-9_가-힣]{2,24}$/.test(name)||password.length<8||password.length>128)return json(res,400,{error:'이름은 2~24자, 비밀번호는 8~128자로 입력해 주세요.'});
  if(!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email))return json(res,400,{error:'올바른 이메일 주소를 입력해 주세요.'});
  if(db.users.some(u=>u.name.toLowerCase()===name.toLowerCase()||u.email===email))return json(res,409,{error:'이미 등록된 이름 또는 이메일입니다.'});
  if(!process.env.RESEND_API_KEY||!process.env.YEON_EMAIL_FROM)return json(res,503,{error:'이메일 인증 발송 설정이 아직 완료되지 않았습니다. 서버 관리자에게 문의해 주세요.'});
  const last=emailRateLimit.get(email)||0;if(Date.now()-last<60000)return json(res,429,{error:'인증 메일은 1분 후 다시 요청할 수 있습니다.'});
  const code=String(crypto.randomInt(100000,1000000));
  const salt=crypto.randomBytes(16).toString('hex'),hash=crypto.scryptSync(password,salt,64).toString('hex');
  const response=await fetch('https://api.resend.com/emails',{method:'POST',headers:{Authorization:'Bearer '+process.env.RESEND_API_KEY,'Content-Type':'application/json'},body:JSON.stringify({from:process.env.YEON_EMAIL_FROM,to:[email],subject:'[YEON] 이메일 인증번호',text:'YEON 이메일 인증번호: '+code+'\n10분 안에 입력해 주세요.'})});
  if(!response.ok){console.error('Mail send failed',response.status);return json(res,502,{error:'인증 메일을 보내지 못했습니다. 잠시 후 다시 시도해 주세요.'})}
  pendingSignups.set(email,{name,salt,hash,codeHash:crypto.createHash('sha256').update(code).digest('hex'),expires:Date.now()+600000,attempts:0});
  emailRateLimit.set(email,Date.now());return json(res,200,{ok:true,expiresIn:600});
 }
 if(route==='/api/register/verify'&&req.method==='POST'){
  const email=safe(b.email,254).toLowerCase(),code=String(b.code||'').trim(),entry=pendingSignups.get(email);
  if(!entry||Date.now()>entry.expires){pendingSignups.delete(email);return json(res,400,{error:'인증번호가 만료되었습니다. 다시 요청해 주세요.'})}
  entry.attempts++;if(entry.attempts>5){pendingSignups.delete(email);return json(res,429,{error:'입력 횟수를 초과했습니다. 다시 요청해 주세요.'})}
  const actual=crypto.createHash('sha256').update(code).digest(),expected=Buffer.from(entry.codeHash,'hex');
  if(!/^\d{6}$/.test(code)||!crypto.timingSafeEqual(actual,expected))return json(res,400,{error:'인증번호가 올바르지 않습니다.'});
  if(db.users.some(u=>u.name.toLowerCase()===entry.name.toLowerCase()||u.email===email))return json(res,409,{error:'이미 등록된 계정입니다.'});
  const user={id:uid(),name:entry.name,email,salt:entry.salt,hash:entry.hash,verified:true};
  db.users.push(user);const token=crypto.randomBytes(32).toString('hex');db.sessions.push({token,userId:user.id});pendingSignups.delete(email);persist();return json(res,201,{token,me:publicUser(user)})
 }
 if(route==='/api/login'&&req.method==='POST'){
  const user=db.users.find(u=>u.name.toLowerCase()===safe(b.name,24).toLowerCase());
  if(!user)return json(res,401,{error:'이름 또는 비밀번호가 잘못되었습니다.'});
  const hash=crypto.scryptSync(String(b.password||''),user.salt,64),expected=Buffer.from(user.hash,'hex');
  if(!crypto.timingSafeEqual(hash,expected))return json(res,401,{error:'이름 또는 비밀번호가 잘못되었습니다.'});
  const token=crypto.randomBytes(32).toString('hex');db.sessions.push({token,userId:user.id});persist();return json(res,200,{token,me:publicUser(user)})
 }
 const user=auth(req,url);if(!user)return json(res,401,{error:'로그인이 필요합니다.'});
 if(route==='/api/events'&&req.method==='GET'){
  res.writeHead(200,{'Content-Type':'text/event-stream','Cache-Control':'no-store','Connection':'keep-alive','Access-Control-Allow-Origin':'*'});res.write(': connected\n\n');if(!streams.has(user.id))streams.set(user.id,new Set());streams.get(user.id).add(res);req.on('close',()=>streams.get(user.id)?.delete(res));return
 }
 if(route==='/api/state'&&req.method==='GET')return json(res,200,state(user));
 if(route==='/api/logout'&&req.method==='POST'){db.sessions=db.sessions.filter(s=>s.token!==((req.headers.authorization||'').replace(/^Bearer /,'')));persist();return json(res,200,{ok:true})}
 if(route==='/api/servers'&&req.method==='POST'){
  const name=safe(b.name,40);if(!name)return json(res,400,{error:'서버 이름을 입력하세요.'});
  const s={id:uid(),name,owner:user.id,invite:crypto.randomBytes(5).toString('hex').toUpperCase()},c={id:uid(),serverId:s.id,name:'일반'};
  db.servers.push(s);db.channels.push(c);db.members.push({serverId:s.id,userId:user.id});persist();emit([user.id],'refresh',{});return json(res,201,{server:s,channel:c})
 }
 if(route==='/api/join'&&req.method==='POST'){
  const s=db.servers.find(s=>s.invite===safe(b.code,30).toUpperCase());if(!s)return json(res,404,{error:'올바른 초대 코드가 아닙니다.'});
  if(!member(user.id,s.id))db.members.push({serverId:s.id,userId:user.id});persist();emit([user.id],'refresh',{});return json(res,200,{server:s})
 }
 if(route==='/api/channels'&&req.method==='POST'){
  const s=db.servers.find(s=>s.id===b.serverId&&member(user.id,s.id));if(!s)return json(res,403,{error:'서버에 참여해야 합니다.'});
  const name=safe(b.name,32);if(!name)return json(res,400,{error:'채널 이름을 입력하세요.'});
  const c={id:uid(),serverId:s.id,name};db.channels.push(c);persist();emit(db.members.filter(m=>m.serverId===s.id).map(m=>m.userId),'refresh',{});return json(res,201,c)
 }
 if(route==='/api/friend'&&req.method==='POST'){
  const target=db.users.find(u=>u.name.toLowerCase()===safe(b.name,24).toLowerCase());
  if(!target||target.id===user.id)return json(res,404,{error:'사용자를 찾을 수 없습니다.'});
  if(db.friends.some(f=>[f.from,f.to].includes(user.id)&&[f.from,f.to].includes(target.id)))return json(res,409,{error:'이미 친구 요청이 있습니다.'});
  db.friends.push({id:uid(),from:user.id,to:target.id,status:'pending'});persist();emit([user.id,target.id],'refresh',{});return json(res,201,{ok:true})
 }
 if(route==='/api/friend/accept'&&req.method==='POST'){
  const f=db.friends.find(f=>f.id===b.id&&f.to===user.id&&f.status==='pending');if(!f)return json(res,404,{error:'요청을 찾을 수 없습니다.'});
  f.status='accepted';persist();emit([f.from,f.to],'refresh',{});return json(res,200,{ok:true})
 }
 if(route==='/api/messages'&&req.method==='POST'){
  const room=safe(b.room,100),text=safe(b.text,2000);if(!room||!text)return json(res,400,{error:'대화 내용이 없습니다.'});
  if(!accessibleRoom(user,room))return json(res,403,{error:'이 대화방을 이용할 수 없습니다.'});
  let recipients=[];
  if(room.startsWith('dm:')){const ids=room.slice(3).split(':');if(!db.friends.some(f=>f.status==='accepted'&&ids.includes(f.from)&&ids.includes(f.to)))return json(res,403,{error:'서로 친구가 되어야 DM을 보낼 수 있습니다.'});recipients=ids}
  else{const c=db.channels.find(c=>c.id===room);recipients=db.members.filter(m=>m.serverId===c.serverId).map(m=>m.userId)}
  const m={id:uid(),room,author:user.id,text,time:now()};db.messages.push(m);db.messages=db.messages.slice(-10000);persist();emit(recipients,'message',m);return json(res,201,m)
 }
 return json(res,404,{error:'존재하지 않는 기능입니다.'})
 }catch(e){console.error(e);if(!res.headersSent)json(res,400,{error:e.message||'요청 실패'})}
});
if(require.main===module)server.listen(port,()=>console.log('YEON server http://localhost:'+server.address().port));
module.exports=server;
