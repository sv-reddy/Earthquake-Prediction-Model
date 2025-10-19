@echo off
echo Starting backend server...

REM Check if virtual environment exists
if not exist ".venv" (
    echo Virtual environment not found. Setting up...
    call setup-venv.bat
    if errorlevel 1 (
        echo Failed to setup virtual environment.
        exit /b 1
    )
)

REM Activate virtual environment
call ".venv\Scripts\activate.bat"

REM Check if main.py exists
if not exist "main.py" (
    echo main.py not found in backend directory.
    exit /b 1
)

REM Start the FastAPI server
echo Starting FastAPI server on http://localhost:8000
python main.py
