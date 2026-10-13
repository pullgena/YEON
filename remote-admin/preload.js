'use strict';
const {contextBridge, ipcRenderer} = require('electron');
contextBridge.exposeInMainWorld('yeonAdmin', Object.freeze({
  connect: address => ipcRenderer.invoke('yeon-admin:connect', address),
  disconnect: () => ipcRenderer.invoke('yeon-admin:disconnect'),
  getStatus: () => ipcRenderer.invoke('yeon-admin:status'),
  onStatus: callback => {
    if (typeof callback !== 'function') return;
    ipcRenderer.on('yeon-admin:status-event', (_event, payload) => callback(payload));
  }
}));
