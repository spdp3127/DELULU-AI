@echo off
title DELULU - AI Personal Operating Layer
echo ===================================================
echo     STARTING DELULU MULTI-USER AI PLATFORM
echo ===================================================
echo.
echo Launching server at http://localhost:8000...
start http://localhost:8000
python delulu/backend/main.py
pause
