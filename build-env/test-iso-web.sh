#!/bin/bash
# ============================================================================
# Thakran OS — GitHub Codespace Web Tester
# ============================================================================
# Boots the compiled Thakran OS ISO directly inside the Codespace using QEMU
# and streams the display to your browser via noVNC (Web VNC).
#
# Usage:
#   chmod +x build-env/test-iso-web.sh
#   ./build-env/test-iso-web.sh
# ============================================================================

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ISO_PATH=$(ls "$PROJECT_ROOT/installer/iso-builder/"*.iso 2>/dev/null | head -n 1)

# Terminal colors
CYAN='\033[1;36m'
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
RED='\033[1;31m'
RESET='\033[0m'

echo -e "${CYAN}════════════════════════════════════════════════════════════════════${RESET}"
echo -e "${CYAN}  🖥️  Thakran OS — Web Simulator (Codespace)${RESET}"
echo -e "${CYAN}════════════════════════════════════════════════════════════════════${RESET}"

if [ -z "$ISO_PATH" ]; then
    echo -e "${RED}❌ No ISO found in installer/iso-builder/! Run build-iso-codespace.sh first.${RESET}"
    exit 1
fi

echo -e "${GREEN}✓ Found ISO: $(basename "$ISO_PATH")${RESET}"

# 1. Install QEMU and noVNC
echo -e "\n${YELLOW}Setting up QEMU and Web VNC server...${RESET}"
sudo apt-get update -qq
sudo apt-get install -y --no-install-recommends qemu-system-x86 qemu-utils novnc websockify net-tools 2>/dev/null

# 2. Kill existing sessions
sudo pkill -f qemu-system-x86_64 || true
sudo pkill -f websockify || true

# 3. Create a virtual hard drive for testing installations (optional but good)
TEST_HDD="/tmp/thakran-test.img"
if [ ! -f "$TEST_HDD" ]; then
    echo "Creating 20GB virtual hard drive for testing..."
    qemu-img create -f qcow2 "$TEST_HDD" 20G
fi

# 4. Start QEMU in background with VNC enabled
# In GitHub Codespaces, hardware acceleration (KVM) is blocked.
# We MUST use software virtualization (TCG).
echo -e "\n${YELLOW}Booting Thakran OS in 8-core / 16GB RAM Virtual Machine (Software Mode)...${RESET}"
qemu-system-x86_64 \
    -machine accel=tcg \
    -m 16G \
    -smp 8 \
    -vga virtio \
    -display vnc=127.0.0.1:0 \
    -cdrom "$ISO_PATH" \
    -drive file="$TEST_HDD",format=qcow2,if=virtio \
    -boot d \
    -usb \
    -device usb-tablet \
    -net nic -net user \
    -daemonize

# 5. Start noVNC bridge (This is the one we want Codespaces to forward)
echo -e "${YELLOW}Starting Web Server...${RESET}"
websockify --web=/usr/share/novnc/ 6080 127.0.0.1:5900 > /dev/null 2>&1 &

# 6. Instructions for Codespace
sleep 2
echo -e "\n${GREEN}════════════════════════════════════════════════════════════════════${RESET}"
echo -e "${GREEN}  ✅ Virtual Machine is Running!${RESET}"
echo -e "${GREEN}════════════════════════════════════════════════════════════════════${RESET}"
echo -e "\n${CYAN}To view Thakran OS:${RESET}"
echo -e "1. Look at the VS Code terminal's ${YELLOW}'PORTS'${RESET} tab."
echo -e "2. Find the port named ${YELLOW}6080${RESET} (Ignore port 5900 if it appears)."
echo -e "3. Click the globe/link icon 🌐 next to port 6080 to open it in your browser."
echo -e "4. In the browser, click ${YELLOW}'Connect'${RESET} (Password is empty)."
echo ""
echo -e "To stop the VM, run: ${RED}sudo pkill -f qemu${RESET}"
echo ""
