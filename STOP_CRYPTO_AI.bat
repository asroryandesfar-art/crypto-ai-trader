@echo off
setlocal
set "ROOT=%~dp0"
cd /d "%ROOT%"

if not exist ".venv\Scripts\python.exe" (
    echo [error] Virtual environment is missing.
    pause
    exit /b 1
)

echo [Crypto AI] Stopping backend and dashboard...
".venv\Scripts\python.exe" "%ROOT%scripts\service_manager.py" stop
echo [ok] Stopped.
timeout /t 3 /nobreak >nul
endlocal
