@echo off
rem One-time setup: Python venv, backend packages, frontend packages.
cd /d "%~dp0.."
if not exist .venv ( python -m venv .venv )
call .venv\Scripts\activate.bat
pip install -r requirements.txt
cd frontend
call npm ci
echo.
echo Setup done. Now run run\start_backend.bat, then run\start_frontend.bat
pause
