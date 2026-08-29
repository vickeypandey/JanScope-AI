@echo off
setlocal
cd /d "%~dp0"
set "JANSCOPE_PY="
py -3.13 --version >nul 2>&1
if not errorlevel 1 set "JANSCOPE_PY=py -3.13"
if defined JANSCOPE_PY goto :python_ready
py -3.12 --version >nul 2>&1
if not errorlevel 1 set "JANSCOPE_PY=py -3.12"
if defined JANSCOPE_PY goto :python_ready
python --version >nul 2>&1
if not errorlevel 1 set "JANSCOPE_PY=python"
if defined JANSCOPE_PY goto :python_ready
python3 --version >nul 2>&1
if not errorlevel 1 set "JANSCOPE_PY=python3"
if defined JANSCOPE_PY goto :python_ready
echo Python was not found through py, python, or python3.
pause
exit /b 1
:python_ready
%JANSCOPE_PY% --version
%JANSCOPE_PY% -c "import sys; raise SystemExit(0 if sys.version_info[:2] in ((3, 12), (3, 13)) else 1)"
if errorlevel 1 (
  echo JanScope requires Python 3.12 or 3.13.
  pause
  exit /b 1
)
%JANSCOPE_PY% -m venv .venv
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements-lite.txt
if not exist ".env" copy ".env.example" ".env" >nul
".venv\Scripts\python.exe" scripts\init_db.py
echo Lightweight demo setup completed. VECTOR_BACKEND automatically falls back to memory.
pause
