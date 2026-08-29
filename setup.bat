@echo off
setlocal
cd /d "%~dp0"

echo [1/5] Checking Python 3.13 or 3.12...
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
echo Install Python 3.13 or 3.12 from https://www.python.org/downloads/
echo and select "Add Python to PATH" during installation.
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

echo [2/5] Creating virtual environment...
if not exist ".venv\Scripts\python.exe" %JANSCOPE_PY% -m venv .venv
if errorlevel 1 goto :failed

echo [3/5] Updating pip...
".venv\Scripts\python.exe" -m pip install --upgrade pip setuptools wheel
if errorlevel 1 goto :failed

echo [4/5] Installing JanScope dependencies. This can take several minutes...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :failed

echo [5/5] Preparing environment, database, and vector index...
if not exist ".env" copy ".env.example" ".env" >nul
".venv\Scripts\python.exe" scripts\init_db.py
if errorlevel 1 goto :failed

echo.
echo Setup completed successfully.
echo Run run_all.bat and open http://127.0.0.1:8501
pause
exit /b 0

:failed
echo.
echo Setup failed. Read START_HERE.md and copy the last error message.
pause
exit /b 1
