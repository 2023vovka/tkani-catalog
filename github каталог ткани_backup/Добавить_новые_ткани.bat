@echo off
echo ========================================================
echo       ADDING NEW FABRICS DEDAR AND MARIAFLORA
echo ========================================================
echo.
echo Running automation script...
echo.
call "%~dp0\.venv\Scripts\python.exe" "%~dp0\scripts\run_all_automation.py"
echo.
echo ========================================================
echo Done! You can close this window.
pause
