'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const {parseTarget,isLanIPv4}=require('../target');

test('Accepts 192.168 LAN target with and without protocol',()=>{
  assert.equal(parseTarget('192.168.1.20:8765'),'http://192.168.1.20:8765/');
  assert.equal(parseTarget('http://192.168.1.20:8765/'),'http://192.168.1.20:8765/');
});
test('Accepts private and loopback addresses',()=>{
  for(const ip of ['10.0.0.25','172.16.5.4','172.31.0.255','192.168.10.5','127.0.0.1']) assert.equal(isLanIPv4(ip),true);
});
test('Rejects public and malformed IPv4',()=>{
  for(const ip of ['8.8.8.8','172.32.1.1','192.169.1.2','256.168.0.1','192.168.1.999','somewhere.com']) assert.equal(isLanIPv4(ip),false);
});
test('Rejects malicious protocols, arbitrary ports, external domains and credentials',()=>{
  for(const ip of ['https://192.168.0.2:8765','http://192.168.0.2:8000','javascript:alert(1)','http://evil.example:8765','http://a@192.168.0.2:8765']) assert.throws(()=>parseTarget(ip));
});
test('Rejects unexpected path, query or fragments',()=>{
  for(const ip of ['http://192.168.0.2:8765/api/status','192.168.0.2:8765/?x=y','192.168.0.2:8765/#foo']) assert.throws(()=>parseTarget(ip));
});
test('Rejects empty/oversized input',()=>{
  assert.throws(()=>parseTarget(''));
  assert.throws(()=>parseTarget('x'.repeat(210)));
});
