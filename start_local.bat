@echo off
echo =========================================
echo Starting Autonomous Career Advisor Locally
echo =========================================

echo.
echo Starting FastAPI Backend...
start cmd /k "cd backend && call .venv\Scripts\activate && python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8080"

echo.
echo Starting Vite Frontend...
start cmd /k "cd frontend && npm run dev"

echo.
echo Both servers are starting up in new windows!
echo Once they are ready, you can access the application at:
echo http://localhost:5173
echo.
pause
