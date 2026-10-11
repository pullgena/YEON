const { app, BrowserWindow, shell } = require('electron');
const path = require('node:path');
let win;
app.whenReady().then(() => {
  process.env.YEON_DESKTOP = '1';
  process.env.PORT = '0';
  process.env.YEON_DATA_FILE = path.join(app.getPath('userData'), 'data.json');
  const server = require('./server');
  const open = () => {
    const port = server.address().port;
    win = new BrowserWindow({
      width: 1300, height: 800, minWidth: 700, minHeight: 500,
      title: 'YEON', backgroundColor: '#171820',
      webPreferences: { nodeIntegration: false, contextIsolation: true, sandbox: true }
    });
    const allowed = 'http://127.0.0.1:' + port;
    win.webContents.setWindowOpenHandler(({url}) => {
      if (url.startsWith('https://')) shell.openExternal(url);
      return { action: 'deny' };
    });
    win.webContents.on('will-navigate', (event, url) => {
      if (!url.startsWith(allowed + '/')) event.preventDefault();
    });
    win.loadURL(allowed + '/');
    win.on('closed', () => { win = null; });
  };
  if (server.listening) open();
  else server.once('listening', open);
});
app.on('window-all-closed', () => app.quit());
