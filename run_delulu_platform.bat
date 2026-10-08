@echo off
cd /d "%~dp0"
title DELULU - AI Personal Operating Layer
echo ========================================================
echo        STARTING DELULU MULTI-USER AI PLATFORM
echo ========================================================
echo.
echo Launching server at http://localhost:8000...
start "" "http://localhost:8000"
python delulu/backend/main.py
if errorlevel 1 (
    echo.
    echo Server stopped or dependencies missing.
    echo Running dependency check...
    python -m pip install -r requirements.txt
    python delulu/backend/main.py
)
pause
