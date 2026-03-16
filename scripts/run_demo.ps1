$ErrorActionPreference = "Stop"

if (-not (Test-Path .\.venv\Scripts\python.exe)) {
    Write-Error "Create the virtual environment first with scripts/bootstrap.ps1"
}

.\.venv\Scripts\streamlit.exe run app.py

