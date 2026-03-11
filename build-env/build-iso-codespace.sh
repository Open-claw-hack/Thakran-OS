#!/bin/bash
# ============================================================================
# Thakran OS — GitHub Codespace ISO Builder (Optimized for 16-core / 64GB RAM)
# ============================================================================
# This script runs the ENTIRE build process natively inside a GitHub Codespace.
# No Docker required — Codespace IS the Linux environment.
#
# Compression: zstd (multi-threaded, ~16 cores) for maximum speed
# Expected ISO size: ~2-3 GB (down from ~7.8 GB with gzip)
# Expected build time: ~8-15 minutes on 16-core Codespace
#
# Usage:
#   chmod +x build-env/build-iso-codespace.sh
#   sudo bash build-env/build-iso-codespace.sh
# ============================================================================

set -e

# ─── Configuration ──────────────────────────────────────────────────────────
OS_NAME="thakran-os"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VERSION=$(cat "$PROJECT_ROOT/VERSION" 2>/dev/null || echo "0.1.0-alpha")
ARCH="amd64"
ROOT_DIR="/tmp/thakran-iso-root"
ISO_DIR="$PROJECT_ROOT/installer/iso-builder/image"
ISO_OUTPUT="$PROJECT_ROOT/installer/iso-builder/${OS_NAME}-${VERSION}-${ARCH}.iso"

# Compression settings (optimized for 16-core Codespace)
# zstd: best speed-to-ratio on multi-core machines
# -Xcompression-level 19: near-maximum compression (22 is max but diminishing returns)
# -processors 0: auto-detect all available cores (will use all 16)
# -b 1048576: 1MB block size for better compression with more RAM available
COMP_ALGO="zstd"
COMP_OPTS="-Xcompression-level 19"
BLOCK_SIZE="1048576"
PROCESSORS=$(nproc)

# Terminal colors
RED='\033[1;31m'
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
BLUE='\033[1;34m'
MAGENTA='\033[1;35m'
CYAN='\033[1;36m'
RESET='\033[0m'

TOTAL_STEPS=7
TIMER_START=$(date +%s)

step_header() {
    echo -e "\n${YELLOW}[$1/${TOTAL_STEPS}] $2${RESET}"
}

time_elapsed() {
    local now=$(date +%s)
    local diff=$((now - TIMER_START))
    printf "%dm %ds" $((diff / 60)) $((diff % 60))
}

echo -e "${MAGENTA}════════════════════════════════════════════════════════════════════${RESET}"
echo -e "${CYAN}  💿 Thakran OS — Codespace ISO Builder v${VERSION}${RESET}"
echo -e "${CYAN}     Arch: ${ARCH}  |  Compression: ${COMP_ALGO}  |  Cores: $(nproc)${RESET}"
echo -e "${CYAN}     RAM: $(free -h | awk '/Mem:/ {print $2}')  |  Disk: $(df -h / | awk 'NR==2 {print $4}') free${RESET}"
echo -e "${MAGENTA}════════════════════════════════════════════════════════════════════${RESET}"

# ─── Pre-flight checks ─────────────────────────────────────────────────────
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}❌ This script requires root. Run with: sudo bash $0${RESET}"
    exit 1
fi

# ─── 1. Install Host Build Dependencies ────────────────────────────────────
step_header 1 "Installing build dependencies..."

