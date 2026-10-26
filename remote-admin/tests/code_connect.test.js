'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const {validatePin, lanCandidates, probe, connectByPin} = require('../code_connect');

const oneLan = {WiFi: [{family:'IPv4',address:'192.168.42.101',internal:false}],
  External:[{family:'IPv4',address:'8.8.8.8',internal:false}]};

test('only exactly eight ASCII digits can be used as access PIN', () => {
  assert.equal(validatePin('01234567'),'01234567');
  for(const value of ['1234','123456789','abcdefgh','１２３４５６７８',42,'']) assert.throws(()=>validatePin(value),/8자리/);
});

test('discovery is limited to local /24 and saved LAN hosts', () => {
  const list = lanCandidates(oneLan, [{address:'http://192.168.5.15:8765/'},{address:'https://public.com'}]);
  assert.ok(list.includes('http://192.168.42.20:8765/'));
  assert.ok(list.includes('http://192.168.5.15:8765/'));
  assert.ok(!list.includes('http://8.8.8.8:8765/'));
  assert.ok(!list.includes('http://192.168.43.20:8765/'));
  assert.ok(list.length <= 255);
});

test('probe accepts only YEON managed PC discovery markers', async () => {
  assert.equal(await probe('192.168.42.20:8765',async()=>({status:200,body:{service:'YEON_REMOTE_MANAGED',protocol:1}})),true);
  assert.equal(await probe('192.168.42.20:8765',async()=>({status:200,body:{service:'OTHER',protocol:1}})),false);
  assert.equal(await probe('192.168.42.20:8765',async()=>{throw Error('offline');}),false);
});

test('one number discovers, logs in once, and installs browser authentication cookie', async () => {
  const methods=[];
  const mockSession={cookies:{set:async cookie=>{methods.push(['cookie',cookie]);}}};
  const pin='10293847';
  const transport=async(address,endpoint,options)=>{
    if(endpoint==='/api/discover') {
      assert.equal(options.payload,undefined,'PIN must never be sent during discovery');
      return {status: address==='http://192.168.42.20:8765/' ? 200 : 404,
        body:{service:'YEON_REMOTE_MANAGED',protocol:1}};
    }
    if(endpoint==='/api/login') {
      assert.equal(options.payload.pin,pin);
      methods.push(['login',address]);
      return {status:200,body:{ok:true},headers:{'set-cookie':['yeon_session='+ 'a'.repeat(43) + '; HttpOnly; SameSite=Strict; Path=/; Max-Age=3600']}};
    }
    throw Error('unexpected endpoint');
  };
  const r=await connectByPin(pin,mockSession,[],{interfaces:oneLan,transport});
  assert.equal(r.address,'http://192.168.42.20:8765/');
  assert.equal(methods.filter(e=>e[0]==='login').length,1);
  const cookie=methods.find(e=>e[0]==='cookie')[1];
  assert.equal(cookie.name,'yeon_session');
  assert.equal(cookie.url,r.address);
  assert.equal(cookie.httpOnly,true);
});

test('no matching managed PC gives a readable message without storing credentials', async () => {
  const session={cookies:{set:()=>assert.fail('No cookie for wrong PIN')}};
  await assert.rejects(()=>connectByPin('12345678',session,[],{interfaces:oneLan,
    transport:async()=>({status:404,body:{}})}),/찾지 못했습니다/);
});
