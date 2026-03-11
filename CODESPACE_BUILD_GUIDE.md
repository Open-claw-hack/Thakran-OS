# 🚀 Thakran OS — GitHub Codespace Build Guide

Build the full Thakran OS bootable ISO inside a **GitHub Codespace** (16 cores, 64 GB RAM).

> [!TIP]
> No Docker needed! The Codespace IS a Linux machine — we build natively.

---

## Compression: `zstd` vs `gzip` (Why This Is Better)

| Feature | Old (`gzip`) | New (`zstd` level 19) |
|---|---|---|
| Compression Speed | Single-threaded | **16 threads** |
| ISO Size (estimated) | ~7.8 GB | **~2-3 GB** |
| Decompression Speed | Moderate | **3x faster** |
| Build Time | ~30-60 min | **~8-15 min** |
| Block Size | 256 KB | **1 MB** (better ratio) |

---

## Step-by-Step Instructions

### Step 1: Push Thakran OS to GitHub

If your repo isn't already on GitHub:

```powershell
# On your Windows PC, in the Thakran OS folder:
cd "C:\Users\mrkar\Desktop\Thakran OS"
git init
git add -A
git commit -m "Thakran OS full source"
git remote add origin https://github.com/YOUR_USERNAME/thakran-os.git
git push -u origin main
```

> [!IMPORTANT]
> Make sure the repo is uploaded BEFORE creating the Codespace.

---

### Step 2: Create a GitHub Codespace

1. Go to your repo on GitHub: `https://github.com/YOUR_USERNAME/thakran-os`
2. Click the green **`<> Code`** button
3. Click the **`Codespaces`** tab
4. Click **`...`** → **`New with options`**
5. Select:
   - **Machine type:** `16-core (64 GB RAM, 128 GB storage)` ⭐
   - **Region:** Closest to you
6. Click **`Create codespace`**

> [!NOTE]
> GitHub Classroom codespace: If you're using GitHub Classroom, the codespace is created from the assignment repo. Follow the same steps — click **Code → Codespaces → Create**.

---

### Step 3: Build the ISO (One Command!)

Once the Codespace terminal opens, run:

```bash
# Make the script executable and run it
chmod +x build-env/build-iso-codespace.sh
sudo bash build-env/build-iso-codespace.sh
```

That's it! The script will:
1. ✅ Install all Linux build dependencies
2. ✅ Create a Debian Bookworm rootfs via `debootstrap`
3. ✅ Install kernel, Wayland, desktop packages
4. ✅ Inject all Thakran OS components (AI, Desktop, Apps)
5. ✅ Compress with **zstd** using all 16 cores
6. ✅ Generate UEFI + BIOS dual-boot ISO

**Expected time: ~8-15 minutes** ⚡

---

### Step 4: Download the ISO

The ISO will be at: `installer/iso-builder/thakran-os-0.1.0-alpha-amd64.iso`

#### Option A: VS Code File Explorer (Easiest)
1. In the Codespace left sidebar, open the **Explorer** panel
2. Navigate to `installer/iso-builder/`
3. Right-click on `thakran-os-0.1.0-alpha-amd64.iso`
4. Click **`Download`**

#### Option B: GitHub CLI (From Your Local Machine)
```bash
# On your local machine (not the Codespace):
gh codespace cp remote:/workspaces/thakran-os/installer/iso-builder/thakran-os-0.1.0-alpha-amd64.iso .
```

#### Option C: Zip + Download (If file is too large for direct download)
```bash
# Inside the Codespace terminal:
cd installer/iso-builder

# Create a zip (no extra compression since ISO is already compressed)
zip -0 thakran-os.zip thakran-os-0.1.0-alpha-amd64.iso

# Then download the .zip file via the Explorer panel
```

#### Option D: Upload to Google Drive / OneDrive
```bash
# Install rclone in the Codespace
curl https://rclone.org/install.sh | sudo bash

# Configure (interactive — follow prompts for your cloud provider)
rclone config

# Upload
rclone copy installer/iso-builder/thakran-os-0.1.0-alpha-amd64.iso myremote:ThakranOS/
```

---

## GitHub Classroom Specific Instructions

If you're using **GitHub Classroom**:

1. **Accept the assignment** — this creates a repo for you
2. **Clone locally**, copy your Thakran OS files into it, and push:
   ```bash
   git clone https://github.com/YOUR_ORG/your-assignment-repo.git
   cp -r "C:\Users\mrkar\Desktop\Thakran OS\*" your-assignment-repo/
   cd your-assignment-repo
   git add -A && git commit -m "Add Thakran OS source" && git push
   ```
3. **Open Codespace** from the assignment repo (Code → Codespaces → New)
4. **Run the build** (same as Step 3 above):
   ```bash
   chmod +x build-env/build-iso-codespace.sh
   sudo bash build-env/build-iso-codespace.sh
   ```
5. **Download the ISO** (same as Step 4 above)

> [!WARNING]
> GitHub Classroom codespaces may have usage limits set by your instructor. The 16-core machine costs credit faster — build efficiently!

---

## Troubleshooting

| Issue | Solution |
|---|---|
| `debootstrap` fails | Run `sudo apt-get update` first, check internet connectivity |
| Out of disk space | Delete `installer/iso-builder/image/` and retry |
| Permission denied | Always use `sudo bash` to run the script |
| Download too slow | Use Option C (zip) or Option D (cloud upload) |
| Codespace times out | Rebuild — the debootstrap cache is persistent in `/tmp` |

---

## Quick Reference

```bash
# Full build (one command):
sudo bash build-env/build-iso-codespace.sh

# Clean and rebuild:
sudo rm -rf /tmp/thakran-iso-root installer/iso-builder/image
sudo bash build-env/build-iso-codespace.sh

# Check ISO size:
ls -lh installer/iso-builder/*.iso
```
