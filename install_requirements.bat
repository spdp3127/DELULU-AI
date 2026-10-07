@echo off
title Install Dependencies - JARVIS AI Assistant
echo ===================================================
echo     INSTALLING DEPENDENCIES FOR JARVIS
echo ===================================================
echo.
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
echo.
echo ===================================================
echo   Setup Complete! You can now run run_jarvis.bat
echo ===================================================
pause