# Remove broken third-party repos that come pre-installed in Codespaces
# (yarn, docker, etc. often have expired/missing GPG keys)
echo -e "${CYAN}  Cleaning up broken Codespace repos...${RESET}"
rm -f /etc/apt/sources.list.d/yarn.list 2>/dev/null || true
rm -f /etc/apt/sources.list.d/docker.list 2>/dev/null || true
rm -f /etc/apt/sources.list.d/github-cli.list 2>/dev/null || true
# Disable any other problematic third-party sources
for f in /etc/apt/sources.list.d/*.list; do
    if [ -f "$f" ] && grep -qiE "yarnpkg|docker\.com|packages\.microsoft" "$f" 2>/dev/null; then
        mv "$f" "${f}.disabled" 2>/dev/null || true
    fi
done

apt-get update -qq 2>/dev/null || apt-get update -qq --allow-releaseinfo-change 2>/dev/null || true
apt-get install -y --no-install-recommends \
    debootstrap \
    squashfs-tools \
    xorriso \
    grub-pc-bin \
    grub-efi-amd64-bin \
    grub-common \
    grub2-common \
    isolinux \
    syslinux-common \
    dosfstools \
    mtools \
    rsync \
    zstd \
    xz-utils \
    wget \
    curl \
    ca-certificates \
    gnupg \
    fakeroot \
    2>/dev/null

echo -e "${GREEN}  ✓ Dependencies installed ($(time_elapsed))${RESET}"

# ─── 2. Build Base Filesystem (debootstrap) ────────────────────────────────
step_header 2 "Building base rootfs (debootstrap bookworm)..."

DEBOOTSTRAP_CACHE="/tmp/thakran-debootstrap-cache"

if [ -d "$ROOT_DIR/bin" ] && [ -d "$ROOT_DIR/usr" ] && [ -f "$ROOT_DIR/etc/os-release" ]; then
    echo -e "${GREEN}  ✓ Reusing cached rootfs from previous build${RESET}"
    echo "    (Delete $ROOT_DIR to force fresh debootstrap)"
else
    rm -rf "$ROOT_DIR"
    mkdir -p "$ROOT_DIR" "$DEBOOTSTRAP_CACHE"
    debootstrap --arch=$ARCH --cache-dir="$DEBOOTSTRAP_CACHE" bookworm "$ROOT_DIR" http://deb.debian.org/debian/
fi

echo -e "${GREEN}  ✓ Base rootfs ready ($(time_elapsed))${RESET}"

# ─── 3. Chroot Package Installation ───────────────────────────────────────
step_header 3 "Installing packages inside rootfs (chroot)..."

# Clean old mounts
for mnt in sys proc run dev/pts dev; do
    umount "$ROOT_DIR/$mnt" 2>/dev/null || true
done

mount --bind /dev "$ROOT_DIR/dev"
mount --bind /run "$ROOT_DIR/run"
mount -t proc none "$ROOT_DIR/proc"
mount -t sysfs none "$ROOT_DIR/sys"
cp /etc/resolv.conf "$ROOT_DIR/etc/resolv.conf" 2>/dev/null || true

cat <<'CHROOT_SCRIPT' > "$ROOT_DIR/install_pkgs.sh"
#!/bin/bash
set -e
export DEBIAN_FRONTEND=noninteractive

# Allow pip system-wide
mkdir -p /etc/pip
cat > /etc/pip/pip.conf <<PIPCONF
[global]
break-system-packages = true
PIPCONF

apt-get update
apt-get install -y --no-install-recommends curl gnupg ca-certificates

# Add Sid for newer packages
echo "deb http://deb.debian.org/debian sid main contrib non-free non-free-firmware" > /etc/apt/sources.list.d/sid.list
cat > /etc/apt/preferences.d/default-release <<PINEOF
Package: *
Pin: release n=bookworm
Pin-Priority: 700

Package: *
Pin: release n=sid
Pin-Priority: 100
PINEOF

apt-get update

# Kernel + Core
apt-get install -y --no-install-recommends \
    linux-image-amd64 \
    initramfs-tools \
    systemd-sysv \
    grub-efi-amd64-bin grub-pc-bin \
    live-boot live-config live-config-systemd || echo "WARNING: Some live-boot packages failed, trying from sid..."

apt-get install -y --no-install-recommends -t sid live-boot live-config live-config-systemd 2>/dev/null || true

apt-get install -y --no-install-recommends \
    wayland-protocols libwayland-client0 libwayland-server0 \
    python3 python3-pip python3-gi gir1.2-gtk-4.0 \
    python3-dev \
    network-manager \
    plymouth plymouth-themes \
    sudo nano wget git || echo "WARNING: Some packages failed"

apt-get install -y --no-install-recommends gir1.2-adw-1 || true

# Wayland stack
apt-get install -y --no-install-recommends -t sid \
    labwc foot xwayland wlr-randr dbus-x11 swaybg 2>/dev/null || \
    apt-get install -y --no-install-recommends \
    labwc foot xwayland wlr-randr dbus-x11 swaybg 2>/dev/null || \
    echo "WARNING: Some Wayland packages not available"

# Optional
apt-get install -y --no-install-recommends calamares 2>/dev/null || echo "INFO: calamares skipped"
apt-get install -y --no-install-recommends wine 2>/dev/null || echo "INFO: wine skipped"

# Waydroid (optional)
if curl -fsSL --connect-timeout 10 https://repo.waydroid.net/waydroid.gpg 2>/dev/null | gpg --dearmor > /usr/share/keyrings/waydroid.gpg 2>/dev/null; then
    echo "deb [signed-by=/usr/share/keyrings/waydroid.gpg] https://repo.waydroid.net/ bookworm main" > /etc/apt/sources.list.d/waydroid.list
    apt-get update
    apt-get install -y --no-install-recommends waydroid || echo "INFO: waydroid failed"
else
    echo "INFO: Waydroid repo unreachable, skipping"
fi

# Generate initramfs
KVER=$(ls /lib/modules 2>/dev/null | head -n 1)
if [ -n "$KVER" ]; then
    update-initramfs -c -k "$KVER" || echo "WARNING: initramfs issues"
else
    echo "WARNING: No kernel found in /lib/modules"
fi

apt-get clean
rm -rf /var/lib/apt/lists/*
CHROOT_SCRIPT

chmod +x "$ROOT_DIR/install_pkgs.sh"
chroot "$ROOT_DIR" /install_pkgs.sh
rm -f "$ROOT_DIR/install_pkgs.sh"

echo -e "${GREEN}  ✓ Packages installed ($(time_elapsed))${RESET}"

# ─── 4. Inject Thakran OS Components ──────────────────────────────────────
step_header 4 "Injecting Thakran OS core components..."

mkdir -p "$ROOT_DIR/opt/thakran"/{ai,desktop,apps,system,cloud,installer}
mkdir -p "$ROOT_DIR/etc/systemd/system"

# Copy components (using rsync for speed on multi-core)
rsync -a "$PROJECT_ROOT/ai/"       "$ROOT_DIR/opt/thakran/ai/"       2>/dev/null || true
rsync -a "$PROJECT_ROOT/desktop/"  "$ROOT_DIR/opt/thakran/desktop/"  2>/dev/null || true
rsync -a "$PROJECT_ROOT/apps/"     "$ROOT_DIR/opt/thakran/apps/"     2>/dev/null || true
rsync -a "$PROJECT_ROOT/cloud/"    "$ROOT_DIR/opt/thakran/cloud/"    2>/dev/null || true
rsync -a "$PROJECT_ROOT/installer/" "$ROOT_DIR/opt/thakran/installer/" 2>/dev/null || true

cp "$PROJECT_ROOT/boot/systemd/"*.service "$ROOT_DIR/etc/systemd/system/" 2>/dev/null || true

# Boot themes
mkdir -p "$ROOT_DIR/boot/grub/themes/thakran"
rsync -a "$PROJECT_ROOT/boot/grub/thakran-grub-theme/" "$ROOT_DIR/boot/grub/themes/thakran/" 2>/dev/null || true
rsync -a "$PROJECT_ROOT/boot/plymouth/" "$ROOT_DIR/usr/share/plymouth/themes/" 2>/dev/null || true

# Python AI packages (non-fatal)
chroot "$ROOT_DIR" /bin/bash -c "pip3 install llama-cpp-python huggingface-hub 2>/dev/null" || echo "INFO: Python AI packages skipped"

# Enable services
chroot "$ROOT_DIR" /bin/bash -c "systemctl enable NetworkManager 2>/dev/null" || true
chroot "$ROOT_DIR" /bin/bash -c "systemctl enable thakran-aid 2>/dev/null" || true

# Create live user
chroot "$ROOT_DIR" /bin/bash -c "id thakran &>/dev/null || (useradd -m -G sudo,video,audio,plugdev,input,render -s /bin/bash thakran && echo 'thakran:thakran' | chpasswd)"

# Set hostname
echo "thakran-os" > "$ROOT_DIR/etc/hostname"
cat > "$ROOT_DIR/etc/hosts" <<HOSTSEOF
127.0.0.1   localhost
127.0.1.1   thakran-os
HOSTSEOF

# Wayland session launcher
mkdir -p "$ROOT_DIR/usr/lib/thakran/desktop"
cat > "$ROOT_DIR/usr/lib/thakran/desktop/start-shell.sh" <<'SHELLSCRIPT'
#!/bin/bash
export XDG_RUNTIME_DIR="/tmp/runtime-$(id -u)"
mkdir -p "$XDG_RUNTIME_DIR"
chmod 0700 "$XDG_RUNTIME_DIR"

export XDG_SESSION_TYPE=wayland
export XDG_CURRENT_DESKTOP=Thakran
export QT_QPA_PLATFORM=wayland
export MOZ_ENABLE_WAYLAND=1
export THAKRAN_AI_SOCKET=/run/thakran/ai.sock

export WLR_RENDERER=pixman
export WLR_NO_HARDWARE_CURSORS=1
export LIBGL_ALWAYS_SOFTWARE=1

mkdir -p "$HOME/.config/labwc"

cat > "$HOME/.config/labwc/autostart" <<'AUTOSTART'
swaybg -c '#0a0a1a' &
python3 /opt/thakran/desktop/shell/panel.py &
foot &
AUTOSTART

if [ ! -f "$HOME/.config/labwc/rc.xml" ]; then
cat > "$HOME/.config/labwc/rc.xml" <<'RCXML'
<?xml version="1.0"?>
<labwc_config>
  <theme><name>Adwaita</name></theme>
  <keyboard>
    <keybind key="A-Return"><action name="Execute"><command>foot</command></action></keybind>
    <keybind key="A-F4"><action name="Close"/></keybind>
    <keybind key="A-Tab"><action name="NextWindow"/></keybind>
    <keybind key="W-space"><action name="Execute"><command>python3 /opt/thakran/desktop/shell/launcher.py</command></action></keybind>
  </keyboard>
</labwc_config>
RCXML
fi

exec dbus-run-session labwc
SHELLSCRIPT
chmod +x "$ROOT_DIR/usr/lib/thakran/desktop/start-shell.sh"

# Create 'user' account
chroot "$ROOT_DIR" /bin/bash -c '
    if ! id user >/dev/null 2>&1; then
        useradd -m -s /bin/bash -G sudo,audio,video,cdrom,plugdev user
    fi
    passwd -d user
'
echo "user ALL=(ALL) NOPASSWD: ALL" > "$ROOT_DIR/etc/sudoers.d/live-user"
chmod 440 "$ROOT_DIR/etc/sudoers.d/live-user"

# TTY1 autologin
mkdir -p "$ROOT_DIR/etc/systemd/system/getty@tty1.service.d"
cat > "$ROOT_DIR/etc/systemd/system/getty@tty1.service.d/autologin.conf" <<'AUTOLOGIN'
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin user --noclear %I $TERM
Type=idle
AUTOLOGIN

# Auto-start Wayland on TTY1
mkdir -p "$ROOT_DIR/home/user"
cat > "$ROOT_DIR/home/user/.bash_profile" <<'BASHPROFILE'
if [ -z "$WAYLAND_DISPLAY" ] && [ "$(tty)" = "/dev/tty1" ]; then
    exec /usr/lib/thakran/desktop/start-shell.sh
fi
BASHPROFILE
cp "$ROOT_DIR/home/user/.bash_profile" "$ROOT_DIR/etc/skel/.bash_profile"
chroot "$ROOT_DIR" /bin/bash -c 'chown -R user:user /home/user' 2>/dev/null || true

echo -e "${GREEN}  ✓ Thakran OS components injected ($(time_elapsed))${RESET}"

# ─── 5. Unmount Chroot ────────────────────────────────────────────────────
step_header 5 "Cleaning up chroot mounts..."

sync
for mnt in sys proc run dev/pts dev; do
    umount "$ROOT_DIR/$mnt" 2>/dev/null || true
done

echo -e "${GREEN}  ✓ Chroot mounts cleaned ($(time_elapsed))${RESET}"

# ─── 6. Compress Filesystem (ZSTD Multi-threaded) ────────────────────────
step_header 6 "Compressing rootfs → SquashFS (${COMP_ALGO}, $(nproc) cores)..."

rm -rf "$ISO_DIR"
mkdir -p "$ISO_DIR/live" "$ISO_DIR/boot/grub" "$ISO_DIR/EFI/boot" "$ISO_DIR/isolinux"

rm -f "$ISO_DIR/live/filesystem.squashfs"

echo -e "${CYAN}  ⚡ Using ${COMP_ALGO} compression with $(nproc) threads${RESET}"
echo -e "${CYAN}  ⚡ Block size: ${BLOCK_SIZE} bytes (1 MB)${RESET}"
echo -e "${CYAN}  ⚡ This is ~3-5x faster and ~30-40% smaller than gzip${RESET}"

mksquashfs "$ROOT_DIR" "$ISO_DIR/live/filesystem.squashfs" \
    -comp "$COMP_ALGO" \
    $COMP_OPTS \
    -b "$BLOCK_SIZE" \
    -processors "$PROCESSORS" \
    -noappend \
    -no-exports \
    -xattrs \
    -wildcards \
    -e 'var/cache/apt/*' \
    -e 'var/lib/apt/lists/*' \
    -e 'tmp/*' \
    -e 'var/tmp/*' \
    -e 'usr/share/doc/*' \
    -e 'usr/share/man/*' \
    -e 'usr/share/info/*' \
    -e 'usr/share/locale/!(en*)' \
    -progress

SQUASH_SIZE=$(du -h "$ISO_DIR/live/filesystem.squashfs" | cut -f1)
echo -e "${GREEN}  ✓ SquashFS created: ${SQUASH_SIZE} ($(time_elapsed))${RESET}"

# Copy kernel and initrd
cp "$ROOT_DIR"/boot/vmlinuz-* "$ISO_DIR/live/vmlinuz" 2>/dev/null || { echo -e "${RED}ERROR: No vmlinuz found!${RESET}"; exit 1; }
cp "$ROOT_DIR"/boot/initrd.img-* "$ISO_DIR/live/initrd" 2>/dev/null || { echo -e "${RED}ERROR: No initrd found!${RESET}"; exit 1; }

echo -e "${GREEN}  ✓ Kernel + initrd copied ($(time_elapsed))${RESET}"

# ─── 7. Generate ISO (UEFI + BIOS) ───────────────────────────────────────
step_header 7 "Generating bootable ISO (UEFI + BIOS)..."

# GRUB config
cat <<GRUBEOF > "$ISO_DIR/boot/grub/grub.cfg"
set timeout=5
set default=0
search --set=root --file /live/vmlinuz

menuentry "Start Thakran OS Live" {
    linux /live/vmlinuz boot=live systemd.unit=multi-user.target
    initrd /live/initrd
}
menuentry "Start Thakran OS (Safe Mode)" {
    linux /live/vmlinuz boot=live nomodeset systemd.unit=multi-user.target debug ignore_loglevel
    initrd /live/initrd
}
menuentry "Install Thakran OS" {
    linux /live/vmlinuz boot=live systemd.unit=multi-user.target only-ubiquity
    initrd /live/initrd
}
GRUBEOF

# EFI boot image
grub-mkstandalone \
    --format=x86_64-efi \
    --output="$ISO_DIR/EFI/boot/bootx64.efi" \
    --locales="" \
    --fonts="" \
    "boot/grub/grub.cfg=$ISO_DIR/boot/grub/grub.cfg"

EFI_IMG="$ISO_DIR/boot/efi.img"
dd if=/dev/zero of="$EFI_IMG" bs=1M count=4
mkfs.vfat "$EFI_IMG"
mmd -i "$EFI_IMG" ::/EFI ::/EFI/boot
mcopy -i "$EFI_IMG" "$ISO_DIR/EFI/boot/bootx64.efi" ::/EFI/boot/bootx64.efi

# BIOS boot image
grub-mkstandalone \
    --format=i386-pc \
    --output="$ISO_DIR/boot/grub/bios.img" \
    --install-modules="linux normal iso9660 biosdisk memdisk search search_fs_file tar ls" \
    --modules="linux normal iso9660 biosdisk search search_fs_file" \
    --locales="" \
    --fonts="" \
    "boot/grub/grub.cfg=$ISO_DIR/boot/grub/grub.cfg"

BIOS_CORE="$ISO_DIR/boot/grub/bios.img"
if [ -f /usr/lib/grub/i386-pc/cdboot.img ]; then
    cat /usr/lib/grub/i386-pc/cdboot.img "$BIOS_CORE" > "$ISO_DIR/boot/grub/bios_eltorito.img"
    mv "$ISO_DIR/boot/grub/bios_eltorito.img" "$BIOS_CORE"
fi

# Generate final ISO
xorriso -as mkisofs \
    -iso-level 3 \
    -o "$ISO_OUTPUT" \
    -full-iso9660-filenames \
    -volid "THAKRAN_OS" \
    -eltorito-boot boot/grub/bios.img \
    -no-emul-boot -boot-load-size 4 -boot-info-table \
    --eltorito-catalog boot/grub/boot.cat \
    --grub2-boot-info \
    --grub2-mbr /usr/lib/grub/i386-pc/boot_hybrid.img \
    -eltorito-alt-boot \
    -e boot/efi.img \
    -no-emul-boot \
    -append_partition 2 0xef "$EFI_IMG" \
    "$ISO_DIR"

# ─── Done! ────────────────────────────────────────────────────────────────
FINAL_SIZE=$(du -h "$ISO_OUTPUT" | cut -f1)
TOTAL_TIME=$(time_elapsed)

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════════╗${RESET}"
echo -e "${GREEN}║  ✅ Thakran OS ISO Built Successfully!                          ║${RESET}"
echo -e "${GREEN}╠══════════════════════════════════════════════════════════════════╣${RESET}"
echo -e "${GREEN}║  📀 File: $(basename "$ISO_OUTPUT")${RESET}"
echo -e "${GREEN}║  📦 Size: ${FINAL_SIZE}${RESET}"
echo -e "${GREEN}║  🗜️  Compression: ${COMP_ALGO} ($(nproc) cores)${RESET}"
echo -e "${GREEN}║  ⏱️  Time: ${TOTAL_TIME}${RESET}"
echo -e "${GREEN}║  💽 Boot: UEFI + Legacy BIOS${RESET}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════════╝${RESET}"
echo ""
echo -e "${CYAN}📥 To download, run:${RESET}"
echo -e "${YELLOW}   # In Codespace terminal:${RESET}"
echo -e "${YELLOW}   #   Right-click the file in the Explorer panel → Download${RESET}"
echo -e "${YELLOW}   # Or use the CLI:${RESET}"
echo -e "${YELLOW}   #   gh codespace cp remote:$(echo "$ISO_OUTPUT" | sed "s|$PROJECT_ROOT|/workspaces/$(basename "$PROJECT_ROOT")|") .${RESET}"
echo ""
