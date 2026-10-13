'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const http = require('node:http');
const {send, cookieForSession} = require('../focus_transport');

test('Focus API refuses invalid and non-local managed addresses', async()=>{
  assert.throws(()=>send('http://8.8.8.8:8765/','/api/focus/request'), /사설 IP/);
  assert.throws(()=>send('http://127.0.0.1:9999/','/api/focus/request'), /8765/);
});
test('Focus sender requests require an authenticated session', async()=>{
  const cookies = {cookies:{get:async()=>[]}};
  await assert.rejects(cookieForSession(cookies,'127.0.0.1:8765'), /8자리/);
  const connected = {cookies:{get:async()=>[{name:'yeon_session',value:'opaqueToken',httpOnly:true}]}};
  assert.equal(await cookieForSession(connected,'127.0.0.1:8765'), 'yeon_session=opaqueToken');
});
