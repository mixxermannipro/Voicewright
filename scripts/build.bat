@echo off
REM Local release build on Windows. Output: dist\Voicewright\Voicewright.exe
cd /d "%~dp0\.."
py -3 -m venv .venv-build
.venv-build\Scripts\python -m pip install --upgrade pip
.venv-build\Scripts\pip install -r requirements-dev.txt
.venv-build\Scripts\pyinstaller --noconfirm voicewright.spec
echo Build finished: dist\Voicewright
