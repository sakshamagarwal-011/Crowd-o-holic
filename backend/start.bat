@echo off
echo Starting Crowd Flow Optimiser Backend...
echo.
echo Backend URL: http://localhost:8000
echo WebSocket:   ws://localhost:8000/ws/simulations/default
echo API Docs:    http://localhost:8000/docs
echo Health:      http://localhost:8000/health
echo.
cd /d "%~dp0"
.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
