@echo off
set BASE_DIR=%~dp0
cd /d "%BASE_DIR%"
start "" "http://localhost:8080/frontend/index.html"
"%BASE_DIR%.venv\Scripts\python.exe" -m uvicorn backend.main:app --port 8080 --host 0.0.0.0
