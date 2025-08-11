# PowerShell script to run the backend server
Write-Host "Starting backend server..." -ForegroundColor Green

# Check if virtual environment exists
if (-not (Test-Path ".venv")) {
    Write-Host "Virtual environment not found. Setting up..." -ForegroundColor Yellow
    $scriptPath = Join-Path $PSScriptRoot "setup-venv.ps1"
    & $scriptPath
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to setup virtual environment."
        exit 1
    }
}

# Activate virtual environment
& ".\.venv\Scripts\Activate.ps1"

# Check if main.py exists
if (-not (Test-Path "main.py")) {
    Write-Error "main.py not found in backend directory."
    exit 1
}

# Start the FastAPI server
Write-Host "Starting FastAPI server on http://localhost:8000" -ForegroundColor Blue
python main.py
