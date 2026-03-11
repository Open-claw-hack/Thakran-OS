# 💿 Thakran OS — Official Windows Build Guide

Since Thakran OS is a custom Linux-based operating system, compiling the source code into a bootable `.iso` file requires Linux filesystems and tools (`debootstrap`, `squashfs-tools`, etc.). 

Because you are building this on Windows, you must use **Docker Desktop** to create a hermetic Linux build environment. 

Here is exactly how to do it start-to-finish:

---

## Step 1: Install Windows Subsystem for Linux (WSL)
Docker Desktop on Windows relies on the WSL2 engine for maximum performance.
1. Open **PowerShell as Administrator** (Right-click Start menu -> Terminal (Admin)).
2. Run the following command:
   ```powershell
   wsl --install
   ```
3. **Restart your computer** when it finishes. 
   *(After restart, a terminal will pop up asking you to create a UNIX username and password. You can make it anything you want).*

## Step 2: Install Docker Desktop
1. Go to [https://docs.docker.com/desktop/install/windows/](https://docs.docker.com/desktop/install/windows/)
2. Download and install **Docker Desktop for Windows**.
3. During installation, make sure the box **"Use WSL 2 instead of Hyper-V"** is checked!
4. Open the Docker Desktop application and leave it running in the background.

## Step 3: Build the Thakran OS `.iso`
Now that your Windows PC has Linux superpowers via Docker, you can execute the build script we wrote!

1. Open PowerShell and navigate to our directory:
   ```powershell
   cd "C:\Users\mrkar\Desktop\Thakran OS\build-env"
   ```
2. Run the automated ISO generator script:
   ```powershell
   .\build-iso.ps1
   ```
   *This script spins up our secure Ubuntu Docker container, installs the cross-compilers, compiles your custom C/Python code into the Linux filesystem, and compresses it into an ISO image.*

## Step 4: Boot Your New OS!
When the script finishes, you will find `thakran-os-0.1.0-alpha-amd64.iso` in the `installer/iso-builder/` folder.

You have two choices to run it:
1. **Virtual Machine (Recommended for testing):** Download [VirtualBox for Windows](https://www.virtualbox.org/wiki/Downloads), create a new "Linux" VM, and attach the ISO file to the storage/CD drive.
2. **Real Hardware:** Download [Rufus](https://rufus.ie/en/), burn the ISO file to an empty USB Pendrive, restart your laptop, and press F12 (or Del/F2) to boot from the USB drive!
