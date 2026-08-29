@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Run setup.bat first.
  pause
  exit /b 1
)
start "JanScope Backend" cmd /k "call run_backend.bat"
timeout /t 4 /nobreak >nul
start "JanScope Frontend" cmd /k "call run_frontend.bat"
echo Backend and frontend are starting in separate windows.
echo Open http://127.0.0.1:8501 if the browser does not open automatically.
