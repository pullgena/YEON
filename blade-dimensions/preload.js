const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("yeonNative", {
  isOnline: () => ipcRenderer.invoke("network:is-online"),
  getNetworkQuality: () => ipcRenderer.invoke("network:quality"),
  openWifiQuickSettings: () => ipcRenderer.invoke("windows:open-wifi-quick-settings"),
  onConnectivityChanged: (callback) => {
    ipcRenderer.on("network:changed", (_event, online) => callback(!!online));
  }
});
