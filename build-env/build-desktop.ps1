#!/usr/bin/env powershell
# ============================================================================
# Thakran OS — Desktop Environment Builder
# ============================================================================
# Compiles the C wlroots compositor inside the Docker environment.
# ============================================================================

$ErrorActionPreference = "Stop"
$ProjectRoot = Resolve-Path ".."

Write-Host "=====================================================================" -ForegroundColor Magenta
Write-Host " 🖥️ Thakran OS — Building Desktop Environment" -ForegroundColor Cyan
Write-Host "=====================================================================" -ForegroundColor Magenta

# Check if Docker is running
try {
    docker info | Out-Null
} catch {
    Write-Error "❌ Docker is not running. Please start Docker Desktop."
    exit 1
}

Write-Host "⚙️ Ensuring builder image is up-to-date..."
docker build -t thakran-builder . | Out-Null

$VolSource = $ProjectRoot.replace('\', '/').replace('C:', '/c')

# Build the desktop
$DockerCmd = @(
    "docker", "run", "--rm",
    "-v", "$VolSource`:/workspace",
    "thakran-builder:latest",
    "/bin/bash", "-c", "cd /workspace && make desktop"
)

Write-Host "🔨 Compiling Wayland Compositor..."
& $DockerCmd

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Desktop Environment successfully compiled!" -ForegroundColor Green
    Write-Host "Target output: $($ProjectRoot)\build\desktop" -ForegroundColor Yellow
} else {
    Write-Host "❌ Build failed!" -ForegroundColor Red
}
