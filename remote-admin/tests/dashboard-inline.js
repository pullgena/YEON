
const $=id=>document.getElementById(id);
let activeAddress='';
function renderComputers(list){
  const el=$('computerList');el.replaceChildren();
  if(!Array.isArray(list)||!list.length){const p=document.createElement('p');p.className='pc-empty';p.textContent='등록된 컴퓨터가 없습니다. 주소를 입력해 연결하세요.';el.append(p);return;}
  for(const item of list){
    const row=document.createElement('div');row.className='pc-item'+(item.address===activeAddress?' active':'');
    const button=document.createElement('button');button.className='pc-select';button.type='button';
    const title=document.createElement('span');title.className='pc-name';title.textContent=item.name;
    const address=document.createElement('span');address.className='pc-address';address.textContent=item.address.replace(/^http:\/\//,'');
    button.append(title,address);button.title=`${item.name} 원격 화면 열기`;
    button.addEventListener('click',async()=>{
      $('error').textContent='';$('address').value=item.address;
      const result=await window.yeonAdmin.connect(item.address);
      if(!result.ok)$('error').textContent=result.error||'원격 화면을 열 수 없습니다.';
    });
    const remove=document.createElement('button');remove.type='button';remove.className='pc-remove';remove.textContent='×';remove.title='목록에서 삭제';
    remove.addEventListener('click',async()=>{
      const result=await window.yeonAdmin.removeComputer(item.address);
      if(!result.ok)$('error').textContent=result.error||'삭제 실패';
    });
    row.append(button,remove);el.append(row);
  }
}
function syncState(data){
  if(!data)return;
  $('status').textContent=data.status||'대기 중';
  activeAddress=data.address||'';
  if(Array.isArray(data.computers))renderComputers(data.computers);
}

$('connectForm').addEventListener('submit',async event=>{
  event.preventDefault();$('error').textContent='';
  $('connect').disabled=true;
  try{
    const result=await window.yeonAdmin.connect($('address').value);
    if(!result.ok)$('error').textContent=result.error||'접속할 수 없습니다.';
  }catch(err){$('error').textContent='연결 요청을 처리할 수 없습니다.';}
  finally{$('connect').disabled=false;}
});
$('disconnect').addEventListener('click',()=>window.yeonAdmin.disconnect());
$('focusStart').addEventListener('click',async()=>{
  $('error').textContent=''; const r=await window.yeonAdmin.focusStart();
  if(!r.ok)$('error').textContent=r.error||'전송을 시작할 수 없습니다.';
});
$('focusStop').addEventListener('click',()=>window.yeonAdmin.focusStop());
async function setAdminControl(enabled){
  $('error').textContent='';
  $('controlOn').disabled=true; $('controlOff').disabled=true;
  try {
    const result=await window.yeonAdmin.controlSet(enabled);
    if(!result.ok)$('error').textContent=result.error||'원격 제어 상태를 변경하지 못했습니다.';
  } catch { $('error').textContent='원격 제어 ON/OFF 요청 중 오류가 발생했습니다.'; }
  await refreshPermission();
}
$('controlOn').addEventListener('click',()=>setAdminControl(true));
$('controlOff').addEventListener('click',()=>setAdminControl(false));
$('remoteMode').addEventListener('click',async()=>{
  $('error').textContent=''; const r=await window.yeonAdmin.remoteMode();
  if(!r.ok)$('error').textContent=r.error||'원격 제어 모드를 열 수 없습니다.';
});
async function refreshPermission(){
  const result=await window.yeonAdmin.controlPermission().catch(()=>({ok:false}));
  $('controlOn').disabled = !result.ok || result.enabled;
  $('controlOff').disabled = !result.ok || !result.enabled;
  $('controlPermission').textContent=!result.ok ? '원격 제어 상태: 대상 PC의 8자리 코드 로그인 후 변경할 수 있습니다.' :
     (result.enabled ? '● 원격 제어 ON · 관리자에서 마우스·키보드 조작을 허용했습니다.' : '● 원격 제어 OFF · 화면만 볼 수 있습니다.');
}
setInterval(refreshPermission,3500);
refreshPermission();
window.yeonAdmin.onStatus(data=>{syncState(data);refreshPermission();});
window.yeonAdmin.getStatus().then(syncState);
$('address').focus();
