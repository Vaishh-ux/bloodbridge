@echo off
REM Double-click this file (or run it from the backend folder) to start the Blood Bridge API.
cd /d "%~dp0"
if not exist .venv (
  echo Creating virtual environment...
  py -m venv .venv 2>nul || python -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install -r requirements.txt
echo.
echo Starting API on http://localhost:8000  (docs: http://localhost:8000/docs)
python -m uvicorn app.main:app --reload --port 8000
pause
