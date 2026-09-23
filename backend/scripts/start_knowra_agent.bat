@echo off
title Knowra Desktop Companion Agent (1-Click Browser Auto-Launch)
echo ========================================================
echo  Starting Knowra Desktop Agent on http://127.0.0.1:9876
echo ========================================================
echo.
cd /d "%~dp0\.."
python scripts\desktop_meeting_companion.py --daemon
pause
