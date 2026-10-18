@echo off
title PeX backend (port 8000)
rem Free port 8000 if an old backend is still running.
for /f "tokens=5" %%p in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do taskkill /PID %%p /F >nul 2>&1
cd /d "%~dp0..\backend"
call ..\.venv\Scripts\activate.bat
set DATABASE_URL=sqlite:///pex_v2.db
set PEX_DEMO=true
set PEX_OPERATION_MODE=ASSISTED
set PEX_BANK_CALLBACK_SECRET=demo-secret
set JWT_SECRET=demo-jwt-secret
set SIM_BANK_ACK_SECONDS=6
echo Backend on http://127.0.0.1:8000  (demo data seeds on first start)
python -m uvicorn app.main:app --port 8000
pause
