@echo off
REM Only needed if you CHANGE the dashboard code in frontend\src. Requires Node.js 18+.
cd /d "%~dp0..\frontend"
if not exist node_modules call npm install
call npm run build
echo Built into frontend\dist - restart run.bat to see changes.
pause
