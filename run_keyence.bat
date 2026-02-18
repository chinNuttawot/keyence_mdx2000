@echo off
REM Keyence MD-X2000 Communication Script - Windows Startup Batch
REM This script runs the Python monitoring in continuous mode using venv

REM Set the project directory
set PROJECT_DIR=C:\Users\Worrakirs Boonchan\.gemini\antigravity\scratch\keyence_mdx2000

REM Change to project directory
cd /d "%PROJECT_DIR%"

REM Run the Python script using venv in continuous mode
call "%PROJECT_DIR%\venv\Scripts\python.exe" main.py --continuous

REM If Python crashes, wait and display error
if %ERRORLEVEL% NEQ 0 (
    echo Error occurred. Press any key to exit...
    pause
)

