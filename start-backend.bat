@echo off
cd /d "%~dp0backend"
if not exist .venv (
  py -3.11 -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -e .
uvicorn app.main:app --reload --port 8000
cd C:\Users\Saksham\Downloads\cctvCrowd_flow_optimiser-main\Crowd_flow_optimiser-main\frontend
