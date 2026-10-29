@echo off
setlocal
cd /d "%~dp0"
set "REVIKNOT_PYTHON=python"
if exist ".venv\Scripts\python.exe" set "REVIKNOT_PYTHON=%~dp0.venv\Scripts\python.exe"
if exist ".venv-dev\Scripts\python.exe" set "REVIKNOT_PYTHON=%~dp0.venv-dev\Scripts\python.exe"
"%REVIKNOT_PYTHON%" -m patchcourt.launcher
if errorlevel 1 (
  echo.
  echo Could not start ReviKnot. Python 3.10+ is required. A free local port is selected automatically.
  pause
)
endlocal
