#!/usr/bin/env powershell
# ============================================================================
# Thakran OS — Kernel Build Orchestrator (Windows / PowerShell)
# ============================================================================
# This script orchestrates the Docker-based build environment to cross-compile
# the Thakran OS Linux kernel directly from Windows.
#
# Usage: .\build-kernel.ps1 [-Arch x86_64|arm64] [-Clean]
# ============================================================================

param (
    [ValidateSet("x86_64", "arm64")]
    [string]$Arch = "x86_64",
    [switch]$Clean
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path ".."
$BuildEnvDir = "$ProjectRoot\build-env"
$OutDir = "$ProjectRoot\out\$Arch"

Write-Host "=====================================================================" -ForegroundColor Magenta
Write-Host " 🌌 Thakran OS — Kernel Builder ($Arch)" -ForegroundColor Cyan
Write-Host "=====================================================================" -ForegroundColor Magenta

# ─── 1. Ensure Output Directories Exist ──────────────────────────────────
if (-not (Test-Path $OutDir)) {
    New-Item -ItemType Directory -Path $OutDir | Out-Null
}

if ($Clean) {
    Write-Host "🧹 Cleaning previous builds..." -ForegroundColor Yellow
    Remove-Item -Path "$OutDir\*" -Recurse -Force -ErrorAction SilentlyContinue
}

# ─── 2. Check Docker ─────────────────────────────────────────────────────
Write-Host "🐳 Checking Docker availability..."
try {
    docker --version | Out-Null
} catch {
    Write-Error "Docker is not installed or not running. Please install Docker Desktop for Windows."
    exit 1
}

# ─── 3. Build Docker Image ───────────────────────────────────────────────
Write-Host "📦 Preparing build container..."
docker build -t thakran-builder:latest $BuildEnvDir

# ─── 4. Execute Build Script Inside Container ────────────────────────────
Write-Host "🔨 Cross-compiling kernel inside container (this will take a while)..." -ForegroundColor Green

# Prepare path mapping (Convert Windows paths to Unix-style for Docker)
$VolSource = $ProjectRoot.ToString().Replace('\', '/')
if ($VolSource -match '^([A-Za-z]):(.*)$') {
    $DriveLetter = $Matches[1].ToLower()
    $RestOfPath = $Matches[2]
    $VolSource = "/$DriveLetter$RestOfPath"
}

# Kernel build configuration
$KernelVersion = "6.12"
$ConfigFile = "config/${Arch}.config"
$KernelUrl = "https://cdn.kernel.org/pub/linux/kernel/v6.x/linux-${KernelVersion}.tar.xz"
$Jobs = [System.Environment]::ProcessorCount

$DockerCmd = @(
    "docker", "run", "--rm",
    "-v", "${VolSource}:/workspace",
    "-e", "ARCH=$Arch",
    "-e", "KERNEL_VERSION=$KernelVersion",
    "-e", "CONFIG_FILE=$ConfigFile",
    "-e", "BUILD_DIR=/workspace/build/kernel",
    "-e", "OUTPUT_DIR=/workspace/out/$Arch",
    "-e", "KERNEL_URL=$KernelUrl",
    "-e", "JOBS=$Jobs",
    "thakran-builder:latest",
    "/bin/bash", "-c", "chmod +x /workspace/kernel/build.sh && /workspace/kernel/build.sh"
)

# Run the build
& docker $DockerCmd

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Kernel compilation completed successfully!" -ForegroundColor Green
    Write-Host "📁 Output saved to: $OutDir"
    
    # List generated files
    Get-ChildItem $OutDir | Format-Table Name, @{Name="Size(MB)";Expression={"{0:N2}" -f ($_.Length / 1MB)}}
} else {
    Write-Error "❌ Kernel compilation failed."
}
