@echo off
echo ==========================================
echo Setup Environment for Fabric Database CRM
echo ==========================================

REM Check if Python is installed
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo Python is not installed or not added to PATH.
    echo Please install Python 3.10+ from python.org and try again.
    pause
    exit /b 1
)

REM Create virtual environment if it doesn't exist
IF NOT EXIST ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
) ELSE (
    echo Virtual environment already exists.
)

REM Activate virtual environment and install requirements
echo Installing dependencies...
call .venv\Scripts\activate.bat
pip install --upgrade pip
pip install -r requirements.txt

REM Install playwright browsers as they might be required for scrapers
echo Installing Playwright browsers...
playwright install

echo ==========================================
echo Setup Complete! 
echo You can now run 'Запуск_Каталога.vbs' or 'run_app.bat'
echo ==========================================
pause
