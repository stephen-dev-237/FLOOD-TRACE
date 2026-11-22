@echo off
setlocal
title FloodTrace V2 - Launcher
cd /d "%~dp0"
echo.
echo ==========================================================
echo                 FLOODTRACE V2
echo             ONE-CLICK LOCAL LAUNCHER
echo ==========================================================
echo.
where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python was not found. Install Python 3.10+ and enable Add to PATH.
  pause
  exit /b 1
)
echo [1/4] Checking Python dependencies...
python -c "import pandas,numpy,fastapi,uvicorn,pydantic" >nul 2>nul
if errorlevel 1 (
  echo Installing required Python packages...
  python -m pip install --upgrade pip
  python -m pip install pandas numpy fastapi uvicorn pydantic
  if errorlevel 1 (
    echo [ERROR] Could not install dependencies.
    pause
    exit /b 1
  )
)
echo [2/4] Starting FloodTrace API on port 8000...
start "FloodTrace API" cmd /k "cd /d ""%~dp0"" && python -m uvicorn api.server:app --host 127.0.0.1 --port 8000"
echo [3/4] Waiting for API...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ok=$false; for($i=0;$i -lt 25;$i++){try{$r=Invoke-RestMethod 'http://127.0.0.1:8000/api/health' -TimeoutSec 2; if($r.status -eq 'online'){$ok=$true;break}}catch{}; Start-Sleep -Seconds 1}; if(-not $ok){exit 1}"
if errorlevel 1 (
  echo [ERROR] Backend did not become ready. Check the FloodTrace API window.
  pause
  exit /b 1
)
echo [4/4] Starting V2 dashboard on port 5500...
start "FloodTrace Dashboard" cmd /k "cd /d ""%~dp0"" && python -m http.server 5500 --bind 127.0.0.1"
timeout /t 2 /nobreak >nul
start "" "http://127.0.0.1:5500/"
echo.
echo FloodTrace V2 is running.
echo Dashboard: http://127.0.0.1:5500/
echo API:       http://127.0.0.1:8000/api/health
echo.
echo Keep both opened terminal windows running while using FloodTrace.
echo To stop both services, run STOP_FLOODTRACE.bat.
echo.
pause
