@echo off
setlocal

where py >nul 2>nul
if %errorlevel% equ 0 (
    set "PYTHON=py"
) else (
    set "PYTHON=python"
    where python >nul 2>nul
    if errorlevel 1 (
        echo Python не найден. Установите Python 3.10+ и включите Add python.exe to PATH.
        exit /b 1
    )
)

if "%~1"=="" (
    echo Использование: install_and_run.bat photo.png
    echo Или: install_and_run.bat photos
    exit /b 0
)

%PYTHON% "%~dp0remove_bg.py" %*
