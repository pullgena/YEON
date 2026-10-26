'use strict';
/** Pair with a manually shared managed PC using only its temporary eight-digit PIN.
 * The PIN is never sent in LAN discovery requests. Discovery stays on private
 * local /24 networks and only the YEON service gets one login attempt per code.
 */
const http = require('node:http');
const os = require('node:os');
const {parseTarget, isLanIPv4} = require('./target');

const PORT = 8765;
const MAX_INTERFACES = 3;
const MAX_LOGIN_CANDIDATES = 12;
const MAX_SCAN_ADDRESSES = MAX_INTERFACES * 254;

function validatePin(pin) {
  if (typeof pin !== 'string' || !/^[0-9]{8}$/.test(pin))
    throw new Error('관리 대상 PC에 표시된 8자리 숫자를 입력하세요.');
  return pin;
}

/** Do not scan remote networks or the public Internet. */
function lanCandidates(interfaces = os.networkInterfaces(), saved = []) {
  const addresses = new Set();
  for (const item of saved) {
    try {
      const address = parseTarget(item.address || item);
      if (isLanIPv4(new URL(address).hostname)) addresses.add(address);
    } catch { /* Ignore older or malformed saved entries. */ }
  }
  let count = 0;
  for (const adapter of Object.values(interfaces || {})) {
    for (const entry of adapter || []) {
      if (entry.internal || !['IPv4', 4].includes(entry.family) || !isLanIPv4(entry.address)) continue;
      const parts = entry.address.split('.').map(Number);
      if (parts.length !== 4 || parts.some(x => !Number.isInteger(x))) continue;
      if (count++ >= MAX_INTERFACES) break;
      const prefix = parts.slice(0, 3).join('.');
      for (let last = 1; last <= 254; last++) addresses.add(`http://${prefix}.${last}:${PORT}/`);
    }
    if (count >= MAX_INTERFACES) break;
  }
  return [...addresses].slice(0, MAX_SCAN_ADDRESSES + saved.length);
}

function request(address, endpoint, options = {}) {
  const base = new URL(parseTarget(address));
  const bytes = options.payload === undefined ? null : Buffer.from(JSON.stringify(options.payload));
  return new Promise((resolve, reject) => {
    const req = http.request({
      hostname:base.hostname,port:PORT,path:endpoint,method:bytes?'POST':'GET',timeout:options.timeout || 700,
      headers:{Host:base.host,Origin:base.origin,
        ...(bytes ? {'Content-Type':'application/json','Content-Length':bytes.length} : {})}
    }, res => {
      const chunks = []; let n = 0;
      res.on('data', data => {
        n += data.length;
        if (n > 4096) {req.destroy(new Error('Unexpected response size'));return;}
        chunks.push(data);
      });
      res.on('end', () => {
        let body = {};
        try {body = JSON.parse(Buffer.concat(chunks).toString('utf8'));} catch {}
        resolve({status:res.statusCode,body,headers:res.headers});
      });
    });
    req.on('timeout', () => req.destroy(new Error('timeout')));
    req.on('error', reject);
    req.end(bytes || undefined);
  });
}

async function probe(address, transport = request) {
  try {
    const response = await transport(address, '/api/discover', {timeout:650});
    return response.status === 200 && response.body?.service === 'YEON_REMOTE_MANAGED' && response.body?.protocol === 1;
  } catch {return false;}
}

/** Bound concurrency and never send user PIN while searching. */
async function discover(interfaces, saved, options = {}) {
  const candidates = lanCandidates(interfaces, saved);
  const found = [];
  let next = 0;
  const workers = Array.from({length:Math.min(options.concurrency || 72,candidates.length)},async()=>{
    while(next < candidates.length && found.length < MAX_LOGIN_CANDIDATES) {
      const address = candidates[next++];
      if (await probe(address, options.transport || request)) found.push(address);
    }
  });
  await Promise.all(workers);
  return found;
}

async function tryLogin(address, pin, electronSession, transport = request) {
  let result;
  try {result = await transport(address, '/api/login', {payload:{pin},timeout:1800});}
  catch {return null;}
  if (result.status !== 200 || result.body?.ok !== true) return null;
  const setCookie = result.headers?.['set-cookie'];
  const line = Array.isArray(setCookie) ? setCookie.find(s => s.startsWith('yeon_session=')) : '';
  const match = /^yeon_session=([A-Za-z0-9_-]{40,100});/.exec(line || '');
  if (!match) return null;
  await electronSession.cookies.set({
    url:parseTarget(address), name:'yeon_session', value:match[1], path:'/', httpOnly:true,
    sameSite:'strict', expirationDate:Math.floor(Date.now()/1000)+3600
  });
  return {address};
}

async function connectByPin(pin, electronSession, saved, {interfaces=os.networkInterfaces(),transport=request}={}) {
  validatePin(pin);
  const addresses = await discover(interfaces, saved, {transport});
  if (!addresses.length) throw new Error('같은 Wi-Fi에서 공유 중인 YEON 관리 대상 PC를 찾지 못했습니다. PC에서 공유 시작을 누르고 Windows 방화벽의 개인 네트워크 허용을 확인하세요.');
  for (const address of addresses) {
    const login = await tryLogin(address, pin, electronSession, transport);
    if (login) return login;
  }
  throw new Error('8자리 코드가 일치하는 관리 대상 PC가 없습니다. 최신 접속 코드를 확인하세요.');
}

module.exports = {validatePin,lanCandidates,probe,discover,tryLogin,connectByPin,request};
