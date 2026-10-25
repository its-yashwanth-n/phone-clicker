@echo off
rem Double-click to start Phone Clicker on Windows.
cd /d "%~dp0"
if not exist .venv (
  echo Setting up for the first time...
  python -m venv .venv || goto :error
)
rem Quick when everything is already installed; picks up new dependencies after an update.
.venv\Scripts\python -m pip install -q --disable-pip-version-check -r requirements.txt || goto :error
.venv\Scripts\python server.py %*
pause
exit /b

:error
echo.
echo Setup failed. Make sure Python 3.9+ is installed from https://python.org
pause
