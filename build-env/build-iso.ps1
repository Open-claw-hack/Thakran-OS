#!/usr/bin/env powershell
# ============================================================================
# Thakran OS - ISO Builder (Windows PowerShell)
# ============================================================================
# Runs the ISO generation inside the hermetic Docker environment.
# Uses Docker layer caching + named volumes to avoid re-downloading packages.
# ============================================================================

$ErrorActionPreference = "Stop"
$ProjectRoot = Resolve-Path ".."
$Arch = "amd64"

if ($args.Count -gt 0) {
    $Arch = $args[0]
}

Write-Host "=====================================================================" -ForegroundColor Magenta
Write-Host " Thakran OS - Building ISO ($Arch)" -ForegroundColor Cyan
Write-Host "=====================================================================" -ForegroundColor Magenta

# --- Check Docker ---
try {
    $null = docker info 2>&1
} catch {
    Write-Error "Docker is not running. Please start Docker Desktop."
    exit 1
}

# --- Build Docker Image (cached if unchanged) ---
Write-Host "Building Docker image (cached if unchanged)..." -ForegroundColor Yellow
docker build -t thakran-builder .
if ($LASTEXITCODE -ne 0) {
    Write-Error "Docker image build failed!"
    exit 1
}

# --- Prepare Volume Mount Path ---
$VolSource = $ProjectRoot.ToString().Replace('\', '/')
if ($VolSource -match '^([A-Za-z]):(.*)$') {
    $DriveLetter = $Matches[1].ToLower()
    $RestOfPath = $Matches[2]
    $VolSource = "/$DriveLetter$RestOfPath"
}

# --- Create persistent cache volume ---
Write-Host "Ensuring build cache volume exists..." -ForegroundColor Yellow
$null = docker volume create thakran-build-cache 2>&1

# --- Build the ISO ---
Write-Host "Generating Bootable ISO Image..." -ForegroundColor Cyan
Write-Host "   (This may take 15-30 minutes on first run, faster on subsequent runs)" -ForegroundColor DarkGray

$BuildCmd = "chmod +x ./build-iso.sh; ./build-iso.sh $Arch"

docker run --rm --privileged -u 0 `
    -v "${VolSource}:/workspace" `
    -v "thakran-build-cache:/tmp" `
    -w "/workspace/installer/iso-builder" `
    thakran-builder:latest `
    /bin/bash -c "$BuildCmd" | Out-Host

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "=====================================================================" -ForegroundColor Green
    Write-Host " ISO successfully generated!" -ForegroundColor Green
    Write-Host "=====================================================================" -ForegroundColor Green

    $IsoFiles = Get-ChildItem -Path "$ProjectRoot\installer\iso-builder\*.iso" -ErrorAction SilentlyContinue
    if ($IsoFiles) {
        foreach ($iso in $IsoFiles) {
            $sizeMB = [math]::Round($iso.Length / 1MB, 1)
            Write-Host " $($iso.Name)  ($sizeMB MB)" -ForegroundColor Yellow
        }
    }
    Write-Host ""
    Write-Host " Next: Boot this ISO in VirtualBox or burn to USB with Rufus!" -ForegroundColor Cyan
} else {
    Write-Host ""
    Write-Host "Build failed! Check the output above for errors." -ForegroundColor Red
    exit 1
}
