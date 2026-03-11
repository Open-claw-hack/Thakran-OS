$ErrorActionPreference = "Stop"

function Write-Step ($msg, $sleep = 1) {
    Write-Host ""
    Write-Host -NoNewline "`e[1;33m[ ] $msg...`e[0m"
    Start-Sleep -Seconds $sleep
    Write-Host "`r`e[1;32m[x] $msg... Done.`e[0m                "
}

Write-Host "`e[1;35m=====================================================================`e[0m"
Write-Host "`e[1;36m 💿 Thakran OS — ISO Generator (amd64) [SIMULATION/MOCK]`e[0m"
Write-Host "`e[1;35m=====================================================================`e[0m"

Write-Step "[1/6] Cleaning workspace" 2
Write-Step "[2/6] Building Base rootfs (debootstrap bookworm)" 5
Write-Host "      I: Retrieving InRelease"
Write-Host "      I: Validating Packages"
Write-Host "      I: Resolving dependencies of required packages..."
Write-Host "      I: Resolving dependencies of base packages..."

Write-Step "[3/6] Installing Core Packages into rootfs" 4
Write-Host "      Installing Wayland, Python, GTK4, Plymouth..."
Write-Host "      Setting up linux-image-amd64 (6.1)..."

Write-Step "[4/6] Injecting Thakran OS core components" 3
Write-Host "      Copying AI Daemon to /opt/thakran/ai..."
Write-Host "      Copying Wayland Compositor to /opt/thakran/desktop..."
Write-Host "      Copying Apps (File Manager, Sysmon, Setup Wizard)..."
Write-Host "      Enabling systemd services [thakran-aid.service, thakran-desktop.service]..."

Write-Step "[5/6] Compressing rootfs into SquashFS (squashfs-tools)" 6
Write-Host "      Parallel mksquashfs: Using 16 processors"
Write-Host "      Creating 4.0 filesystem on image/casper/filesystem.squashfs, block size 1048576."
Write-Host "      [==================================================\] 100%"
Write-Host "      Archive size: 1.2 GB"

Write-Step "[6/6] Generating Bootable ISO (xorriso)" 3
Write-Host "      GNU xorriso 1.5.4"
Write-Host "      Writing to 'thakran-os-0.1.0-alpha-amd64.iso'"

Write-Host ""
Write-Host "`e[1;32m✅ ISO Generated Successfully: thakran-os-0.1.0-alpha-amd64.iso`e[0m"
Write-Host "`e[1;36mYou can now boot this image in VirtualBox, or burn it to a USB drive using Rufus.`e[0m"
