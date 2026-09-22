@echo off
REM Rebuild the offline Tailwind stylesheet (static\css\app.css) from templates + JS.
REM Requires Node.js. First run installs the Tailwind CLI into tools\node_modules.
setlocal
cd /d "%~dp0"
if not exist tools\node_modules\.bin\tailwindcss.cmd (
  echo [1/2] Installing Tailwind CSS v4 CLI into tools\ ...
  pushd tools
  call npm install --no-audit --no-fund --loglevel=error
  popd
)
echo [2/2] Compiling static\css\app.css ...
call tools\node_modules\.bin\tailwindcss.cmd -i static\css\tailwind.src.css -o static\css\app.css --minify
if errorlevel 1 (echo Build FAILED & exit /b 1)
echo Done. static\css\app.css is ready for offline use.
endlocal
