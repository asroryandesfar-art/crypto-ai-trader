@echo off
setlocal
set "ROOT=%~dp0"

echo Stopping Crypto AI backend/dashboard processes from:
echo %ROOT%

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$root='%ROOT%';" ^
  "$venv=$root+'.venv\Scripts\';" ^
  "Get-CimInstance Win32_Process | Where-Object {" ^
  "  $_.Name -like 'python*' -and (($_.ExecutablePath -like ($venv+'*')) -or ($_.CommandLine -like ('*'+$root+'*'))) -and (" ^
  "    $_.CommandLine -like '* main.py*' -or" ^
  "    $_.CommandLine -like '*crypto_dashboard.py*' -or" ^
  "    $_.CommandLine -like '*streamlit*run*crypto_dashboard.py*' -or" ^
  "    $_.CommandLine -like '*pip install*requirements*.txt*'" ^
  "  )" ^
  "} | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue; Write-Host ('Stopped PID '+$_.ProcessId) }"

echo Stopped matching backend/dashboard processes.
endlocal
