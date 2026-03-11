<![CDATA[<div align="center">

# 🌌 Thakran OS

### The World's Lightest AI-Native Operating System

**Built by AI. For Humans & AI Agents. Runs Everywhere.**

[![Version](https://img.shields.io/badge/version-0.1.0--alpha-blueviolet?style=for-the-badge)](VERSION)
[![License](https://img.shields.io/badge/license-Proprietary-red?style=for-the-badge)](LICENSE)
[![Kernel](https://img.shields.io/badge/kernel-Linux%206.x-yellow?style=for-the-badge)](kernel/)
[![AI](https://img.shields.io/badge/AI-Core%20Integrated-orange?style=for-the-badge)](ai/)
[![Arch](https://img.shields.io/badge/arch-x86__64%20%7C%20ARM64-green?style=for-the-badge)](kernel/config/)

---

*A featherweight, next-generation OS with AI at its core — runs on a Raspberry Pi, flies on a workstation. Supports Windows, Android, macOS, and iOS apps. One OS to rule them all.*

</div>

---

## 🚀 Vision

Thakran OS is the operating system the world has been waiting for. Ultra-lightweight yet insanely capable — it runs on a 10-year-old laptop with 512MB RAM just as beautifully as on a 128GB workstation.

- 🪶 **Featherweight Core** — 256MB RAM base footprint. Boots in under 5 seconds
- 🧠 **AI at the Core** — Local AI engine auto-scales from tiny (50MB) to ultra (34B) models based on your hardware
- 🌍 **Universal App Support** — Run Windows (.exe), Android (.apk), macOS (.app), and iOS (web) apps natively
- 🏗️ **Multi-Architecture** — x86_64 (Intel/AMD) + ARM64 (Raspberry Pi, Apple Silicon, Snapdragon)
- ⚡ **Auto-Optimizing** — AI continuously tunes performance for YOUR specific hardware
- 🔒 **Security-First** — AppArmor sandboxing, encrypted storage, AI-powered threat detection
- 🎨 **Stunning UI** — Glassmorphic design, smooth 60fps animations, adaptive themes
- 🤖 **Agent-Ready** — First-class support for AI agents to operate alongside human users
- 📦 **Install Anywhere** — ISO for fresh install, dual-boot, Raspberry Pi SD card image

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     User / AI Agent                          │
├──────────────────────────────────────────────────────────────┤
│              Thakran Desktop Shell (Wayland)                  │
│  ┌──────────┬──────────┬───────────┬─────────┬───────────┐  │
│  │  Panel   │ Launcher │ Assistant │  Apps   │ App Store │  │
│  └──────────┴──────────┴───────────┴─────────┴───────────┘  │
├──────────────────────────────────────────────────────────────┤
│              Universal App Compatibility Layer                │
│  ┌──────────┬──────────┬──────────┬──────────┬───────────┐  │
│  │ Wine     │ Waydroid │ Darling  │ Flatpak  │ AppImage  │  │
│  │ Windows  │ Android  │ macOS    │ Linux    │ Portable  │  │
│  └──────────┴──────────┴──────────┴──────────┴───────────┘  │
├──────────────────────────────────────────────────────────────┤
│              AI Core Engine (thakran-aid)                     │
│  ┌──────────┬───────────┬──────────────┬─────────────────┐  │
│  │ Local AI │ Model Mgr │ HW Optimizer │ Adaptive Scale  │  │
│  └──────────┴───────────┴──────────────┴─────────────────┘  │
├──────────────────────────────────────────────────────────────┤
│              System Services (Ultra-Light)                    │
│  ┌──────────┬──────────┬────────┬──────────┬────────────┐  │
│  │ Security │ Network  │ Power  │ Packages │ Containers │  │
│  └──────────┴──────────┴────────┴──────────┴────────────┘  │
├──────────────────────────────────────────────────────────────┤
│              Custom Linux Kernel (6.x, Multi-Arch)            │
│              x86_64 │ ARM64 (aarch64) │ RISC-V (future)      │
├──────────────────────────────────────────────────────────────┤
│              Hardware (Any: Raspberry Pi → Workstation)       │
└──────────────────────────────────────────────────────────────┘
               ☁️ Online AI Cloud (Optional Subscription)
```

---

## 🪶 Performance Tiers

Thakran OS **automatically adapts** to your hardware. No configuration needed.

| Tier | Hardware | RAM | AI Model | Desktop Mode |
|------|----------|-----|----------|-------------|
| 🌱 **Nano** | Raspberry Pi 3, old laptops | 512MB–1GB | Cloud-only or tiny (50MB) | Lite Shell |
| 🌿 **Lite** | Raspberry Pi 4/5, budget PCs | 2–4GB | thakran-tiny (0.7GB) | Standard Shell |
| 🌳 **Standard** | Modern laptops, desktops | 8–16GB | thakran-standard (4.5GB) | Full Shell + Effects |
| 🏔️ **Ultra** | Workstations, gaming PCs | 32GB+ | thakran-pro/ultra (8-20GB) | Full Shell + All Apps |

---

## 🌍 Universal App Support

Run apps from **any platform** — no compromises.

| Platform | Technology | Status | What It Runs |
|----------|-----------|--------|-------------|
| 🐧 **Linux** | Native | ✅ Full | .deb, .rpm, Flatpak, AppImage, Snap |
| 🪟 **Windows** | Wine/Proton | ✅ Full | .exe, .msi — Office, Photoshop, games |
| 🤖 **Android** | Waydroid | ✅ Full | .apk — Play Store apps in a container |
| 🍎 **macOS** | Darling | 🟡 Beta | .app — macOS command-line & some GUI apps |
| 📱 **iOS** | PWA Engine | 🟡 Beta | iOS web apps via Progressive Web App engine |
| 🎮 **Steam** | Proton/SteamOS | ✅ Full | Steam games library |

---

## 🧠 AI Features

### Local AI (Free, Adapts to Your Hardware)
- **Auto-Scales**: Picks the right model size for your device (50MB on Pi → 20GB on workstation)
- **Thakran AI Assistant** — Chat, voice commands, system automation
- **Smart File Search** — Find files by describing what you're looking for
- **AI Terminal** — Natural language to commands, error explanation
- **System Optimizer** — AI continuously tunes performance for your workload
- **Smart Notifications** — AI filters and prioritizes your notifications

### Cloud AI (Premium Subscription)
- **Advanced Models** — GPT-4, Claude, Gemini access (essential for low-end devices!)
- **Cloud Processing** — Offload heavy AI tasks when hardware is limited
- **AI App Store** — Download specialized AI models and agents
- **Cross-Device Sync** — Your AI learns across all your devices

---

## 📦 Installation

### Option 1: x86_64 (Intel/AMD) — PC/Laptop
```bash
# Download the ISO
wget https://thakranos.dev/download/thakran-os-0.1.0-x86_64.iso

# Create bootable USB
sudo dd if=thakran-os-0.1.0-x86_64.iso of=/dev/sdX bs=4M status=progress

# Boot from USB and follow the installer
```

### Option 2: ARM64 — Raspberry Pi
```bash
# Download the Pi image
wget https://thakranos.dev/download/thakran-os-0.1.0-arm64-rpi.img.xz

# Flash to SD card
xzcat thakran-os-0.1.0-arm64-rpi.img.xz | sudo dd of=/dev/sdX bs=4M status=progress

# Insert SD card and boot!
```

### Option 3: Dual Boot
The installer auto-detects existing OS (Windows, macOS, Linux) and configures dual-boot. Your existing OS stays untouched.

### System Requirements

| Tier | CPU | RAM | Storage | GPU |
|------|-----|-----|---------|-----|
| **Absolute Minimum** | 1 core, ARMv8/x86_64 | 512 MB | 4 GB | Any (framebuffer) |
| **Minimum (with AI)** | 2 cores | 2 GB | 8 GB | Any |
| **Recommended** | 4+ cores | 8 GB+ | 32 GB+ | Discrete GPU |
| **Power User** | 8+ cores | 32 GB+ | 100 GB+ | NVIDIA/AMD GPU |

**Supported devices**: Raspberry Pi 3/4/5, any x86_64 PC (2010+), ARM64 SBCs, laptops, desktops, workstations, servers.

---

## 🛠️ Building from Source (Windows/Linux/Mac)

We package a hermetic Docker build environment so you can cross-compile the Linux kernel directly from your current OS.

```powershell
# Clone the repository
git clone https://github.com/thakran-os/thakran-os.git
cd thakran-os

# 1. Build the Kernel (requires Docker Desktop)
cd build-env
.\build-kernel.ps1 -Arch x86_64
.\build-kernel.ps1 -Arch arm64

# 2. Test the Kernel in QEMU
.\test-kernel.ps1 -Arch x86_64

# 3. Build the Desktop Environment & Wayland Compositor
.\build-desktop.ps1

# 4. Build UI & AI Engine (Make)
cd ..
make ai-engine
make iso ARCH=x86_64
```

---

## 📁 Project Structure

```
Thakran OS/
├── kernel/          # Multi-arch kernel configs (x86_64, ARM64)
├── boot/            # Bootloader, splash screen, init system
├── system/          # Hardware detection, security, networking
├── ai/              # AI Core Engine (auto-scaling)
├── compat/          # Universal app compatibility layers
│   ├── wine/        # Windows app support
│   ├── waydroid/    # Android app support
│   ├── darling/     # macOS app support
│   └── pwa/         # iOS Progressive Web Apps
├── desktop/         # Wayland compositor, shell, theme
├── apps/            # Core applications
├── installer/       # ISO builder & graphical installer
├── cloud/           # Online AI & subscription services
├── branding/        # Logos, icons, fonts
├── docs/            # Documentation
└── scripts/         # Build & utility scripts
```

---

## 🤝 Contributing

Thakran OS is a massive undertaking. We welcome contributions in:
- 🐧 Kernel & driver support (x86_64, ARM64, RISC-V)
- 🧠 AI model optimization (especially for low-end hardware)
- 🎨 UI/UX design & frontend development
- 🪟 Wine/Waydroid/Darling compatibility improvements
- 🔒 Security auditing & hardening
- 📖 Documentation & tutorials

---

## 📄 License

Thakran OS is proprietary software. See [LICENSE](LICENSE) for details.

---

<div align="center">

**Thakran OS** — *Intelligence, Built In. Runs Everywhere.*

</div>
]]>
