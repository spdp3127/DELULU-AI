@echo off
title Push DELULU to GitHub (spdp3127)
echo ========================================================
echo       UPLOADING DELULU AI TO GITHUB (spdp3127)
echo ========================================================
echo.
echo NOTE: If a code appears below:
echo 1. Open Google Chrome (where your spdp3127 account is logged in).
echo 2. Go to: https://github.com/login/device
echo 3. Enter the 8-character code and click Authorize.
echo ========================================================
echo.
git push -u origin main
echo.
if errorlevel 1 (
    echo [ERROR] Push failed. Please check your login or network.
) else (
    echo [SUCCESS] DELULU AI uploaded successfully to https://github.com/spdp3127/DELULU-AI
)
echo.
pause
