@echo off
REM Runs every automated test: crisis engine, fusion, prosody, API, conversation (4 languages),
REM real AI models (needs models_cache) and - if Node.js is installed - the face-logic tests.
cd /d "%~dp0.."
".venv\Scripts\python.exe" -m pytest backend\tests -v -p no:cacheprovider
where node >nul 2>nul && node frontend\tests\faceLogic.test.ts
pause
