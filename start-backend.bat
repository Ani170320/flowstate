@echo off
echo =======================================================
echo Starting FLOWSTATE FastAPI Backend on http://localhost:8000
echo =======================================================
cd /d "%~dp0"
set PYTHONPATH=backend
backend\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
