const {contextBridge,ipcRenderer}=require('electron');
contextBridge.exposeInMainWorld('yeon',Object.freeze({
 openWifi:()=>ipcRenderer.invoke('open-wifi-settings'),
 retry:()=>ipcRenderer.invoke('retry-connection'),
 chooseMode:(mode,url)=>ipcRenderer.invoke('choose-mode',mode,url),
 showServers:()=>ipcRenderer.invoke('show-servers'),
 enterCode:(code)=>ipcRenderer.invoke('enter-code',code),
 openVeylo:()=>ipcRenderer.invoke('open-veylo')
}));

// A rapid standard double click anywhere in the YEON window closes the app.
window.addEventListener('dblclick',event=>{if(event.isTrusted)ipcRenderer.send('yeon-window-double-click-quit')},true);
