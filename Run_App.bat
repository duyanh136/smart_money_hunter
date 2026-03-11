@echo off
pushd "%~dp0"

echo ----------------------------------------
echo Starting Smart Money Hunter Application
echo ----------------------------------------

REM Kiem tra xem thu muc venv da ton tai chua, chua co thi tao moi
if not exist venv (
    echo [1/3] Creating Python Virtual Environment. Please wait...
    python -m venv venv
    if errorlevel 1 (
        echo Error: Khong the tao Virtual Environment. Dam bao ban da cai Python va them vao PATH.
        pause
        exit /b 1
    )
)

echo [2/3] Cheking and installing missing dependencies...
"%~dp0venv\Scripts\python.exe" -m pip install --upgrade pip >nul 2>&1
"%~dp0venv\Scripts\pip.exe" install -r requirements.txt

echo.
echo ========================================
echo SERVER IS RUNNING
echo Access at http://127.0.0.1:5000
echo ========================================

echo Starting Git Auto-Sync in background...
start "" "%~dp0venv\Scripts\python.exe" git_auto_sync.py

"%~dp0venv\Scripts\python.exe" app.py
pause
