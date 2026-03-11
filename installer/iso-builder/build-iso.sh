#!/bin/bash
# ============================================================================
# Thakran OS — Bootable ISO Generator
# ============================================================================
# Creates a live, bootable ISO image of Thakran OS.
# Uses debootstrap for base Debian filesystem, installs packages,
# copies Thakran OS components, and generates a UEFI+BIOS bootable ISO.
# ============================================================================

set -e

# Configuration
OS_NAME="thakran-os"
VERSION=$(cat /workspace/VERSION 2>/dev/null || echo "0.1.0-alpha")
ARCH=${1:-"amd64"}
ROOT_DIR="/tmp/thakran-iso-root"
ISO_DIR="$(pwd)/image"
ISO_NAME="${OS_NAME}-${VERSION}-${ARCH}.iso"

echo -e "\e[1;35m=====================================================================\e[0m"
echo -e "\e[1;36m 💿 Thakran OS — ISO Generator ($ARCH) v${VERSION}\e[0m"
echo -e "\e[1;35m=====================================================================\e[0m"

if [ "$EUID" -ne 0 ]; then
  echo -e "\e[1;31m❌ Please run as root (or inside the build-env container)\e[0m"
  exit 1
fi

# ─── 1. Clean previous build ──────────────────────────────────────────────
echo -e "\n\e[1;33m[1/7] Cleaning workspace...\e[0m"
rm -rf "$ISO_DIR"
mkdir -p "$ISO_DIR/live" "$ISO_DIR/boot/grub" "$ISO_DIR/EFI/boot" "$ISO_DIR/isolinux"

# ─── 2. Build Base Filesystem (skip if cached) ────────────────────────────
echo -e "\e[1;33m[2/7] Building Base rootfs (debootstrap)...\e[0m"

DEBOOTSTRAP_CACHE="/tmp/thakran-debootstrap-cache"

if [ -d "$ROOT_DIR/bin" ] && [ -d "$ROOT_DIR/usr" ] && [ -f "$ROOT_DIR/etc/os-release" ]; then
    echo -e "\e[1;32m  ✓ Reusing cached rootfs from previous build\e[0m"
    echo "  (Delete $ROOT_DIR manually to force a fresh debootstrap)"
else
    rm -rf "$ROOT_DIR"
    mkdir -p "$ROOT_DIR"
    mkdir -p "$DEBOOTSTRAP_CACHE"

    # Use cache directory to avoid re-downloading .deb packages
    debootstrap --arch=$ARCH --cache-dir="$DEBOOTSTRAP_CACHE" bookworm "$ROOT_DIR" http://deb.debian.org/debian/
fi

# ─── 3. Chroot Setup & Package Installation ──────────────────────────────
echo -e "\e[1;33m[3/7] Installing Core Packages into rootfs...\e[0m"

# Bind mounts for chroot (unmount first in case of leftover mounts)
umount "$ROOT_DIR/sys"  2>/dev/null || true
umount "$ROOT_DIR/proc" 2>/dev/null || true
umount "$ROOT_DIR/run"  2>/dev/null || true
umount "$ROOT_DIR/dev/pts" 2>/dev/null || true
umount "$ROOT_DIR/dev"  2>/dev/null || true

mount --bind /dev "$ROOT_DIR/dev"
mount --bind /run "$ROOT_DIR/run"
mount -t proc none "$ROOT_DIR/proc"
mount -t sysfs none "$ROOT_DIR/sys"

# Copy resolv.conf for network inside chroot
cp /etc/resolv.conf "$ROOT_DIR/etc/resolv.conf" 2>/dev/null || true

cat <<'CHROOT_SCRIPT' > "$ROOT_DIR/install_pkgs.sh"
#!/bin/bash
set -e
export DEBIAN_FRONTEND=noninteractive

# Allow pip to install system-wide packages (Debian Bookworm restriction)
mkdir -p /etc/pip
cat > /etc/pip/pip.conf <<PIPCONF
[global]
break-system-packages = true
PIPCONF

# Essential tools for repo management
apt-get update
apt-get install -y --no-install-recommends curl gnupg ca-certificates

# Add Sid/Testing repositories for modern packages
echo "deb http://deb.debian.org/debian sid main contrib non-free non-free-firmware" > /etc/apt/sources.list.d/sid.list

# Pin bookworm as default, only use sid when needed
cat > /etc/apt/preferences.d/default-release <<PINEOF
Package: *
Pin: release n=bookworm
Pin-Priority: 700

Package: *
Pin: release n=sid
Pin-Priority: 100
PINEOF

apt-get update

