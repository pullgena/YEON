@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ==============================================
echo   YEON Remote Manager v1.0.1 - Windows EXE builder
echo ==============================================
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0build-windows.ps1"
if errorlevel 1 (
  echo.
  echo [ERROR] Build failed. Please check the message above.
) else (
  echo.
  echo [OK] Build command completed.
)
pause
