@echo off
title Storage & Memory GCM Platform
echo ================================================================
echo   Storage & Memory Global Compliance Management (GCM) Platform
echo   205 Countries & Territories ^| 11 Storage Product Categories
echo   Product-Based Testing vs Document Matrix ^| Excel Exporter
echo ================================================================
echo.
echo [1/2] Verifying Python dependencies (Flask, OpenPyXL)...
pip install -r requirements.txt --quiet
echo.
echo [2/2] Launching GCM Platform at http://localhost:5000 ...
start http://localhost:5000
python app.py
pause
