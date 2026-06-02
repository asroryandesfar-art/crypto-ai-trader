@echo off
setlocal
set "ROOT=%~dp0"
cd /d "%ROOT%"

if not exist ".venv\Scripts\python.exe" (
    echo [error] Virtual environment is missing. Run INSTALL_DEPENDENCIES.bat first.
    pause
    exit /b 1
)

echo [safety] Running live preflight before enabling real orders...
".venv\Scripts\python.exe" main.py --preflight-live
if errorlevel 1 (
    echo.
    echo [blocked] Binance preflight failed. Real-money trading remains disabled.
    echo [blocked] Use BINANCE_NETWORK_DIAGNOSE.bat to inspect DNS/TLS blocking.
    pause
    exit /b 1
)

echo [safety] Preflight passed. Enabling guarded live mode...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$p='.env';" ^
  "$lines=Get-Content $p -ErrorAction SilentlyContinue;" ^
  "$map=@{TRADING_MODE='live';LIVE_TRADING='true';LIVE_TRADING_LOCKDOWN='false';EMERGENCY_STOP='false';MAX_LEVERAGE='10';MAX_RISK_PER_TRADE='1';MAX_OPEN_POSITIONS='1';MAX_LIVE_ORDER_USDT='15';LIVE_ORDER_CONFIRMATION='I_ACCEPT_REAL_MONEY_RISK'};" ^
  "foreach($k in $map.Keys){" ^
  "  if($lines -match ('^'+[regex]::Escape($k)+'=')){" ^
  "    $lines=$lines -replace ('^'+[regex]::Escape($k)+'=.*'), ($k+'='+$map[$k])" ^
  "  } else { $lines += ($k+'='+$map[$k]) }" ^
  "};" ^
  "Set-Content -Path $p -Value $lines -Encoding UTF8"

call "%ROOT%STOP_TERMINAL.bat"
timeout /t 3 /nobreak >nul

echo [start] Opening LIVE backend terminal...
start "Crypto AI LIVE Backend" "%ROOT%RUN_BACKEND_TERMINAL.bat"

timeout /t 4 /nobreak >nul

echo [start] Opening dashboard terminal...
start "Crypto AI Dashboard" "%ROOT%RUN_DASHBOARD_TERMINAL.bat"

timeout /t 8 /nobreak >nul
start "" "http://127.0.0.1:8501"

echo.
echo [ok] Live backend/dashboard launched.
pause
endlocal
