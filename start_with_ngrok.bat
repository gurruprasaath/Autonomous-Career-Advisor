@echo off
setlocal

cd /d "%~dp0"

echo ==========================================
echo Starting Project Servers
echo ==========================================

echo [1/3] Launching Backend (FastAPI)...
start "Backend - FastAPI" cmd /k "cd backend && call .venv\Scripts\activate && uvicorn app.main:app --reload --port 8080"

echo [2/3] Launching Frontend (Vite)...
if not exist "frontend\node_modules" (
    echo       node_modules missing - running npm install first ^(one-time, may take a minute^)...
    start "Frontend - Vite" cmd /k "cd frontend && npm install && npm run dev"
) else (
    start "Frontend - Vite" cmd /k "cd frontend && npm run dev"
)

echo [3/3] Launching ngrok for Frontend (Port 5173)...
:: Using the domain specified in vite.config.js allowedHosts
start "ngrok - Frontend" cmd /k "ngrok http --domain=upscale-crumpled-siren.ngrok-free.dev 5173"

echo.
echo All servers are starting in separate terminal windows.
echo   Backend:  http://localhost:8000
echo   Frontend: http://localhost:5173
echo   ngrok:    Check the ngrok window for the public URL
echo.
pause
