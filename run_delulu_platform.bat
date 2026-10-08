@echo off
cd /d "%~dp0"
title DELULU - Native Desktop AI Assistant
echo ========================================================
echo        STARTING DELULU NATIVE DESKTOP ASSISTANT
echo ========================================================
echo.
echo Launching DELULU Native Desktop Window (Zero Localhost UI)...
python delulu/desktop_app.py
if errorlevel 1 (
    echo.
    echo Running dependency check...
    python -m pip install -r requirements.txt
    python delulu/desktop_app.py
)
pause
