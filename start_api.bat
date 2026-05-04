@echo off
REM Quick Start Script for DevOps Log Analyzer API (Windows)

setlocal enabledelayedexpansion

cls
echo ================================================================================
echo DevOps Log Analyzer - API Quick Start
echo ================================================================================
echo.

REM 1. Check Python
echo [1/5] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version') do set PYTHON_VERSION=%%i
echo OK - %PYTHON_VERSION%
echo.

REM 2. Check Ollama
echo [2/5] Checking Ollama service...
powershell -Command "try { $response = Invoke-WebRequest -Uri 'http://localhost:11434/api/tags' -UseBasicParsing; if ($response.StatusCode -eq 200) { Write-Host 'OK - Ollama is running' } } catch { Write-Host 'WARNING: Ollama may not be running. Start with: ollama serve' }"
echo.

REM 3. Install dependencies
echo [3/5] Installing Python dependencies...
if exist "requirements.txt" (
    python -m pip install -r requirements.txt --quiet
    echo OK - Dependencies installed
) else (
    echo ERROR: requirements.txt not found
    pause
    exit /b 1
)
echo.

REM 4. Create directories
echo [4/5] Setting up directories...
if not exist "data\logs" mkdir data\logs
if not exist "vector_db" mkdir vector_db
echo OK - Directories ready
echo.

REM 5. Start FastAPI server
echo [5/5] Starting FastAPI server...
echo.
echo OK - Server starting on http://localhost:8000
echo.
echo Endpoints:
echo   API Docs:   http://localhost:8000/docs
echo   ReDoc:      http://localhost:8000/redoc
echo.
echo Test the API:
echo   Health Check: http://localhost:8000/health
echo   Test Suite:   python test_api.py
echo.
echo Press Ctrl+C to stop
echo.

python -m uvicorn main_api:app --host 0.0.0.0 --port 8000 --reload

pause
