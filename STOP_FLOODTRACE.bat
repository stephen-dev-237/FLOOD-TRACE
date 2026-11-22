@echo off
title Stop FloodTrace V2
echo Stopping FloodTrace services on ports 8000 and 5500...
powershell -NoProfile -ExecutionPolicy Bypass -Command "foreach($port in @(8000,5500)){Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object {Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue}}"
echo FloodTrace services stopped.
pause
