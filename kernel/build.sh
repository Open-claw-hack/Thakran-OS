#!/bin/bash
# ============================================================================
# Thakran OS — Kernel Build Script (Internal to Docker)
# ============================================================================
# Downloads, patches, configures, and compiles the Linux kernel.
# Triggered by build-env/build-kernel.ps1.
# ============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info()  { echo -e "${BLUE}[INFO]${NC} $1"; }
log_ok()    { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step()  { echo -e "${CYAN}[STEP]${NC} $1"; }

# ─── Banner ─────────────────────────────────────────────────────────────────
echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║           🌌 Thakran OS — Kernel Builder                    ║"
echo "║           Building Linux ${KERNEL_VERSION} (Optimized)             ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# ─── Dependency Check ───────────────────────────────────────────────────────
log_step "Checking build dependencies..."

DEPS=(gcc make flex bison libelf-dev libssl-dev bc wget xz-utils)
MISSING=()

for dep in "${DEPS[@]}"; do
    if ! dpkg -s "$dep" &>/dev/null; then
        MISSING+=("$dep")
    fi
done

if [ ${#MISSING[@]} -gt 0 ]; then
    log_warn "Missing dependencies: ${MISSING[*]}"
    log_info "Installing missing dependencies..."
    sudo apt-get update -qq
    sudo apt-get install -y -qq "${MISSING[@]}"
fi

log_ok "All dependencies satisfied"

# ─── Download Kernel ────────────────────────────────────────────────────────
log_step "Preparing kernel source..."

mkdir -p "$BUILD_DIR" "$OUTPUT_DIR"

if [ ! -f "$BUILD_DIR/linux-${KERNEL_VERSION}.tar.xz" ]; then
    log_info "Downloading Linux kernel ${KERNEL_VERSION}..."
    wget -q --show-progress -O "$BUILD_DIR/linux-${KERNEL_VERSION}.tar.xz" "$KERNEL_URL"
else
    log_info "Using cached kernel source"
fi

if [ ! -d "$BUILD_DIR/linux-${KERNEL_VERSION}" ]; then
    log_info "Extracting kernel source..."
    tar -xf "$BUILD_DIR/linux-${KERNEL_VERSION}.tar.xz" -C "$BUILD_DIR"
fi

KERNEL_SRC="$BUILD_DIR/linux-${KERNEL_VERSION}"
log_ok "Kernel source ready at $KERNEL_SRC"

# ─── Apply Patches ─────────────────────────────────────────────────────────
PATCH_DIR="$(dirname "$0")/patches"
if [ -d "$PATCH_DIR" ] && [ "$(ls -A "$PATCH_DIR" 2>/dev/null)" ]; then
    log_step "Applying Thakran OS kernel patches..."
    for patch in "$PATCH_DIR"/*.patch; do
        log_info "Applying $(basename "$patch")..."
        cd "$KERNEL_SRC"
        patch -p1 < "$patch" || log_warn "Patch may have already been applied: $(basename "$patch")"
    done
    log_ok "All patches applied"
else
    log_info "No patches to apply"
fi

# ─── Configure Kernel ──────────────────────────────────────────────────────
log_step "Configuring kernel with Thakran OS optimizations..."

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cp "$SCRIPT_DIR/$CONFIG_FILE" "$KERNEL_SRC/.config"

cd "$KERNEL_SRC"
make olddefconfig

log_ok "Kernel configured"

# ─── Build Kernel ───────────────────────────────────────────────────────────
log_step "Building kernel with $JOBS parallel jobs..."
log_info "This may take 15-60 minutes depending on your hardware..."

make -j"$JOBS" bzImage
make -j"$JOBS" modules

log_ok "Kernel build complete"

# ─── Install to Output ─────────────────────────────────────────────────────
log_step "Installing kernel to output directory..."

OUTPUT_ABS="$(cd "$SCRIPT_DIR" && cd "$(dirname "$OUTPUT_DIR")" && pwd)/$(basename "$OUTPUT_DIR")"
mkdir -p "$OUTPUT_ABS"/{boot,lib/modules}

# Copy kernel image
cp arch/x86/boot/bzImage "$OUTPUT_ABS/boot/vmlinuz-thakran"

# Install modules
make INSTALL_MOD_PATH="$OUTPUT_ABS" modules_install

# Copy System.map and config
cp System.map "$OUTPUT_ABS/boot/System.map-thakran"
cp .config "$OUTPUT_ABS/boot/config-thakran"

log_ok "Kernel installed to $OUTPUT_ABS"

# ─── Summary ───────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  ✓ Thakran OS Kernel Build Complete                         ║${NC}"
echo -e "${GREEN}╠══════════════════════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║  Kernel:  vmlinuz-thakran                                   ║${NC}"
echo -e "${GREEN}║  Version: Linux ${KERNEL_VERSION}                                  ║${NC}"
echo -e "${GREEN}║  Config:  ${CONFIG_FILE}                              ║${NC}"
echo -e "${GREEN}║  Output:  ${OUTPUT_ABS}/boot/                       ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
