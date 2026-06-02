@echo off
setlocal
set "ROOT=%~dp0"
cd /d "%ROOT%"

if not exist ".venv\Scripts\python.exe" (
    echo [error] Virtual environment is missing. Run INSTALL_DEPENDENCIES.bat first.
    pause
    exit /b 1
)

echo [dashboard] Starting web dashboard on http://127.0.0.1:8501
echo.
".venv\Scripts\python.exe" -m streamlit run "%ROOT%crypto_dashboard.py" --server.address 127.0.0.1 --server.port 8501
echo.
echo [dashboard] Process ended.
pause
endlocal
