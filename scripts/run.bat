@echo off
REM Start Voicewright from source on Windows. Creates a venv on first run.
cd /d "%~dp0\.."
if not exist .venv (
  py -3 -m venv .venv
  .venv\Scripts\python -m pip install --upgrade pip
  .venv\Scripts\pip install -e .
)
start "" .venv\Scripts\pythonw -m voicewright %*
