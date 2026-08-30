$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

if (-not (Test-Path '.env')) {
    Copy-Item '.env.example' '.env'
    Write-Host 'Created .env. Add your FORTYGUARD_API_KEY to it, then run this script again.' -ForegroundColor Yellow
    exit 1
}

.\.venv\Scripts\python.exe scripts\fetch_fortyguard.py
