@echo off
REM ============================================================
REM  MindBridge - start the app, then open http://localhost:8000
REM  Use Google Chrome or Microsoft Edge (needed for voice mode).
REM ============================================================
setlocal
cd /d "%~dp0.."
if not exist ".venv\Scripts\python.exe" (
    echo First run scripts\setup.bat
    pause
    exit /b 1
)
echo Starting MindBridge on http://localhost:8000  (close this window to stop)
start "" http://localhost:8000
".venv\Scripts\python.exe" -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
pause
