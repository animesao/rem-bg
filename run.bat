@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Run setup_once.bat once before starting the app.
    pause
    exit /b 1
)

if not exist "models\u2net.onnx" (
    echo The u2net model was not found. Run setup_once.bat once first.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" "%~dp0background_remover_app.py"
