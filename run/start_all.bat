@echo off
rem Starts the PeX backend (8001) and frontend (5174) in two windows, then opens the app.
start "PeX backend" cmd /k "%~dp0start_backend.bat"
timeout /t 8 /nobreak >nul
start "PeX frontend" cmd /k "%~dp0start_frontend.bat"
timeout /t 8 /nobreak >nul
start http://localhost:5174
