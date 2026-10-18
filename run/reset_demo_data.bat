@echo off
rem Wipes the demo database so it reseeds fresh (cutoffs are relative to seed time). Stop the backend first.
cd /d "%~dp0..\backend"
del /q pex_v2.db pex_v2.db-shm pex_v2.db-wal 2>nul
echo Demo database reset. Start the backend to reseed.
pause
