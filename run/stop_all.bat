@echo off
rem Stops only the PeX v2 servers (backend 8001, frontend 5174). The original AG demo on port 8000 is left running.
for %%P in (8001 5174) do (
  for /f "tokens=5" %%p in ('netstat -ano ^| findstr :%%P ^| findstr LISTENING') do taskkill /PID %%p /F >nul 2>&1
)
echo Stopped PeX v2 servers.
pause
