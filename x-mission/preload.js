'use strict';
const {contextBridge, ipcRenderer} = require('electron');
contextBridge.exposeInMainWorld('yeonDesktop', Object.freeze({
  close: () => ipcRenderer.send('close-window'),
  minimize: () => ipcRenderer.send('minimize-window'),
  maximize: () => ipcRenderer.send('toggle-maximize-window'),
  onMission: callback => ipcRenderer.on('show-mission', () => callback())
}));
