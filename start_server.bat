@echo off
cd "C:\Users\yoshiaki\Desktop\Travel App\Travel App"

echo Checking for processes on port 8000...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000 "') do (
    echo Killing PID %%a on port 8000...
    taskkill /PID %%a /F >nul 2>&1
)

:loop
echo Starting server...
python -m uvicorn main:app --host 0.0.0.0 --port 8000
echo Server stopped. Restarting in 3 seconds...
timeout /t 3 >nul
goto loop
