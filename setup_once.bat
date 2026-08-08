@echo off
setlocal EnableExtensions
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel% equ 0 (
    set "PYTHON=py"
) else (
    set "PYTHON=python"
    where python >nul 2>nul
    if errorlevel 1 (
        echo Python was not found.
        echo Install Python 3.10+ from https://www.python.org/downloads/
        echo Enable Add python.exe to PATH during installation.
        pause
        exit /b 1
    )
)

if not exist ".venv\Scripts\python.exe" (
    echo [1/3] Creating virtual environment...
    %PYTHON% -m venv .venv
    if errorlevel 1 goto :error
)

set "VPYTHON=%~dp0.venv\Scripts\python.exe"

echo [2/3] Installing dependencies...
"%VPYTHON%" -m pip install --upgrade pip
if errorlevel 1 goto :error
"%VPYTHON%" -m pip install -r requirements.txt
if errorlevel 1 goto :error

if not exist "models" mkdir models

echo [3/3] Downloading the u2net model...
"%VPYTHON%" -c "import os; os.environ['U2NET_HOME']=os.path.abspath('models'); from rembg import new_session; new_session('u2net')"
if errorlevel 1 goto :error

if not exist "output" mkdir output

echo.
echo Setup completed.
echo Internet is not required for future use.
echo Start the app with run.bat
echo.
pause
exit /b 0

:error
echo.
echo Setup failed. Check your internet connection and the message above.
pause
exit /b 1
