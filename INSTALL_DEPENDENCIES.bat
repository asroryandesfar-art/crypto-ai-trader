@echo off
setlocal
set "ROOT=%~dp0"
cd /d "%ROOT%"

if not exist ".venv\Scripts\python.exe" (
    echo [setup] Creating virtual environment...
    python -m venv .venv
)

echo [setup] Installing backend dependencies...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt
if errorlevel 1 (
    echo [error] Failed to install backend dependencies.
    pause
    exit /b 1
)

echo [setup] Installing dashboard dependencies...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements_dashboard.txt
if errorlevel 1 (
    echo [error] Failed to install dashboard dependencies.
    pause
    exit /b 1
)

echo [done] Dependencies are installed. Now run START_CRYPTO_AI.bat.
pause
endlocal
