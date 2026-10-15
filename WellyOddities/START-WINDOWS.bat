@echo off
cd /d "%~dp0"
where py >nul 2>&1
if %ERRORLEVEL% EQU 0 (set PY=py) else (set PY=python)
%PY% -m pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo Unable to install Python packages. Install Python from python.org and rerun.
  pause
  exit /b 1
)
%PY% server.py
pause
