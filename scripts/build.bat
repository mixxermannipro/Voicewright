@echo off
REM Local release build on Windows.
REM Output: dist\Voicewright\Voicewright.exe, release\*.zip, release\*.exe and SHA-256 files.
setlocal EnableExtensions
cd /d "%~dp0\.."

if not exist ".venv-build\Scripts\python.exe" (
    py -3 -m venv .venv-build || goto :error
)
".venv-build\Scripts\python.exe" -m pip install --upgrade pip || goto :error
".venv-build\Scripts\python.exe" -m pip install -r requirements-dev.txt || goto :error
".venv-build\Scripts\python.exe" -m pip check || goto :error
".venv-build\Scripts\python.exe" -m pytest -q || goto :error

set "VERSION="
for /f "usebackq delims=" %%v in (`".venv-build\Scripts\python.exe" -c "import sys; sys.path.insert(0, 'src'); from voicewright import __version__; print(__version__)"`) do set "VERSION=%%v"
if not defined VERSION goto :error
echo Building Voicewright %VERSION%

".venv-build\Scripts\pyinstaller.exe" --noconfirm --clean voicewright.spec || goto :error

if not exist release mkdir release
set "ZIP=release\Voicewright-%VERSION%-windows-x64.zip"
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "Compress-Archive -Path 'dist\Voicewright\*' -DestinationPath '%ZIP%' -Force" || goto :error

set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if exist "%ISCC%" (
    "%ISCC%" "/DAppVersion=%VERSION%" "/DSourceDir=%CD%\dist\Voicewright" "/DOutputDir=%CD%\release" packaging\windows\voicewright.iss || goto :error
) else (
    echo Inno Setup 6 not found - skipping the installer.
)

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "Get-ChildItem release\Voicewright-%VERSION%-windows-x64* -File | Where-Object { $_.Extension -in '.zip','.exe' } | ForEach-Object { $h = (Get-FileHash $_.FullName -Algorithm SHA256).Hash.ToLower(); [IO.File]::WriteAllText($_.FullName + '.sha256', $h + '  ' + $_.Name + [char]10) }" || goto :error

echo Build finished: dist\Voicewright and release\
exit /b 0

:error
echo Build failed with exit code %errorlevel%.
exit /b %errorlevel%
