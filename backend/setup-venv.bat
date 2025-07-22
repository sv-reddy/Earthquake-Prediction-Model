@echo off
echo Setting up Python virtual environment...

REM Check if .venv exists
if exist ".venv" (
    echo Virtual environment already exists.
) else (
    echo Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo Failed to create virtual environment. Make sure Python is installed.
        exit /b 1
    )
)

REM Activate virtual environment
echo Activating virtual environment...
call ".venv\Scripts\activate.bat"

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt

if errorlevel 0 (
    echo Backend setup completed successfully!
) else (
    echo Failed to install dependencies.
    exit /b 1
)
