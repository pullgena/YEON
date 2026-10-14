'use strict';
const http = require('node:http');
const fs = require('node:fs/promises');
const path = require('node:path');
const {parseTarget} = require('./target');
const {cookieForSession, send} = require('./focus_transport');
const MAX_FILE = 8 * 1024 * 1024;
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));

function cleanFilename(name) {
  if (typeof name !== 'string') throw new Error('파일 이름이 잘못되었습니다.');
  const filename = name.replace(/\\/g,'/').split('/').pop().replace(/[<>:"/\\|?*\x00-\x1f]/g,'').replace(/[. ]+$/g,'').slice(0,110);
  if (!filename || filename === '.' || filename === '..') throw new Error('파일 이름이 잘못되었습니다.');
  return filename;
}

/** GET and POST binary, over the same LAN-validated authenticated server. */
function transferBytes(address, endpoint, cookie, bytes = null) {
  const base = new URL(parseTarget(address));
  return new Promise((resolve,reject)=>{
    const method = bytes === null ? 'GET' : 'POST';
    const req = http.request({hostname:base.hostname, port:Number(base.port),path:endpoint,method,timeout:15000,
      headers:{Host:base.host,Origin:base.origin,Cookie:cookie,
        ...(bytes===null?{}:{'Content-Type':'application/octet-stream','Content-Length':bytes.length})}},res=>{
      const chunks=[];let total=0;
      res.on('data',chunk=>{
        total+=chunk.length;
        if(total>MAX_FILE+8192){req.destroy(new Error('허용 크기를 초과했습니다.'));return;}
        chunks.push(chunk);
      });
      res.on('end',()=>{
        const data=Buffer.concat(chunks);
        if(res.statusCode<200||res.statusCode>=300){
          let error='파일 교환 요청 실패';try{error=JSON.parse(data.toString('utf8')).error||error;}catch{}
          reject(new Error(error));return;
        }
        resolve(data);
      });
    });
    req.on('timeout',()=>req.destroy(new Error('파일 전송 시간이 초과됐습니다.')));
    req.on('error',reject);
    req.end(bytes||undefined);
  });
}

async function waitForApproval(address,cookie,id,allowed,report) {
  for(let i=0;i<150;i++) {
    await pause(1500);
    const r=await send(address,`/api/files/status?id=${encodeURIComponent(id)}`,{method:'GET',cookie});
    if (r.state==='denied') throw new Error('관리 대상 PC에서 파일 요청을 거절했습니다.');
    if (r.state==='error') throw new Error('관리 대상 PC에 파일을 저장하지 못했습니다.');
    if (allowed.includes(r.state)) return r;
    if(r.state!=='pending') throw new Error(`파일 작업 상태: ${r.state}`);
  }
  throw new Error('관리 대상 PC의 응답 대기 시간이 초과됐습니다.');
}

async function sendFile({electronSession, address, dialog, parent, report}) {
  const chosen=await dialog.showOpenDialog(parent,{title:'관리 대상 PC에 보낼 파일 선택',properties:['openFile']});
  if(chosen.canceled||!chosen.filePaths?.length)return {canceled:true};
  const filename=cleanFilename(path.basename(chosen.filePaths[0]));
  const stat=await fs.stat(chosen.filePaths[0]);
  if(!stat.isFile()||stat.size<1||stat.size>MAX_FILE)throw new Error('파일 크기는 1바이트~8MB만 가능합니다.');
  const cookie=await cookieForSession(electronSession,address);
  const response=await send(address,'/api/files/offer',{cookie,bytes:Buffer.from(JSON.stringify({filename,size:stat.size}))});
  report(`${filename} · 관리 대상 PC의 저장 승인을 기다리는 중…`);
  await waitForApproval(address,cookie,response.id,['approved'],report);
  const content=await fs.readFile(chosen.filePaths[0]);
  if(content.length!==stat.size)throw new Error('파일이 선택된 후 크기가 바뀌었습니다.');
  await transferBytes(address,`/api/files/upload?id=${encodeURIComponent(response.id)}`,cookie,content);
  report(`파일 전송 완료 · ${filename}`);
  return {ok:true};
}

async function requestFile({electronSession,address,dialog,parent,report}) {
  const cookie=await cookieForSession(electronSession,address);
  const response=await send(address,'/api/files/request',{cookie});
  report('관리 대상 PC에 파일 제출을 요청했습니다. 대상 사용자의 선택을 기다리는 중…');
  const ready=await waitForApproval(address,cookie,response.id,['ready'],report);
  const chosen=await dialog.showSaveDialog(parent,{title:'제출된 파일을 저장할 위치 선택',
    defaultPath:cleanFilename(ready.filename)});
  if(chosen.canceled||!chosen.filePath){report('관리자가 파일 저장을 취소했습니다.');return {canceled:true};}
  const data=await transferBytes(address,`/api/files/download?id=${encodeURIComponent(response.id)}`,cookie);
  if(data.length!==ready.size)throw new Error('제출된 파일의 크기가 일치하지 않습니다.');
  await fs.writeFile(chosen.filePath,data);
  report(`파일 제출 완료 · ${ready.filename}`);
  return {ok:true};
}
module.exports={MAX_FILE,cleanFilename,transferBytes,sendFile,requestFile};
