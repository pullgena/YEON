$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$sourceRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$appRoot = $sourceRoot
if (!(Test-Path (Join-Path $appRoot 'app.py'))) {
    throw 'remote-control/app.py was not found. Extract the entire ZIP first.'
}

function Find-Python312 {
    if (Get-Command py.exe -ErrorAction SilentlyContinue) {
        try {
            $candidate = (& py.exe -3.12 -c 'import sys; print(sys.executable)' 2>$null)
            if ($LASTEXITCODE -eq 0 -and $candidate -and (Test-Path $candidate.Trim())) {
                return $candidate.Trim()
            }
        } catch { }
    }
    $candidates = @(
        (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312\python.exe'),
        'C:\Program Files\Python312\python.exe',
        'C:\Python312\python.exe'
    )
    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) { return $candidate }
    }
    return $null
}

$python = Find-Python312
if (!$python) {
    if (!(Get-Command winget.exe -ErrorAction SilentlyContinue)) {
        throw 'Python 3.12 is missing. Install it from https://www.python.org/downloads/ and run BUILD-WINDOWS.bat again.'
    }
    Write-Host '[1/5] Installing Python 3.12 with winget...' -ForegroundColor Cyan
    & winget.exe install -e --id Python.Python.3.12 --source winget --accept-source-agreements --accept-package-agreements
    if ($LASTEXITCODE -ne 0) { throw 'Python installation failed.' }
    $python = Find-Python312
    if (!$python) { throw 'Python installation completed, but Python 3.12 could not be found. Restart Windows and run this file again.' }
}

Write-Host '[1/5] Python 3.12 found.' -ForegroundColor Cyan
$venvDir = Join-Path $appRoot '.build-venv'
$venvPython = Join-Path $venvDir 'Scripts\python.exe'
if (!(Test-Path $venvPython)) {
    & $python -m venv $venvDir
    if ($LASTEXITCODE -ne 0) { throw 'Unable to create the Python environment.' }
}

Push-Location $appRoot
try {
    Write-Host '[2/5] Installing build dependencies...' -ForegroundColor Cyan
    & $venvPython -m pip install --disable-pip-version-check --upgrade pip
    if ($LASTEXITCODE -ne 0) { throw 'pip upgrade failed.' }
    & $venvPython -m pip install --disable-pip-version-check -r requirements.txt 'pyinstaller>=6.8,<7'
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }

    Write-Host '[3/5] Checking source syntax...' -ForegroundColor Cyan
    & $venvPython -m compileall -q app.py pc_control.py remote_server.py tray_visual.py tools/make_icon.py
    if ($LASTEXITCODE -ne 0) { throw 'Python syntax check failed.' }

    Write-Host '[4/5] Running tests...' -ForegroundColor Cyan
    & $venvPython -m unittest discover -s tests -v
    if ($LASTEXITCODE -ne 0) { throw 'One or more tests failed. Build stopped.' }

    Write-Host '[5/5] Building Windows EXE...' -ForegroundColor Cyan
    & $venvPython tools/make_icon.py
    if ($LASTEXITCODE -ne 0) { throw 'Icon generation failed.' }
    & $venvPython -m PyInstaller --noconfirm --clean --onefile --windowed --name 'YEON-Managed-PC-v1.2.0' --icon 'assets/yeon-managed.ico' --add-data 'assets/yeon-managed.ico;assets' --add-data 'web/index.html;web' --hidden-import 'pystray._win32' app.py
    if ($LASTEXITCODE -ne 0) { throw 'PyInstaller failed.' }

    $exe = Join-Path $appRoot 'dist\YEON-Managed-PC-v1.2.0.exe'
    if (!(Test-Path $exe)) { throw 'EXE was not created.' }
    Write-Host "SUCCESS: $exe" -ForegroundColor Green
    Start-Process -FilePath explorer.exe -ArgumentList ('/select,"' + $exe + '"')
} finally {
    Pop-Location
}
