@echo off
rem Run a workspace engine script with a per-user environment outside the
rem synced Opportunity folder. ASCENT_PYTHON can pin the base interpreter.
setlocal EnableExtensions
set "SCRIPT_DIR=%~dp0"
if defined ASCENT_OPPORTUNITY_ROOT (
  set "OPPORTUNITY_ROOT=%ASCENT_OPPORTUNITY_ROOT%"
) else (
  set "OPPORTUNITY_ROOT=%CD%"
)
set "INSTALL_DEPENDENCIES=0"
if "%~1"=="--install-dependencies" (
  set "INSTALL_DEPENDENCIES=1"
  shift
)

if defined ASCENT_PYTHON (
  set "BASE_PYTHON=%ASCENT_PYTHON%"
) else (
  where python3 >nul 2>&1 && (set "BASE_PYTHON=python3") || (set "BASE_PYTHON=python")
)
"%BASE_PYTHON%" -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" || (
  echo Python 3.10 or newer is required. ASCENT_PYTHON resolved to: %BASE_PYTHON% 1>&2
  exit /b 1
)

for /f "usebackq delims=" %%I in (`"%BASE_PYTHON%" -c "import pathlib,sys; print(pathlib.Path(sys.argv[1]).expanduser().resolve())" "%OPPORTUNITY_ROOT%"`) do set "OPPORTUNITY_ROOT=%%I"
set "ASCENT_OPPORTUNITY_ROOT=%OPPORTUNITY_ROOT%"
"%BASE_PYTHON%" "%SCRIPT_DIR%launcher_preflight.py" %* || exit /b 2
for /f "usebackq delims=" %%I in (`"%BASE_PYTHON%" -c "import hashlib,os,sys; value=os.path.normcase(os.path.realpath(sys.argv[1])).encode('utf-8'); print(hashlib.sha256(value).hexdigest()[:20])" "%OPPORTUNITY_ROOT%"`) do set "PATH_HASH=%%I"
if defined ASCENT_CACHE_DIR (set "CACHE_ROOT=%ASCENT_CACHE_DIR%") else (set "CACHE_ROOT=%USERPROFILE%\.ascent")
set "VENV=%CACHE_ROOT%\venvs\%PATH_HASH%"
set "PYTHON=%VENV%\Scripts\python.exe"
set "SYSTEM_DIR=%OPPORTUNITY_ROOT%\workspace\.system"

if not exist "%PYTHON%" (
  echo creating cached Python environment: %VENV% 1>&2
  "%BASE_PYTHON%" -m venv "%VENV%" || exit /b 1
)
if not exist "%SYSTEM_DIR%" mkdir "%SYSTEM_DIR%" || exit /b 1
>"%SYSTEM_DIR%\.venv-path" echo %VENV%

if "%INSTALL_DEPENDENCIES%"=="1" (
  echo installing Ascent Python dependencies into: %VENV% 1>&2
  "%PYTHON%" -m pip install -r "%SCRIPT_DIR%..\requirements.txt" || exit /b 1
) else (
  "%PYTHON%" -c "import docx, fitz, openpyxl, pptx, yaml" >nul 2>&1 || (
    echo Ascent Python dependencies are not installed in %VENV%. 1>&2
    echo After getting approval to install them, rerun this command with --install-dependencies before the script and its arguments. 1>&2
    exit /b 2
  )
)

"%PYTHON%" %*
