'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const {cleanList,remember,forget} = require('../computers');

test('remembers and selects named authenticated PCs without duplicates',()=>{
  let list=remember([], '192.168.1.20:8765');
  assert.equal(list[0].name,'192.168.1.20:8765');
  list=remember(list,'192.168.1.30:8765','OFFICE-PC');
  list=remember(list,'192.168.1.20:8765','CLASSROOM-PC');
  assert.equal(list.length,2);
  assert.deepEqual(list.map(r=>r.name),['CLASSROOM-PC','OFFICE-PC']);
  list=forget(list,'192.168.1.20:8765');
  assert.equal(list.length,1);
});
test('computer names are sanitized and addresses restricted to LAN',()=>{
  const r=cleanList([{address:'http://192.168.0.1:8765/',name:'\u0000 A  \n'},
    {address:'http://8.8.8.8:8765/',name:'outside'},
    {address:'http://192.168.0.1:8765/',name:'duplicate'}]);
  assert.deepEqual(r,[{address:'http://192.168.0.1:8765/',name:'A'}]);
  assert.throws(()=>remember([],'https://evil.example:8765/','evil'));
});
