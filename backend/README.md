# Backend Setup Instructions

This backend runs a FastAPI server for the earthquake prediction web application.

## Quick Start

### Option 1: Using npm scripts (Recommended)
From the root directory:
```bash
# Setup backend virtual environment (run once)
npm run setup-backend

# Run both frontend and backend concurrently
npm run dev
```

### Option 2: Manual setup
From the backend directory:

**Using PowerShell:**
```powershell
# Setup virtual environment
.\setup-venv.ps1

# Start backend server
.\start-backend.ps1
```

**Using Command Prompt:**
```cmd
# Setup virtual environment
setup-venv.bat

# Start backend server
start-backend.bat
```

## What happens during setup:
1. Creates a Python virtual environment (`.venv`)
2. Activates the virtual environment
3. Installs all dependencies from `requirements.txt`
4. Starts the FastAPI server on `http://localhost:8000`

## Dependencies
- Python 3.7+
- FastAPI
- Uvicorn
- Other packages listed in `requirements.txt`

## API Endpoints
The backend provides various endpoints for:
- Earthquake data analysis
- Tectonic plate information
- GNSS data processing
- Risk assessment calculations

Server runs on: `http://localhost:8000`
API documentation available at: `http://localhost:8000/docs`

## Troubleshooting

### PowerShell Execution Policy Issues
If you get execution policy errors, run PowerShell as Administrator and execute:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Or use the batch file alternatives:
```bash
npm run backend-batch
npm run setup-backend-batch
```

### Python Virtual Environment Issues
- Ensure Python is installed and available in PATH
- Delete `.venv` folder and run setup again if corrupted
- Check that `pip` is available and working
