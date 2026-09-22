@echo off
REM Build the standalone one-file executable (dist\GCM_Platform.exe).
setlocal
cd /d "%~dp0"
echo [1/3] Installing build dependencies...
python -m pip install -r requirements.txt --quiet --disable-pip-version-check
echo [2/3] Rebuilding offline stylesheet...
call build_assets.bat
echo [3/3] Running PyInstaller...
python -m PyInstaller GCM_Platform.spec --clean -y
if errorlevel 1 (echo Build FAILED & exit /b 1)
echo.
echo Done: dist\GCM_Platform.exe
endlocal
