@echo off
title PeX frontend (port 5174)
cd /d "%~dp0..\frontend"
if not exist node_modules ( call npm ci )
echo Open http://localhost:5174 once it says Local:
call npm run dev
pause
