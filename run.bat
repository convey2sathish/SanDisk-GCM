@echo off
title GCM Platform 2.0
cd /d "%~dp0"
echo ================================================================
echo   Storage ^& Memory Global Compliance Management (GCM) Platform
echo   v2.0 "Horizon" - 205 jurisdictions ^| 11 product categories
echo   Safety ^| EMC ^| Environmental ^| Cyber - works fully offline
echo ================================================================
echo.
echo [1/2] Checking Python dependencies...
python -m pip install -r requirements.txt --quiet --disable-pip-version-check
if errorlevel 1 (
  echo   Dependency installation failed. Make sure Python 3.10+ and pip are installed.
  pause
  exit /b 1
)
echo.
echo [2/2] Starting the platform (the browser opens automatically)...
echo       Press Ctrl+C in this window to stop.
python app.py
pause
