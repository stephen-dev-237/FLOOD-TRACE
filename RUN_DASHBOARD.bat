@echo off
title FloodTrace Dashboard
cd /d "%~dp0"
echo.
echo ==========================================
echo        FLOODTRACE DASHBOARD V2
echo ==========================================
echo.
echo Starting frontend on http://127.0.0.1:5500
echo.
echo Keep your FloodTrace FastAPI backend running
echo separately on http://127.0.0.1:8000
echo.
echo Press Ctrl+C to stop.
echo.
python -m http.server 5500
pause
