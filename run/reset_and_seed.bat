@echo off
title PeX reset and seed
rem Wipes the demo database and seeds everything a demo or a manual test round needs:
rem baseline cases, showcase cases, STP batch, and the manual-test pack (TST-... cases, one clean case for each of the 41 profiles).
rem Stop the backend first (run\stop_all.bat). Start it again afterwards (run\start_all.bat).
cd /d "%~dp0.."
call .venv\Scripts\activate.bat
set DATABASE_URL=sqlite:///pex_v2.db
set PEX_DEMO=true
set PEX_OPERATION_MODE=ASSISTED
python scripts\reset_and_seed_demo.py --db sqlite:///pex_v2.db
echo.
echo Done. Now run run\start_all.bat
pause
