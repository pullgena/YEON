const { app, BrowserWindow, Menu, ipcMain, net, shell } = require("electron");
const path = require("path");
const { execFile } = require("child_process");

app.commandLine.appendSwitch("autoplay-policy", "no-user-gesture-required");

let mainWindow = null;
let lastOnline = null;

function runPowerShell(script) {
  return new Promise((resolve) => {
    execFile(
      "powershell.exe",
      ["-NoProfile", "-ExecutionPolicy", "Bypass", "-WindowStyle", "Hidden", "-Command", script],
      { windowsHide: true, timeout: 7000 },
      (error, stdout, stderr) => resolve({
        ok: !error,
        stdout: String(stdout || "").trim(),
        stderr: String(stderr || "").trim()
      })
    );
  });
}

async function openWifiQuickSettings() {
  if (process.platform !== "win32") return { opened: false, fallback: false };

  const script = String.raw`
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class KeySender {
  [DllImport("user32.dll", SetLastError=true)]
  public static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, UIntPtr dwExtraInfo);
}
"@
$KEYEVENTF_KEYUP = 0x0002
$VK_LWIN = 0x5B
$VK_A = 0x41
[KeySender]::keybd_event($VK_LWIN, 0, 0, [UIntPtr]::Zero)
[KeySender]::keybd_event($VK_A, 0, 0, [UIntPtr]::Zero)
Start-Sleep -Milliseconds 60
[KeySender]::keybd_event($VK_A, 0, $KEYEVENTF_KEYUP, [UIntPtr]::Zero)
[KeySender]::keybd_event($VK_LWIN, 0, $KEYEVENTF_KEYUP, [UIntPtr]::Zero)
Start-Sleep -Milliseconds 850

$clicked = $false
try {
  Add-Type -AssemblyName UIAutomationClient
  Add-Type -AssemblyName UIAutomationTypes
  $root = [System.Windows.Automation.AutomationElement]::RootElement
  $buttons = $root.FindAll(
    [System.Windows.Automation.TreeScope]::Descendants,
    [System.Windows.Automation.Condition]::TrueCondition
  ) | Where-Object {
    $_.Current.ControlType -eq [System.Windows.Automation.ControlType]::Button -and
    $_.Current.Name -match 'Wi-?Fi|와이파이|무선'
  }
  $target = $buttons | Where-Object {
    $_.Current.Name -match '관리|Manage|연결|network|네트워크'
  } | Select-Object -First 1
  if (-not $target) { $target = $buttons | Select-Object -Last 1 }
  if ($target) {
    $pattern = $null
    if ($target.TryGetCurrentPattern(
      [System.Windows.Automation.InvokePattern]::Pattern,
      [ref]$pattern
    )) {
      $pattern.Invoke()
      $clicked = $true
    }
  }
} catch {}
if ($clicked) { Write-Output "CLICKED" } else { Write-Output "FALLBACK" }
`;

  const result = await runPowerShell(script);
  if (result.ok && result.stdout.includes("CLICKED")) {
    return { opened: true, fallback: false };
  }

  try {
    await shell.openExternal("ms-settings:network-wifi");
    return { opened: false, fallback: true };
  } catch {
    return { opened: false, fallback: false };
  }
}

async function getNetworkQuality() {
  if (!net.isOnline()) {
    return { online: false, ok: false, latency: null };
  }

  const start = Date.now();
  let timeout;

  try {
    const controller = new AbortController();
    timeout = setTimeout(() => controller.abort(), 3500);

    const response = await net.fetch(
      "https://www.gstatic.com/generate_204",
      {
        method: "GET",
        cache: "no-store",
        signal: controller.signal
      }
    );

    clearTimeout(timeout);

    return {
      online: true,
      ok: response.ok || response.status === 204,
      latency: Date.now() - start
    };
  } catch {
    if (timeout) clearTimeout(timeout);
    return {
      online: true,
      ok: false,
      latency: Date.now() - start
    };
  }
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 960,
    minHeight: 600,
    backgroundColor: "#000000",
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true,
      webSecurity: true
    }
  });

  Menu.setApplicationMenu(null);
  mainWindow.loadFile(path.join(__dirname, "game.html"));
  mainWindow.webContents.setWindowOpenHandler(() => ({ action: "deny" }));
}

ipcMain.handle("network:is-online", () => net.isOnline());
ipcMain.handle("network:quality", getNetworkQuality);
ipcMain.handle("windows:open-wifi-quick-settings", openWifiQuickSettings);

setInterval(() => {
  const online = net.isOnline();
  if (online !== lastOnline) {
    lastOnline = online;
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send("network:changed", online);
    }
  }
}, 1500);

app.whenReady().then(() => {
  lastOnline = net.isOnline();
  createWindow();
  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});