# Install Kernel and Core System
apt-get install -y --no-install-recommends \
    linux-image-amd64 \
    initramfs-tools \
    systemd-sysv \
    grub-efi-amd64-bin grub-pc-bin \
    live-boot live-config live-config-systemd || echo "WARNING: Some live-boot packages failed, trying from sid..."

# Try from sid if not in bookworm
apt-get install -y --no-install-recommends -t sid live-boot live-config live-config-systemd 2>/dev/null || true

apt-get install -y --no-install-recommends \
    wayland-protocols libwayland-client0 libwayland-server0 \
    python3 python3-pip python3-gi gir1.2-gtk-4.0 \
    python3-dev \
    network-manager \
    plymouth plymouth-themes \
    sudo nano wget git || echo "WARNING: Some packages failed to install"

# Install GTK4/Adwaita (needed for desktop shell)
apt-get install -y --no-install-recommends gir1.2-adw-1 || true

# Install Wayland display stack (labwc compositor + foot terminal)
apt-get install -y --no-install-recommends -t sid \
    labwc foot xwayland wlr-randr dbus-x11 swaybg 2>/dev/null || \
    apt-get install -y --no-install-recommends \
    labwc foot xwayland wlr-randr dbus-x11 swaybg 2>/dev/null || \
    echo "WARNING: Some Wayland packages not available"

# Calamares and Wine are optional — don't fail the build
apt-get install -y --no-install-recommends calamares 2>/dev/null || echo "INFO: calamares not available, skipping"
apt-get install -y --no-install-recommends wine 2>/dev/null || echo "INFO: wine not available, skipping"

# Install Waydroid (optional — repo may be unreachable)
if curl -fsSL --connect-timeout 10 https://repo.waydroid.net/waydroid.gpg 2>/dev/null | gpg --dearmor > /usr/share/keyrings/waydroid.gpg 2>/dev/null; then
    echo "deb [signed-by=/usr/share/keyrings/waydroid.gpg] https://repo.waydroid.net/ bookworm main" > /etc/apt/sources.list.d/waydroid.list
    apt-get update
    apt-get install -y --no-install-recommends waydroid || echo "INFO: waydroid install failed, skipping"
else
    echo "INFO: Waydroid repo unreachable, skipping"
fi

# NOTE: libwlroots-dev removed — not needed (we use labwc) and conflicts with sid libinput

# Generate initial ramdisk for the kernel
KVER=$(ls /lib/modules 2>/dev/null | head -n 1)
if [ -n "$KVER" ]; then
    update-initramfs -c -k "$KVER" || echo "WARNING: initramfs generation had issues"
else
    echo "WARNING: No kernel found in /lib/modules, initrd might fail"
fi

