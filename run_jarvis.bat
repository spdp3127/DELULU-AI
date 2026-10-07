@echo off
title JARVIS AI Assistant - Stark Industries HUD
echo ===================================================
echo       INITIALIZING JARVIS AI ASSISTANT
echo ===================================================
echo.
python main.py
if errorlevel 1 (
    echo.
    echo An error occurred. Please run install_requirements.bat first.
    pause
)
