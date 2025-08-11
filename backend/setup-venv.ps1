# PowerShell script to setup virtual environment for the backend
Write-Host "Setting up Python virtual environment..." -ForegroundColor Green

# Check if .venv exists
if (Test-Path ".venv") {
    Write-Host "Virtual environment already exists." -ForegroundColor Yellow
} else {
    Write-Host "Creating virtual environment..." -ForegroundColor Blue
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to create virtual environment. Make sure Python is installed."
        exit 1
    }
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Blue
& ".\.venv\Scripts\Activate.ps1"

# Install dependencies
Write-Host "Installing dependencies..." -ForegroundColor Blue
pip install -r requirements.txt

if ($LASTEXITCODE -eq 0) {
    Write-Host "Backend setup completed successfully!" -ForegroundColor Green
} else {
    Write-Error "Failed to install dependencies."
    exit 1
}