# Clean up apt cache
apt-get clean
rm -rf /var/lib/apt/lists/*
CHROOT_SCRIPT

chmod +x "$ROOT_DIR/install_pkgs.sh"
chroot "$ROOT_DIR" /install_pkgs.sh
rm -f "$ROOT_DIR/install_pkgs.sh"

# ─── 4. Inject Thakran OS Custom Code ─────────────────────────────────────
echo -e "\e[1;33m[4/7] Injecting Thakran OS core components...\e[0m"

# Create directory structure
mkdir -p "$ROOT_DIR/opt/thakran"/{ai,desktop,apps,system,cloud,installer}
mkdir -p "$ROOT_DIR/etc/systemd/system"

# Copy AI Daemon
cp -r /workspace/ai/* "$ROOT_DIR/opt/thakran/ai/" 2>/dev/null || true
# Copy Desktop Compositor & Shell
cp -r /workspace/desktop/* "$ROOT_DIR/opt/thakran/desktop/" 2>/dev/null || true
# Copy Apps
cp -r /workspace/apps/* "$ROOT_DIR/opt/thakran/apps/" 2>/dev/null || true
# Copy System Services
cp /workspace/boot/systemd/*.service "$ROOT_DIR/etc/systemd/system/" 2>/dev/null || true
# Copy Cloud and Installer features
cp -r /workspace/cloud/* "$ROOT_DIR/opt/thakran/cloud/" 2>/dev/null || true
cp -r /workspace/installer/* "$ROOT_DIR/opt/thakran/installer/" 2>/dev/null || true

# Copy boot theme files
mkdir -p "$ROOT_DIR/boot/grub/themes/thakran"
cp -r /workspace/boot/grub/thakran-grub-theme/* "$ROOT_DIR/boot/grub/themes/thakran/" 2>/dev/null || true
cp -r /workspace/boot/plymouth/* "$ROOT_DIR/usr/share/plymouth/themes/" 2>/dev/null || true

# Install Python requirements inside chroot (non-fatal)
chroot "$ROOT_DIR" /bin/bash -c "pip3 install llama-cpp-python huggingface-hub 2>/dev/null" || echo "INFO: Python AI packages install skipped (build deps may be missing)"

# Enable services (non-fatal — services may reference paths that don't exist yet)
chroot "$ROOT_DIR" /bin/bash -c "systemctl enable NetworkManager 2>/dev/null" || true
chroot "$ROOT_DIR" /bin/bash -c "systemctl enable thakran-aid 2>/dev/null" || true
# NOTE: thakran-desktop.service requires the custom compositor binary which is not yet compiled.
# We use autologin + labwc instead.

# Add Live User
chroot "$ROOT_DIR" /bin/bash -c "id thakran &>/dev/null || (useradd -m -G sudo,video,audio,plugdev,input,render -s /bin/bash thakran && echo 'thakran:thakran' | chpasswd)"

# Set hostname
echo "thakran-os" > "$ROOT_DIR/etc/hostname"
cat > "$ROOT_DIR/etc/hosts" <<HOSTSEOF
127.0.0.1   localhost
127.0.1.1   thakran-os
HOSTSEOF

# ─── Create start-shell.sh (Wayland session launcher) ─────────────────────
mkdir -p "$ROOT_DIR/usr/lib/thakran/desktop"
cat > "$ROOT_DIR/usr/lib/thakran/desktop/start-shell.sh" <<'SHELLSCRIPT'
#!/bin/bash
# Thakran OS — Wayland Session Launcher
# Starts labwc compositor with the Thakran shell components

export XDG_RUNTIME_DIR="/tmp/runtime-$(id -u)"
mkdir -p "$XDG_RUNTIME_DIR"
chmod 0700 "$XDG_RUNTIME_DIR"

export XDG_SESSION_TYPE=wayland
export XDG_CURRENT_DESKTOP=Thakran
export QT_QPA_PLATFORM=wayland
export MOZ_ENABLE_WAYLAND=1
export THAKRAN_AI_SOCKET=/run/thakran/ai.sock

# Software rendering fallback (needed for VirtualBox / no GPU)
export WLR_RENDERER=pixman
export WLR_NO_HARDWARE_CURSORS=1
export LIBGL_ALWAYS_SOFTWARE=1

# Create labwc config directory
mkdir -p "$HOME/.config/labwc"

# Write labwc autostart — launch Thakran shell components
cat > "$HOME/.config/labwc/autostart" <<'AUTOSTART'
# Set dark background
swaybg -c '#0a0a1a' &

# Launch Thakran panel (taskbar)
python3 /opt/thakran/desktop/shell/panel.py &

# Launch a terminal emulator
foot &
AUTOSTART

# Write labwc rc.xml for basic keybindings
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

# Start labwc (this blocks until the session ends)
exec dbus-run-session labwc
SHELLSCRIPT
chmod +x "$ROOT_DIR/usr/lib/thakran/desktop/start-shell.sh"

# ─── Create the 'user' account directly in the rootfs ─────────────────────────
# This is the GUARANTEED way to have the account ready at boot time.
# live-config's dynamic user creation is unreliable with --no-install-recommends.
chroot "$ROOT_DIR" /bin/bash -c '
    # Create user with home directory if it does not exist
    if ! id user >/dev/null 2>&1; then
        useradd -m -s /bin/bash -G sudo,audio,video,cdrom,plugdev user
    fi
    # Delete password so agetty autologin works (no password prompt)
    passwd -d user
'
# Give passwordless sudo
echo "user ALL=(ALL) NOPASSWD: ALL" > "$ROOT_DIR/etc/sudoers.d/live-user"
chmod 440 "$ROOT_DIR/etc/sudoers.d/live-user"

# ─── Configure TTY1 autologin for 'user' ─────────────────────────────────────
mkdir -p "$ROOT_DIR/etc/systemd/system/getty@tty1.service.d"
cat > "$ROOT_DIR/etc/systemd/system/getty@tty1.service.d/autologin.conf" <<'AUTOLOGIN'
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin user --noclear %I $TERM
Type=idle
AUTOLOGIN

# ─── Configure .bash_profile to auto-start Wayland on TTY1 ───────────────
mkdir -p "$ROOT_DIR/home/user"
cat > "$ROOT_DIR/home/user/.bash_profile" <<'BASHPROFILE'
# Auto-start Thakran Desktop on TTY1
if [ -z "$WAYLAND_DISPLAY" ] && [ "$(tty)" = "/dev/tty1" ]; then
    exec /usr/lib/thakran/desktop/start-shell.sh
fi
BASHPROFILE
# Also put it in /etc/skel as a fallback
cp "$ROOT_DIR/home/user/.bash_profile" "$ROOT_DIR/etc/skel/.bash_profile"
chroot "$ROOT_DIR" /bin/bash -c 'chown -R user:user /home/user' 2>/dev/null || true

# ─── 5. Unmount chroot binds ──────────────────────────────────────────────
echo -e "\e[1;33m[5/7] Cleaning up chroot mounts...\e[0m"
sync
umount "$ROOT_DIR/sys"  2>/dev/null || true
umount "$ROOT_DIR/proc" 2>/dev/null || true
umount "$ROOT_DIR/run"  2>/dev/null || true
umount "$ROOT_DIR/dev/pts" 2>/dev/null || true
umount "$ROOT_DIR/dev"  2>/dev/null || true

# ─── 6. Compress Filesystem ───────────────────────────────────────────────
echo -e "\e[1;33m[6/7] Compressing rootfs into SquashFS...\e[0m"
rm -f "$ISO_DIR/live/filesystem.squashfs"
mksquashfs "$ROOT_DIR" "$ISO_DIR/live/filesystem.squashfs" -comp gzip -b 262144 -noappend

# Copy kernel and initrd from the rootfs
cp "$ROOT_DIR"/boot/vmlinuz-* "$ISO_DIR/live/vmlinuz" 2>/dev/null || { echo "ERROR: No vmlinuz found!"; exit 1; }
cp "$ROOT_DIR"/boot/initrd.img-* "$ISO_DIR/live/initrd" 2>/dev/null || { echo "ERROR: No initrd found!"; exit 1; }

# ─── 7. Generate ISO (UEFI + BIOS dual boot) ─────────────────────────────
echo -e "\e[1;33m[7/7] Generating Bootable ISO (xorriso)...\e[0m"

# Create GRUB config for the ISO
cat <<GRUBEOF > "$ISO_DIR/boot/grub/grub.cfg"
set timeout=5
set default=0

# Crucial: Find the actual CD/USB drive containing the kernel, 
# otherwise GRUB looks inside the embedded mkstandalone (memdisk)
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

# ── Create EFI boot image ──
grub-mkstandalone \
    --format=x86_64-efi \
    --output="$ISO_DIR/EFI/boot/bootx64.efi" \
    --locales="" \
    --fonts="" \
    "boot/grub/grub.cfg=$ISO_DIR/boot/grub/grub.cfg"

# Create a FAT12/16 EFI system partition image for xorriso
EFI_IMG="$ISO_DIR/boot/efi.img"
dd if=/dev/zero of="$EFI_IMG" bs=1M count=4
mkfs.vfat "$EFI_IMG"
mmd -i "$EFI_IMG" ::/EFI ::/EFI/boot
mcopy -i "$EFI_IMG" "$ISO_DIR/EFI/boot/bootx64.efi" ::/EFI/boot/bootx64.efi

# ── Create BIOS boot image ──
grub-mkstandalone \
    --format=i386-pc \
    --output="$ISO_DIR/boot/grub/bios.img" \
    --install-modules="linux normal iso9660 biosdisk memdisk search search_fs_file tar ls" \
    --modules="linux normal iso9660 biosdisk search search_fs_file" \
    --locales="" \
    --fonts="" \
    "boot/grub/grub.cfg=$ISO_DIR/boot/grub/grub.cfg"

# Prepend cdboot.img to bios.img for El Torito
BIOS_CORE="$ISO_DIR/boot/grub/bios.img"
if [ -f /usr/lib/grub/i386-pc/cdboot.img ]; then
    cat /usr/lib/grub/i386-pc/cdboot.img "$BIOS_CORE" > "$ISO_DIR/boot/grub/bios_eltorito.img"
    mv "$ISO_DIR/boot/grub/bios_eltorito.img" "$BIOS_CORE"
fi

# ── Generate the final ISO ──
xorriso -as mkisofs \
    -iso-level 3 \
    -o "$ISO_NAME" \
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

echo ""
echo -e "\e[1;32m╔══════════════════════════════════════════════════════════════╗\e[0m"
echo -e "\e[1;32m║  ✅ ISO Generated Successfully: $ISO_NAME\e[0m"
echo -e "\e[1;32m╠══════════════════════════════════════════════════════════════╣\e[0m"
echo -e "\e[1;32m║  Size: $(du -h "$ISO_NAME" | cut -f1)\e[0m"
echo -e "\e[1;32m║  Boot: UEFI + Legacy BIOS\e[0m"
echo -e "\e[1;32m╚══════════════════════════════════════════════════════════════╝\e[0m"
echo -e "\e[1;36mYou can now boot this image in QEMU, VirtualBox, or burn it to a USB drive using Rufus.\e[0m"
