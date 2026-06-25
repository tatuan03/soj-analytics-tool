@echo off
title SOJ Analytics Tool
echo ==========================================
echo Starting SOJ Analytics Tool
echo ==========================================

echo.
echo [1/3] Starting Frontend server on port 8080...
start "Frontend Server" cmd /c "python -m http.server 8080"
timeout /t 2 /nobreak > NUL

echo.
echo [2/3] Setting up Backend environment...
cd backend
if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
)

echo Activating virtual environment...
call .venv\Scripts\activate.bat

echo Installing dependencies...
pip install -r requirements.txt

if not exist ".env" (
    echo Creating .env file from template...
    copy .env.example .env
)

echo.
echo ==========================================
echo [3/3] Starting Backend server on port 8000...
echo.
echo System is starting up:
echo - Frontend: http://127.0.0.1:8080/index.html
echo - Backend API: http://127.0.0.1:8000/docs
echo ==========================================
uvicorn app.main:app --reload
