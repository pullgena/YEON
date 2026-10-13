@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build-windows.ps1"
if errorlevel 1 (
 echo.
 echo BUILD FAILED. See error messages above.
 pause
 exit /b 1
)
echo BUILD SUCCEEDED.
pause
