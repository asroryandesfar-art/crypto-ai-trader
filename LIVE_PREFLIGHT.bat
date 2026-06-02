@echo off
setlocal
set "ROOT=%~dp0"
cd /d "%ROOT%"

if not exist ".venv\Scripts\python.exe" (
    echo [error] Virtual environment is missing. Run INSTALL_DEPENDENCIES.bat first.
    pause
    exit /b 1
)

echo Running Binance Futures live preflight from:
echo %ROOT%
echo.
echo This check does not place orders.
echo.

".venv\Scripts\python.exe" main.py --preflight-live
set "RC=%ERRORLEVEL%"

echo.
if not "%RC%"=="0" (
    echo [blocked] Live trading preflight failed. Live mode was NOT enabled.
    pause
    exit /b %RC%
)

echo [ok] Live trading preflight passed.
pause
exit /b 0
