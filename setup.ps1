# Khidmati Iraq Backend – Setup Script
# Run this from the project root: .\setup.ps1

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "`n=== Khidmati Iraq – Setup ===" -ForegroundColor Cyan

# 1. Create virtual environment
if (-not (Test-Path ".venv")) {
    Write-Host "`n[1/5] Creating virtual environment..." -ForegroundColor Yellow
    python -m venv .venv
} else {
    Write-Host "`n[1/5] Virtual environment already exists, skipping." -ForegroundColor Green
}

# 2. Activate virtual environment
Write-Host "`n[2/5] Activating virtual environment..." -ForegroundColor Yellow
. .\.venv\Scripts\Activate.ps1

# 3. Upgrade pip
Write-Host "`n[3/5] Upgrading pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip

# 4. Install dependencies
Write-Host "`n[4/5] Installing dependencies from requirements.txt..." -ForegroundColor Yellow
pip install -r requirements.txt

# 5. Create .env if it does not exist
Write-Host "`n[5/5] Setting up environment file..." -ForegroundColor Yellow
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "  .env created from .env.example" -ForegroundColor Green
    Write-Host "  IMPORTANT: Edit .env and set a strong JWT_SECRET_KEY before running in production." -ForegroundColor Red
} else {
    Write-Host "  .env already exists, skipping." -ForegroundColor Green
}

Write-Host "`n=== Setup complete! ===" -ForegroundColor Cyan
Write-Host "`nNext steps:" -ForegroundColor White
Write-Host "  1. Create the PostgreSQL database:" -ForegroundColor White
Write-Host "       psql -U postgres -c `"CREATE DATABASE khidmati_iraq;`"" -ForegroundColor DarkGray
Write-Host "  2. Create the test database:" -ForegroundColor White
Write-Host "       psql -U postgres -c `"CREATE DATABASE khidmati_iraq_test;`"" -ForegroundColor DarkGray
Write-Host "  3. Edit .env with your settings." -ForegroundColor White
Write-Host "  4. Run migrations:" -ForegroundColor White
Write-Host "       alembic upgrade head" -ForegroundColor DarkGray
Write-Host "  5. Seed the database:" -ForegroundColor White
Write-Host "       python -m scripts.seed" -ForegroundColor DarkGray
Write-Host "  6. Start the server:" -ForegroundColor White
Write-Host "       uvicorn app.main:app --reload" -ForegroundColor DarkGray
Write-Host ""
