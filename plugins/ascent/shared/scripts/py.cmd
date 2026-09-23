@echo off
rem Run a workspace engine script with the Opportunity's Python environment.
rem Set EAD_REPO_ROOT when the installed skill library lives elsewhere.
setlocal
set SCRIPT_DIR=%~dp0
python "%SCRIPT_DIR%launcher_preflight.py" %* || exit /b 2
set REPO_ROOT=%EAD_REPO_ROOT%
set VENV=%REPO_ROOT%\workspace\.system\.venv
set PYTHON=%VENV%\Scripts\python.exe

python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" || (
  echo Python 3.10 or newer is required. 1>&2
  exit /b 1
)

if not exist "%PYTHON%" (
  echo creating workspace Python environment in workspace\.system\.venv ... 1>&2
  python -m venv "%VENV%" || exit /b 1
  "%PYTHON%" -m pip install --quiet --upgrade pip || exit /b 1
  "%PYTHON%" -m pip install --quiet -r "%SCRIPT_DIR%..\requirements.txt" || exit /b 1
)

"%PYTHON%" %*
