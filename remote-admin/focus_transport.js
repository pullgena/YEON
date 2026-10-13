'use strict';
const http = require('node:http');
const {parseTarget} = require('./target');

// POSTs are restricted to the already authenticated and LAN-validated managed PC.
function send(address, endpoint, {cookie, bytes, method = 'POST', type = 'application/json'} = {}) {
  const base = new URL(parseTarget(address));
  const payload = bytes ?? Buffer.from('{}');
  return new Promise((resolve, reject) => {
    const request = http.request({
      hostname: base.hostname, port: Number(base.port), path: endpoint, method,
      timeout: 3500,
      headers: {
        Host: base.host, Origin: base.origin,
        ...(method === 'POST' ? {'Content-Type': type, 'Content-Length': payload.length} : {}),
        ...(cookie ? {Cookie: cookie} : {})
      }
    }, response => {
      const chunks = [];
      response.on('data', chunk => { if (Buffer.concat(chunks).length < 8192) chunks.push(chunk); });
      response.on('end', () => {
        let obj = {};
        try {obj = JSON.parse(Buffer.concat(chunks).toString('utf8'));} catch {}
        if (response.statusCode < 200 || response.statusCode >= 300)
          return reject(new Error(obj.error || `관리 대상 PC에서 요청을 거절했습니다 (${response.statusCode})`));
        resolve(obj);
      });
    });
    request.on('timeout', () => request.destroy(new Error('관리 대상 PC에 응답이 없습니다.')));
    request.on('error', reject);
    if (method === 'POST') request.end(payload);
    else request.end();
  });
}

async function cookieForSession(electronSession, address) {
  const cookies = await electronSession.cookies.get({url: parseTarget(address)});
  const auth = cookies.find(item => item.name === 'yeon_session');
  if (!auth) throw new Error('먼저 원격 제어 창에서 8자리 접속 코드로 로그인하세요.');
  return `yeon_session=${auth.value}`;
}

const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));

class FocusSender {
  constructor({electronSession, desktopCapturer, onStatus}) {
    this.electronSession = electronSession;
    this.desktopCapturer = desktopCapturer;
    this.onStatus = onStatus;
    this.active = false;
    this.address = null;
    this.cookie = null;
  }
  async start(address) {
    if (this.active) throw new Error('이미 집중 화면 전송이 진행 중입니다.');
    const safe = parseTarget(address);
    const cookie = await cookieForSession(this.electronSession, safe);
    this.active = true;
    this.address = safe;
    this.cookie = cookie;
    try {
      await send(safe, '/api/focus/request', {cookie});
      this.onStatus('관리 대상 PC의 집중 화면 전송 승인을 기다리는 중…');
      let state = 'pending';
      for (let i = 0; i < 38 && this.active; i++) {
        await sleep(1000);
        state = (await send(safe, '/api/focus/status', {method:'GET', cookie})).mode;
        if (state !== 'pending') break;
      }
      if (!this.active) return;
      if (state !== 'active') throw new Error('관리 대상 PC에서 승인하지 않았거나 시간이 만료되었습니다.');
      this.onStatus('집중 화면 전송 중 · 대상 PC에서는 ESC로 종료할 수 있습니다.');
      let consecutiveErrors = 0;
      while (this.active) {
        try {
          const screens = await this.desktopCapturer.getSources({types:['screen'], thumbnailSize:{width:1152,height:648}});
          if (!screens.length) throw new Error('전송할 관리자 화면을 찾을 수 없습니다.');
          let jpeg = screens[0].thumbnail.toJPEG(58);
          if (jpeg.length > 900000) jpeg = screens[0].thumbnail.resize({width:800}).toJPEG(50);
          await send(safe, '/api/focus/frame', {cookie, bytes:jpeg, type:'image/jpeg'});
          consecutiveErrors = 0;
        } catch (error) {
          consecutiveErrors++;
          if (consecutiveErrors >= 3) throw error;
        }
        await sleep(320);
      }
    } catch (error) {
      if (this.active) this.onStatus(`집중 화면 전송 종료 · ${error.message}`);
      throw error;
    } finally {
      this.active = false;
      this.address = null;
      this.cookie = null;
      try {await send(safe, '/api/focus/stop', {cookie});} catch {}
    }
  }
  async stop() {
    const {active,address,cookie} = this;
    this.active = false;
    if (active && address && cookie) {
      try {await send(address, '/api/focus/stop', {cookie});} catch {}
    }
  }
}
module.exports = {send,cookieForSession,FocusSender};
