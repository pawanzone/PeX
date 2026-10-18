@echo off
rem Stops PeX servers (python and node).
taskkill /IM python.exe /F >nul 2>&1
taskkill /IM node.exe /F >nul 2>&1
echo Stopped.
pause
