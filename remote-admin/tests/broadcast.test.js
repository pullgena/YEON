'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const {FocusSender} = require('../focus_transport');

test('screen sender rejects invalid display modes without opening a connection', async()=>{
  const sender = new FocusSender({electronSession:{}, desktopCapturer:{}, onStatus:()=>{}});
  await assert.rejects(sender.start('192.168.1.22:8765','unknown'), /지원하지 않는 전송 방식/);
  assert.equal(sender.active,false);
});
test('stop invalidates sender generation so prior stream cannot close a later one',async()=>{
  const sender = new FocusSender({electronSession:{},desktopCapturer:{},onStatus:()=>{}});
  sender.active=true;
  sender.address=null;
  sender.cookie=null;
  const old=sender.generation;
  await sender.stop();
  assert.equal(sender.active,false);
  assert.equal(sender.generation,old+1);
});
