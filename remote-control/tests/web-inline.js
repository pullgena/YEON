
(() => {
  const $ = id => document.getElementById(id);
  let connected=false, controlsEnabled=false, frameTimer=null, statusTimer=null, lastPointer={x:0.5,y:0.5};
  let frameErrors=0, pressedButton=null, previousMove=0;
  const capture=$('keyboardCapture');
  let composing=false, typingTimer=null;
  const forwardedKeys=new Set();
  let keyboardQueue=Promise.resolve();
  function queueInput(data){
    keyboardQueue=keyboardQueue.catch(()=>{}).then(async()=>{
      if(!connected||!controlsEnabled)return;
      try{await request('/api/action',data)}catch(err){toast(err.message)}
    });
  }
  function flushInput(){
    if(typingTimer)clearTimeout(typingTimer);typingTimer=null;
    if(composing)return;
    const text=capture.value;capture.value='';
    if(!connected||!controlsEnabled||!text)return;
    for(let start=0;start<text.length;start+=800) queueInput({type:'text',text:text.slice(start,start+800)});
  }
  capture.addEventListener('compositionstart',()=>{composing=true;});
  capture.addEventListener('compositionend',()=>{composing=false;setTimeout(flushInput,0);});
  capture.addEventListener('input',event=>{
    if(composing||event.isComposing)return;
    clearTimeout(typingTimer);typingTimer=setTimeout(flushInput,35);
  });
  function focusTyping(){if(connected&&controlsEnabled)capture.focus({preventScroll:true});}
  $('mobileKeyboard').addEventListener('click',focusTyping);

  const img=$('frame');
  const translations={Control:'ctrl',Alt:'alt',Shift:'shift',Meta:'win',Escape:'esc',Enter:'enter',Backspace:'backspace',Delete:'delete',Tab:'tab',ArrowLeft:'left',ArrowRight:'right',ArrowUp:'up',ArrowDown:'down', ' ':'space',CapsLock:'capslock',PageUp:'pgup',PageDown:'pgdn',Home:'home',End:'end',Insert:'insert'};
  const keymap = key => translations[key] || (key.length===1 ? key.toLowerCase() : key.toLowerCase());

  function toast(msg){const t=$('toast');t.textContent=msg;t.style.display='block';clearTimeout(toast.timer);toast.timer=setTimeout(()=>{t.style.display='none'},2700)}
  async function request(path, data){
    const res=await fetch(path,{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
    let payload={};try{payload=await res.json()}catch(_){}
    if(res.status===401 && path!=='/api/login'){leave();throw new Error('인증이 만료되었습니다.')}
    if(!res.ok)throw new Error(payload.error||`요청 실패 (${res.status})`);
    return payload;
  }
  function setControlPermission(enabled){
    controlsEnabled = !!enabled;
    const label = $('remotePermission');
    label.classList.toggle('on',controlsEnabled);
    label.textContent = controlsEnabled ? '● 원격 제어 ON · 마우스와 키보드 사용 가능' : '● 원격 제어 OFF · 화면만 보기 (관리자 앱에서 ON으로 변경)';
    for(const element of document.querySelectorAll('[data-hotkey], #rightClick, #scrollUp, #scrollDown')){
      element.disabled = !controlsEnabled;
    }
    if(!controlsEnabled){
      pressedButton=null;capture.blur();capture.value='';clearTimeout(typingTimer);
      forwardedKeys.clear();
    }
  }
  async function action(data){
    if(!connected||!controlsEnabled)return;
    try{await request('/api/action',data)}catch(e){toast(e.message)}
  }
  function stopFrame(){if(frameTimer)clearTimeout(frameTimer);frameTimer=null;img.removeAttribute('src')}
  function leave(){connected=false;controlsEnabled=false;capture.blur();capture.value='';clearTimeout(typingTimer);forwardedKeys.clear();stopFrame();if(statusTimer)clearInterval(statusTimer);statusTimer=null;$('loginView').classList.remove('hidden');$('appView').classList.add('hidden');$('pin').value=''}
  async function begin(){
    try{
      const res=await fetch('/api/status',{credentials:'same-origin',cache:'no-store'});
      if(!res.ok){leave();return}
      const info=await res.json();
      $('resolution').textContent=`(${info.width} × ${info.height})`;
      setControlPermission(info.remoteControlEnabled);
      $('remotePcName').textContent=info.computerName ? '· '+info.computerName : '';
      $('loginView').classList.add('hidden');$('appView').classList.remove('hidden');
      connected=true;frameErrors=0;nextFrame();
      if(statusTimer)clearInterval(statusTimer);
      statusTimer=setInterval(async()=>{
        if(!connected)return;
        try{const r=await fetch('/api/status',{cache:'no-store'});if(!r.ok){leave();return} const info=await r.json();setControlPermission(info.remoteControlEnabled);}
        catch(e){$('connectionStatus').textContent='연결 확인 중';}
      },4000);
    }catch(e){leave();$('loginError').textContent='연결할 수 없습니다. PC에서 공유 중인지 확인하세요.'}
  }
  function nextFrame(){
    if(!connected)return;
    frameTimer=setTimeout(()=>{if(connected)img.src='/api/frame?_='+Date.now()},180);
  }
  img.addEventListener('load',()=>{frameErrors=0;$('placeholder').classList.add('hidden');$('frameInfo').textContent='실시간';nextFrame()});
  img.addEventListener('error',()=>{
    if(!connected)return;
    frameErrors++;
    $('frameInfo').textContent='화면 연결 확인 중';
    if(frameErrors>8){leave();return}
    frameTimer=setTimeout(()=>{if(connected)img.src='/api/frame?_='+Date.now()},850);
  });

  $('loginForm').addEventListener('submit',async e=>{
    e.preventDefault();const btn=$('loginButton');btn.disabled=true;$('loginError').textContent='';
    try{await request('/api/login',{pin:$('pin').value.trim()});await begin()}
    catch(err){$('loginError').textContent=err.message}
    finally{btn.disabled=false}
  });
  $('disconnect').addEventListener('click',async()=>{try{await request('/api/logout',{})}catch(e){}leave()});
  document.querySelectorAll('[data-hotkey]').forEach(b=>b.addEventListener('click',()=>action({type:'hotkey',name:b.dataset.hotkey})));
  $('rightClick').addEventListener('click',()=>{action({...lastPointer,type:'down',button:'right'});setTimeout(()=>action({...lastPointer,type:'up',button:'right'}),95)});
  $('scrollUp').addEventListener('click',()=>action({type:'scroll',amount:3}));
  $('scrollDown').addEventListener('click',()=>action({type:'scroll',amount:-3}));

  function point(e){
    const r=img.getBoundingClientRect();const nw=img.naturalWidth, nh=img.naturalHeight;
    if(!nw||!nh||!r.width||!r.height)return null;
    const s=Math.min(r.width/nw,r.height/nh);const w=nw*s,h=nh*s;
    const x=(e.clientX-(r.left+(r.width-w)/2))/w, y=(e.clientY-(r.top+(r.height-h)/2))/h;
    if(!Number.isFinite(x)||!Number.isFinite(y))return null;
    return {x:Math.max(0,Math.min(1,x)),y:Math.max(0,Math.min(1,y))};
  }
  img.addEventListener('pointerdown',e=>{
    if(!connected||!controlsEnabled)return;e.preventDefault();const p=point(e);if(!p)return;
    lastPointer=p;pressedButton=e.button===2?'right':e.button===1?'middle':'left';focusTyping();
    try{img.setPointerCapture(e.pointerId)}catch(_){}
    action({...p,type:'down',button:pressedButton});
  });
  img.addEventListener('pointermove',e=>{
    if(!connected||!controlsEnabled)return;const p=point(e);if(!p)return;lastPointer=p;
    const now=performance.now();if(now-previousMove<55)return;previousMove=now;
    action({...p,type:'move'});
  });
  function finishPointer(e){if(!connected||!controlsEnabled||!pressedButton)return;const p=point(e)||lastPointer;action({...p,type:'up',button:pressedButton});pressedButton=null}
  img.addEventListener('pointerup',finishPointer);
  img.addEventListener('pointercancel',finishPointer);
  img.addEventListener('lostpointercapture',finishPointer);
  img.addEventListener('contextmenu',e=>e.preventDefault());
  $('screen').addEventListener('wheel',e=>{if(!connected||!controlsEnabled)return;e.preventDefault();action({type:'scroll',amount:e.deltaY>0?-3:3})},{passive:false});
  // Hidden text capture receives real IME composition, so Korean and Google typing work
  // directly after clicking a field in the remote screenshot. No visible text box needed.
  const special=new Set(['Enter','Escape','Tab','Backspace','Delete','ArrowLeft','ArrowRight',
    'ArrowUp','ArrowDown','Home','End','Insert','PageUp','PageDown','Control','Alt','Meta']);
  document.addEventListener('keydown',e=>{
    if(!connected||!controlsEnabled||composing||e.isComposing||e.key==='Process'||e.key==='Dead')return;
    if(e.target!==capture && e.target.closest('input,textarea,button,select'))return;
    const shortcut=e.ctrlKey||e.altKey||e.metaKey;
    const shouldForward=special.has(e.key)||shortcut;
    if(!shouldForward)return; // Printable text arrives through the IME-aware input event.
    e.preventDefault();
    flushInput();
    const key=keymap(e.key);
    if(!forwardedKeys.has(key)){
      forwardedKeys.add(key);
      queueInput({type:'keyDown',key});
    }
  });
  document.addEventListener('keyup',e=>{
    if(!connected||!controlsEnabled)return;
    const key=keymap(e.key);
    if(!forwardedKeys.has(key))return;
    e.preventDefault();forwardedKeys.delete(key);queueInput({type:'keyUp',key});
  });
  window.addEventListener('blur',()=>{
    flushInput();
    for(const key of forwardedKeys)queueInput({type:'keyUp',key});
    forwardedKeys.clear();
    if(pressedButton){action({...lastPointer,type:'up',button:pressedButton});pressedButton=null;}
  });
  begin();
})();
