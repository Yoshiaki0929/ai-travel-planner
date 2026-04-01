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
echo Server stopped. Checking in 3 seconds...
timeout /t 3 >nul

REM ポート8000が他のプロセスに使われていたら別インスタンスが起動済み → このウィンドウを閉じる
netstat -ano | findstr ":8000 " >nul 2>&1
if %errorlevel% == 0 (
    echo Another server instance is running. Closing this window.
    timeout /t 2 >nul
    exit /b 0
)

goto loop
