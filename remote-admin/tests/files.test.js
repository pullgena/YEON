'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const {MAX_FILE,cleanFilename}=require('../file_transfer');
test('file names cannot insert paths or reserved characters',()=>{
  assert.equal(cleanFilename('C:\\downloads\\lesson?.pdf'),'lesson.pdf');
  assert.equal(cleanFilename('../safe.txt'),'safe.txt');
  assert.throws(()=>cleanFilename('...'));
});
test('file limits and admin UI controls are included',()=>{
  assert.equal(MAX_FILE,8*1024*1024);
  const html=require('node:fs').readFileSync(require('node:path').join(__dirname,'../index.html'),'utf8');
  assert.match(html,/id="sendFile"/);
  assert.match(html,/id="requestFile"/);
  assert.match(html,/class="sidebar-computers"/);
});
