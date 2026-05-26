# Lobster Quant - Development Startup Script
# Launches both frontend (Next.js) and backend (FastAPI) concurrently

$ErrorActionPreference = "Stop"

# Color helpers
function Write-Color($text, $color = "White") {
    Write-Host $text -ForegroundColor $color
}

function Write-Banner($text) {
    Write-Host ""
    Write-Host "=" * 60 -ForegroundColor Cyan
    Write-Host "  $text" -ForegroundColor Cyan
    Write-Host "=" * 60 -ForegroundColor Cyan
    Write-Host ""
}

Write-Banner "Lobster Quant - Starting Development Environment"

$rootDir = $PSScriptRoot

# ─── Prerequisite Checks ───────────────────────────────────────────
$checks = @()

# Check Node.js (for frontend)
$nodeVersion = (node --version 2>$null)
if ($nodeVersion) {
    Write-Color "  [OK] Node.js $nodeVersion" Green
    $checks += $true
}
else {
    Write-Color "  [MISSING] Node.js not found. Install from https://nodejs.org" Red
    $checks += $false
}

# Check Python (for backend)
try {
    $pyVersion = python --version 2>&1
    Write-Color "  [OK] Python $($pyVersion -replace 'Python ','')" Green
    $checks += $true
}
catch {
    Write-Color "  [MISSING] Python not found. Install from https://python.org" Red
    $checks += $false
}

# Check npm dependencies (frontend)
if (-not (Test-Path "$rootDir\lobster-quant-web\node_modules")) {
    Write-Color "  [INSTALL] Frontend dependencies missing. Running npm install..." Yellow
    Push-Location "$rootDir\lobster-quant-web"
    npm install
    Pop-Location
    Write-Color "  [OK] Frontend dependencies installed" Green
}

# Check Python deps (backend) - quick check for uvicorn
$uvicornCheck = python -c "import uvicorn" 2>$null
if (-not $?) {
    Write-Color "  [INSTALL] Backend dependencies missing. Running pip install..." Yellow
    Push-Location "$rootDir\backend"
    pip install -r requirements.txt
    Pop-Location
    Write-Color "  [OK] Backend dependencies installed" Green
}

if ($checks -contains $false) {
    Write-Color ""
    Write-Color "Missing prerequisites. Please install them and try again." Red
    exit 1
}

Write-Host ""

# ─── Environment Variables ─────────────────────────────────────────
$env:PYTHONPATH = "$rootDir;$rootDir\lobster_quant"

# ─── Launch Backend ────────────────────────────────────────────────
Write-Color "  Launching Backend  → http://localhost:8000 (FastAPI)" Yellow
$backendJob = Start-Job -Name "LobsterQuant-Backend" -ScriptBlock {
    param($rootDir, $envPath)

    # Restore env vars inside the job
    $env:PYTHONPATH = $envPath

    Set-Location "$rootDir\backend"

    # Try uvicorn module first, then fall back to python -m uvicorn
    $uvicornCmd = Get-Command uvicorn -ErrorAction SilentlyContinue
    if ($uvicornCmd) {
        & uvicorn main:app --host 0.0.0.0 --port 8000 --reload 2>&1
    }
    else {
        python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload 2>&1
    }
} -ArgumentList $rootDir, "$rootDir;$rootDir\lobster_quant"

# Give backend a moment to start
Start-Sleep -Seconds 1.5

# ─── Launch Frontend ───────────────────────────────────────────────
Write-Color "  Launching Frontend → http://localhost:3000 (Next.js)" Yellow
$frontendJob = Start-Job -Name "LobsterQuant-Frontend" -ScriptBlock {
    param($rootDir)
    Set-Location "$rootDir\lobster-quant-web"
    npm run dev 2>&1
} -ArgumentList $rootDir

# Give frontend a moment to start
Start-Sleep -Seconds 2

Write-Host ""

# ─── Status Summary ────────────────────────────────────────────────
Write-Banner "Development Environment Ready"
Write-Color "  Frontend : http://localhost:3000" Green
Write-Color "  Backend  : http://localhost:8000" Green
Write-Color "  API Docs : http://localhost:8000/docs" Green
Write-Host ""
Write-Color "Press Ctrl+C to stop all services." Magenta
Write-Host ""

# ─── Wait & Cleanup on Ctrl+C ──────────────────────────────────────
try {
    # Block until user presses Ctrl+C
    while ($true) {
        Start-Sleep -Seconds 1
    }
}
finally {
    Write-Host ""
    Write-Banner "Shutting Down"
    Write-Color "  Stopping Backend..." Yellow
    Stop-Job -Name "LobsterQuant-Backend" -ErrorAction SilentlyContinue
    Remove-Job -Name "LobsterQuant-Backend" -ErrorAction SilentlyContinue
    Write-Color "  Stopping Frontend..." Yellow
    Stop-Job -Name "LobsterQuant-Frontend" -ErrorAction SilentlyContinue
    Remove-Job -Name "LobsterQuant-Frontend" -ErrorAction SilentlyContinue
    Write-Color "All services stopped." Green
    Write-Host ""
}