@echo off
setlocal
set "ROOT=%~dp0"
cd /d "%ROOT%"

if not exist ".venv\Scripts\python.exe" (
    echo [error] Virtual environment is missing. Run INSTALL_DEPENDENCIES.bat first.
    pause
    exit /b 1
)

echo [backend] Starting Crypto AI backend from:
echo %ROOT%
echo.
".venv\Scripts\python.exe" "%ROOT%main.py"
echo.
echo [backend] Process ended.
pause
endlocal
