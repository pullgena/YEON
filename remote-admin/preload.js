'use strict';
const {contextBridge, ipcRenderer} = require('electron');
contextBridge.exposeInMainWorld('yeonAdmin', Object.freeze({
  connect: address => ipcRenderer.invoke('yeon-admin:connect', address),
  disconnect: () => ipcRenderer.invoke('yeon-admin:disconnect'),
  focusStart: () => ipcRenderer.invoke('yeon-admin:focus-start'),
  broadcastStart: () => ipcRenderer.invoke('yeon-admin:broadcast-start'),
  focusStop: () => ipcRenderer.invoke('yeon-admin:focus-stop'),
  remoteMode: () => ipcRenderer.invoke('yeon-admin:remote-mode'),
  controlPermission: () => ipcRenderer.invoke('yeon-admin:control-permission'),
  controlSet: enabled => ipcRenderer.invoke('yeon-admin:control-set', enabled),
  sendFile: () => ipcRenderer.invoke('yeon-admin:file-send'),
  requestFile: () => ipcRenderer.invoke('yeon-admin:file-request'),
  getComputers: () => ipcRenderer.invoke('yeon-admin:computers'),
  removeComputer: address => ipcRenderer.invoke('yeon-admin:computer-remove', address),
  getStatus: () => ipcRenderer.invoke('yeon-admin:status'),
  onStatus: callback => {
    if (typeof callback !== 'function') return;
    ipcRenderer.on('yeon-admin:status-event', (_event, payload) => callback(payload));
  }
}));
