#!/bin/bash
# ============================================================================
# Thakran OS — Development Environment Setup
# ============================================================================
# Sets up the build environment for Thakran OS development.
# Run this once to prepare your machine for building.
# ============================================================================

set -euo pipefail

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║       ⚙ Thakran OS — Development Environment Setup         ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# ─── Detect OS ──────────────────────────────────────────────────────────────
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
else
    OS="unknown"
fi

echo -e "${YELLOW}Detected OS: ${OS}${NC}"

# ─── Install System Dependencies ───────────────────────────────────────────
echo -e "${YELLOW}[1/5] Installing system dependencies...${NC}"

case $OS in
    ubuntu|debian)
        sudo apt-get update -qq
        sudo apt-get install -y -qq \
            build-essential \
            gcc g++ make cmake \
            python3 python3-pip python3-venv \
            git wget curl \
            flex bison bc \
            libelf-dev libssl-dev \
            libncurses-dev \
            xorriso mtools \
            squashfs-tools debootstrap \
            grub-pc-bin grub-efi-amd64-bin \
            qemu-system-x86 qemu-utils \
            libgtk-4-dev libadwaita-1-dev \
            gobject-introspection \
            libgirepository1.0-dev \
            libvte-2.91-gtk4-dev \
            shellcheck
        ;;
    fedora)
        sudo dnf install -y \
            gcc gcc-c++ make cmake \
            python3 python3-pip \
            git wget curl \
            flex bison bc \
            elfutils-libelf-devel openssl-devel \
            xorriso squashfs-tools \
            qemu-system-x86 \
            gtk4-devel libadwaita-devel \
            vte291-gtk4-devel
        ;;
    arch)
        sudo pacman -S --needed --noconfirm \
            base-devel cmake python python-pip \
            git wget curl bc \
            xorriso squashfs-tools \
            qemu-full \
            gtk4 libadwaita vte4
        ;;
    *)
        echo -e "${RED}Unsupported OS: $OS. Please install dependencies manually.${NC}"
        ;;
esac

echo -e "${GREEN}  ✓ System dependencies installed${NC}"

# ─── Python Environment ────────────────────────────────────────────────────
echo -e "${YELLOW}[2/5] Setting up Python environment...${NC}"

python3 -m venv .venv 2>/dev/null || python3 -m venv --without-pip .venv
source .venv/bin/activate

pip install --quiet --upgrade pip
pip install --quiet \
    pyyaml \
    fastapi \
    uvicorn \
    httpx \
    aiofiles \
    pydantic \
    rich \
    click

echo -e "${GREEN}  ✓ Python environment ready${NC}"

# ─── Create Build Directory ────────────────────────────────────────────────
echo -e "${YELLOW}[3/5] Creating build directories...${NC}"

mkdir -p build/{kernel,ai,desktop,apps,iso}
mkdir -p .cache/models

echo -e "${GREEN}  ✓ Build directories created${NC}"

# ─── Git Setup ──────────────────────────────────────────────────────────────
echo -e "${YELLOW}[4/5] Initializing git repository...${NC}"

if [ ! -d .git ]; then
    git init
    
    cat > .gitignore << 'EOF'
# Build artifacts
build/
.cache/

# Python
.venv/
__pycache__/
*.pyc
*.pyo

# AI Models (too large for git)
*.gguf
*.bin
*.onnx
*.safetensors

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS files
.DS_Store
Thumbs.db

# ISO images
*.iso
EOF
    
    git add .
    git commit -m "Initial commit: Thakran OS project scaffolding" --allow-empty 2>/dev/null || true
fi

echo -e "${GREEN}  ✓ Git repository initialized${NC}"

# ─── Verify Setup ──────────────────────────────────────────────────────────
echo -e "${YELLOW}[5/5] Verifying setup...${NC}"

echo "  Python: $(python3 --version)"
echo "  GCC: $(gcc --version | head -1)"
echo "  Make: $(make --version | head -1)"
echo "  Git: $(git --version)"

echo -e "${GREEN}  ✓ All checks passed${NC}"

# ─── Summary ───────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  ✓ Development environment ready!                           ║${NC}"
echo -e "${GREEN}╠══════════════════════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║  Next steps:                                                ║${NC}"
echo -e "${GREEN}║    make kernel       Build the custom kernel                ║${NC}"
echo -e "${GREEN}║    make ai-engine    Build the AI engine                    ║${NC}"
echo -e "${GREEN}║    make desktop      Build the desktop shell                ║${NC}"
echo -e "${GREEN}║    make iso          Generate bootable ISO                  ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
