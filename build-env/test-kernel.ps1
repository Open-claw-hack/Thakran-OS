#!/usr/bin/env powershell
# ============================================================================
# Thakran OS — Kernel Test Harness (QEMU on Windows)
# ============================================================================
# Boots the compiled Linux kernel directly in QEMU to verify it works
# without needing to build a full ISO.
#
# Usage: .\test-kernel.ps1 [-Arch x86_64|arm64]
# ============================================================================

param (
    [ValidateSet("x86_64", "arm64")]
    [string]$Arch = "x86_64"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Resolve-Path ".."
$OutDir = "$ProjectRoot\out\$Arch"

Write-Host "=====================================================================" -ForegroundColor Magenta
Write-Host " 💻 Thakran OS — Kernel Test Harness ($Arch)" -ForegroundColor Cyan
Write-Host "=====================================================================" -ForegroundColor Magenta

# ─── 1. Locate Kernel Image ──────────────────────────────────────────────
$KernelFiles = Get-ChildItem "$OutDir\vmlinuz*" -ErrorAction SilentlyContinue
if ($KernelFiles.Count -eq 0) {
    Write-Error "❌ Kernel image not found in $OutDir. Please run build-kernel.ps1 first."
    exit 1
}

$KernelImage = $KernelFiles[0].FullName
Write-Host "🔍 Found Kernel: $(Split-Path $KernelImage -Leaf)"

# ─── 2. Create Minimal Initramfs (BusyBox) ───────────────────────────────
Write-Host "📦 Generating minimal initramfs for testing..."
$InitramfsDir = "$OutDir\initramfs_staging"
$InitramfsFile = "$OutDir\initramfs.cpio.gz"

if (Test-Path $InitramfsDir) { Remove-Item -Path $InitramfsDir -Recurse -Force }
New-Item -ItemType Directory -Path "$InitramfsDir\bin" | Out-Null
New-Item -ItemType Directory -Path "$InitramfsDir\sbin" | Out-Null
New-Item -ItemType Directory -Path "$InitramfsDir\etc" | Out-Null
New-Item -ItemType Directory -Path "$InitramfsDir\proc" | Out-Null
New-Item -ItemType Directory -Path "$InitramfsDir\sys" | Out-Null
New-Item -ItemType Directory -Path "$InitramfsDir\dev" | Out-Null

# Create a simple init script
$InitScript = @"
#!/bin/busybox sh
/bin/busybox mount -t proc proc /proc
/bin/busybox mount -t sysfs sysfs /sys
/bin/busybox mount -t devtmpfs devtmpfs /dev

echo ""
echo "================================================================="
echo " 🌌 Welcome to Thakran OS Minimal Test Environment"
echo "================================================================="
echo "✅ Kernel successfully booted!"
echo "✅ Architecture: $Arch"
echo ""
echo "Type 'poweroff' to exit."
echo ""

exec /bin/busybox sh
"@

Set-Content -Path "$InitramfsDir\init" -Value $InitScript
# In a real environment we'd chmod +x, but Windows doesn't support ELF execution flags here directly.
# We will use Docker to build the initramfs properly.

$VolSource = $ProjectRoot.replace('\', '/').replace('C:', '/c')
$DockerCmd = @(
    "docker", "run", "--rm",
    "-v", "$VolSource`:/workspace",
    "thakran-builder:latest",
    "/bin/bash", "-c",
    "cd /workspace/out/$Arch/initramfs_staging && wget -q https://busybox.net/downloads/binaries/1.35.0-x86_64-linux-musl/busybox -O bin/busybox && chmod +x bin/busybox init && find . | cpio -H newc -o | gzip > ../initramfs.cpio.gz"
)

# For ARM64 we need the ARM busybox
if ($Arch -eq "arm64") {
    $DockerCmd[-1] = "cd /workspace/out/$Arch/initramfs_staging && wget -q https://busybox.net/downloads/binaries/1.35.0-aarch64-linux-musl/busybox -O bin/busybox && chmod +x bin/busybox init && find . | cpio -H newc -o | gzip > ../initramfs.cpio.gz"
}

Write-Host "⚙️ Building initramfs via Docker..."
& $DockerCmd

# ─── 3. Launch QEMU ──────────────────────────────────────────────────────
Write-Host "🚀 Launching QEMU..." -ForegroundColor Green

if ($Arch -eq "x86_64") {
    $QemuCmd = @(
        "qemu-system-x86_64",
        "-kernel", $KernelImage,
        "-initrd", $InitramfsFile,
        "-m", "2G",
        "-append", "console=ttyS0 quiet loglevel=3 thakran.tier=auto",
        "-nographic",
        "-cpu", "host",
        "-accel", "whpx" # Windows Hypervisor Platform
    )
} else {
    $QemuCmd = @(
        "qemu-system-aarch64",
        "-M", "virt",
        "-cpu", "cortex-a57",
        "-m", "2G",
        "-kernel", $KernelImage,
        "-initrd", $InitramfsFile,
        "-append", "console=ttyAMA0 quiet loglevel=3 thakran.tier=auto",
        "-nographic"
    )
}

try {
    Write-Host "Press Ctrl+A, then X to exit QEMU if it hangs." -ForegroundColor Yellow
    & $QemuCmd
} catch {
    Write-Host "If QEMU failed, ensure QEMU is installed and added to your Windows PATH: https://qemu.weilnetz.de/w64/" -ForegroundColor Yellow
    Write-Host "Run this command manually: $($QemuCmd -join ' ')"
}
