@echo off
setlocal
set "ROOT=%~dp0"
cd /d "%ROOT%"

echo [Crypto AI] Preparing one-click startup...

if not exist ".venv\Scripts\python.exe" (
    echo [setup] Virtual environment is missing.
    echo [setup] Opening installer first. After it finishes, run START_CRYPTO_AI.bat again.
    start "Crypto AI Dependency Installer" "%ROOT%INSTALL_DEPENDENCIES.bat"
    pause
    exit /b 1
)

if not exist "crypto_dashboard.py" (
    echo [error] crypto_dashboard.py was not found in %ROOT%
    pause
    exit /b 1
)

echo [db] Checking SQLite database and dashboard tables...
".venv\Scripts\python.exe" "%ROOT%scripts\launcher_prepare.py" --paper
if errorlevel 1 (
    echo [error] Database preparation failed.
    pause
    exit /b 1
)

echo [services] Starting backend and web dashboard in safe PAPER mode...
".venv\Scripts\python.exe" "%ROOT%scripts\service_manager.py" restart
if errorlevel 1 (
    echo [error] Services failed to start. Check logs\backend.err.log and logs\dashboard.err.log.
    pause
    exit /b 1
)

echo [browser] Opening launcher page and dashboard...
powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%scripts\open_dashboard_when_ready.ps1" -Root "%ROOT%"

echo.
echo [ok] Crypto AI is running.
echo      Web dashboard: http://127.0.0.1:8501
echo      Database: %ROOT%crypto_trader.db
echo.
echo To stop it later, double-click STOP_CRYPTO_AI.bat
timeout /t 5 /nobreak >nul
endlocal
