@echo off
rem Run an engine script with the project's Python environment, creating the
rem environment on first use. Windows twin of the "py" script.
setlocal
set SCRIPT_DIR=%~dp0
for %%I in ("%SCRIPT_DIR%..\..\..\..") do set REPO_ROOT=%%~fI
set VENV=%REPO_ROOT%\.venv
set PYTHON=%VENV%\Scripts\python.exe

if not exist "%PYTHON%" (
  echo creating project Python environment in .venv ... 1>&2
  python -m venv "%VENV%" || exit /b 1
  "%PYTHON%" -m pip install --quiet --upgrade pip || exit /b 1
  "%PYTHON%" -m pip install --quiet -r "%SCRIPT_DIR%..\requirements.txt" || exit /b 1
)

"%PYTHON%" %*
