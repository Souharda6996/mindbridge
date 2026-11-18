@echo off
REM ============================================================
REM  MindBridge - one-time setup on a new Windows PC
REM  Needs: Python 3.10-3.12 (python.org, tick "Add to PATH")
REM  Node.js is NOT needed (the dashboard is pre-built in frontend\dist)
REM ============================================================
setlocal
cd /d "%~dp0.."
echo.
echo [1/4] Creating Python virtual environment (.venv)...
if not exist ".venv\Scripts\python.exe" (
    python -m venv .venv || (echo Python not found. Install Python 3.12 from python.org and tick "Add to PATH". & pause & exit /b 1)
)
echo [2/4] Installing PyTorch (CPU build, ~200 MB)...
".venv\Scripts\python.exe" -m pip install --upgrade pip -q
".venv\Scripts\python.exe" -m pip install torch --index-url https://download.pytorch.org/whl/cpu -q || (echo PyTorch install failed - check internet. & pause & exit /b 1)
echo [3/4] Installing backend packages...
".venv\Scripts\python.exe" -m pip install -r backend\requirements.txt -q || (echo Package install failed. & pause & exit /b 1)
echo [4/4] Downloading 4 AI models into models_cache (~2.5 GB, skipped if already present)...
if exist "models_cache\.models_ready" (
    echo        models already present - skipping download
) else (
    ".venv\Scripts\python.exe" scripts\download_models.py
)
if not exist ".env" copy ".env.example" ".env" >nul
echo.
echo Setup complete. Start MindBridge with scripts\run.bat
pause
