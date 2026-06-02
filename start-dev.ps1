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

# Check for port conflicts (critical - prevents wrong backend being used)
Write-Color "  Checking ports 3000 and 8001..." Cyan
$port8001 = netstat -ano 2>$null | Select-String ":8001\s.*LISTENING"
$port3000 = netstat -ano 2>$null | Select-String ":3000\s.*LISTENING"

if ($port8001) {
    $pid8001 = ($port8001 -split '\s+')[-1]
    $proc8001 = Get-Process -Id $pid8001 -ErrorAction SilentlyContinue
    Write-Color "  [WARN] Port 8001 is already in use by PID $pid8001 ($($proc8001.ProcessName))" Yellow
    Write-Color "         Killing process to free port..." Yellow
    Stop-Process -Id $pid8001 -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 1
    Write-Color "  [OK] Port 8001 freed" Green
}

if ($port3000) {
    $pid3000 = ($port3000 -split '\s+')[-1]
    $proc3000 = Get-Process -Id $pid3000 -ErrorAction SilentlyContinue
    Write-Color "  [WARN] Port 3000 is already in use by PID $pid3000 ($($proc3000.ProcessName))" Yellow
    Write-Color "         Killing process to free port..." Yellow
    Stop-Process -Id $pid3000 -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 1
    Write-Color "  [OK] Port 3000 freed" Green
}

if ($port3000) {
    $pid3000 = ($port3000 -split '\s+')[-1]
    $proc3000 = Get-Process -Id $pid3000 -ErrorAction SilentlyContinue
    Write-Color "  [WARN] Port 3000 is already in use by PID $pid3000 ($($proc3000.ProcessName))" Yellow
    Write-Color "         Killing process to free port..." Yellow
    Stop-Process -Id $pid3000 -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 1
    Write-Color "  [OK] Port 3000 freed" Green
}

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

# ─── Launch Backend ────────────────────────────────────────────────
Write-Color "  Launching Backend  → http://localhost:8001 (FastAPI)" Yellow

$backendScript = @"
Set-Location '$rootDir\backend'
`$env:PYTHONPATH = '$rootDir;$rootDir\lobster_quant'
python -m uvicorn main:app --host 127.0.0.1 --port 8001 --reload
"@

$backendProcess = Start-Process -FilePath "powershell" -ArgumentList "-NoExit", "-Command", $backendScript -WindowStyle Minimized -PassThru

# ─── Launch Frontend ───────────────────────────────────────────────
Write-Color "  Launching Frontend → http://localhost:3000 (Next.js)" Yellow

$frontendScript = @"
Set-Location '$rootDir\lobster-quant-web'
npm run dev
"@

$frontendProcess = Start-Process -FilePath "powershell" -ArgumentList "-NoExit", "-Command", $frontendScript -WindowStyle Minimized -PassThru

# Give services a moment to start
Start-Sleep -Seconds 5

# ─── Verify Services ──────────────────────────────────────────────
Write-Host ""
Write-Color "  Verifying services..." Cyan

$backendReady = $false
$frontendReady = $false

for ($i = 1; $i -le 10; $i++) {
    $port8001 = netstat -ano 2>$null | Select-String ":8001\s.*LISTENING"
    $port3000 = netstat -ano 2>$null | Select-String ":3000\s.*LISTENING"
    
    if ($port8001 -and -not $backendReady) {
        Write-Color "  [OK] Backend is listening on port 8001" Green
        $backendReady = $true
    }
    if ($port3000 -and -not $frontendReady) {
        Write-Color "  [OK] Frontend is listening on port 3000" Green
        $frontendReady = $true
    }
    if ($backendReady -and $frontendReady) { break }
    
    Start-Sleep -Seconds 1
}

if (-not $backendReady) {
    Write-Color "  [WARN] Backend may still be starting..." Yellow
}
if (-not $frontendReady) {
    Write-Color "  [WARN] Frontend may still be starting..." Yellow
}

Write-Host ""

# ─── Status Summary ────────────────────────────────────────────────
Write-Banner "Development Environment Ready"
Write-Color "  Frontend : http://localhost:3000" Green
Write-Color "  Backend  : http://localhost:8001" Green
Write-Color "  API Docs : http://localhost:8001/docs" Green
Write-Host ""
Write-Color "  Backend PID  : $($backendProcess.Id)" Gray
Write-Color "  Frontend PID : $($frontendProcess.Id)" Gray
Write-Host ""
Write-Color "Close the minimized PowerShell windows to stop services." Magenta
Write-Color "Or run: Stop-Process -Id $($backendProcess.Id),$($frontendProcess.Id) -Force" Magenta
Write-Host ""