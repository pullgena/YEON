const {contextBridge,ipcRenderer}=require('electron');
contextBridge.exposeInMainWorld('yeon',Object.freeze({
 openWifi:()=>ipcRenderer.invoke('open-wifi-settings'),
 retry:()=>ipcRenderer.invoke('retry-connection')
}));
