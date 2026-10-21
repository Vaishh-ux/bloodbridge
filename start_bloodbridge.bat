@echo off
REM Blood Bridge - one-click start for Windows (no VS Code needed).
REM Put this file in the BloodBridge folder (the one that contains "backend" and "frontend")
REM and double-click it. Two windows open: keep both open while using the site.
cd /d "%~dp0"

if not exist backend\requirements.txt (
  echo Could not find the backend folder. Put this file inside the BloodBridge folder.
  pause
  exit /b 1
)

REM ---- Backend window ----
start "Blood Bridge - Backend" cmd /k "cd /d "%~dp0backend" && (if not exist .venv (py -m venv .venv 2>nul || python -m venv .venv)) && call .venv\Scripts\activate.bat && python -m pip install -q -r requirements.txt && python -m uvicorn app.main:app --port 8000"

REM ---- Frontend window ----
start "Blood Bridge - Frontend" cmd /k "cd /d "%~dp0frontend" && (if not exist node_modules npm install) && npm run dev"

echo Starting... the site will open in your browser in about 20 seconds.
timeout /t 20 /nobreak >nul
start "" http://localhost:5173
