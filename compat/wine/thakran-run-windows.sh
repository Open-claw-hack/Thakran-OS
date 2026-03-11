#!/bin/bash
# ============================================================================
# Thakran OS — Universal App Launcher (Wine / Proton)
# ============================================================================
# Seamlessly runs Windows executables (.exe, .msi) as if they were native.
# Integrates with the Wayland desktop (Wayland driver for Wine).
# 
# Usage: thakran-run-windows <path-to.exe>
# ============================================================================

set -euo pipefail

EXE_PATH="$1"
WINE_PREFIX="$HOME/.local/share/thakran/compat/windows"
THAKRAN_THEME="$HOME/.config/thakran/theme/colors.json"

if [ -z "$EXE_PATH" ]; then
    echo "Usage: thakran-run-windows <path-to.exe>"
    exit 1
fi

echo "🚀 Launching Windows App: $(basename "$EXE_PATH")"

# ─── Initialize Prefix ──────────────────────────────────────────────────
if [ ! -d "$WINE_PREFIX" ]; then
    echo "📦 Initializing Windows compatibility layer..."
    mkdir -p "$WINE_PREFIX"
    WINEPREFIX="$WINE_PREFIX" wineboot --init
    
    # Configure Wine for Wayland (no X11 overhead)
    cat > /tmp/wayland.reg << 'EOF'
REGEDIT4

[HKEY_CURRENT_USER\Software\Wine\Drivers]
"Graphics"="wayland"

[HKEY_CURRENT_USER\Control Panel\Desktop]
"FontSmoothing"="2"
"FontSmoothingGamma"=dword:00000578
"FontSmoothingOrientation"=dword:00000001
"FontSmoothingType"=dword:00000002
EOF
    WINEPREFIX="$WINE_PREFIX" regedit /tmp/wayland.reg
    rm /tmp/wayland.reg
    
    # Install core fonts and runtimes (dxvk, vkd3d for games)
    if command -v winetricks &> /dev/null; then
        WINEPREFIX="$WINE_PREFIX" winetricks -q corefonts dxvk vkd3d
    fi
fi

# ─── Match Thakran OS Theme ─────────────────────────────────────────────
# This extracts the dark/light preference and injects it into Wine
if [ -f "$THAKRAN_THEME" ]; then
    THEME_MODE=$(grep '"mode":' "$THAKRAN_THEME" | cut -d'"' -f4 || echo "dark")
    if [ "$THEME_MODE" == "dark" ]; then
        # Apply dark theme to Wine
        WINEPREFIX="$WINE_PREFIX" wine reg add 'HKCU\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize' /v AppsUseLightTheme /t REG_DWORD /d 0 /f >/dev/null 2>&1
    else
        WINEPREFIX="$WINE_PREFIX" wine reg add 'HKCU\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize' /v AppsUseLightTheme /t REG_DWORD /d 1 /f >/dev/null 2>&1
    fi
fi

# ─── Launch Application ─────────────────────────────────────────────────
# Use Esync/Fsync for massive performance improvements
export WINEPREFIX="$WINE_PREFIX"
export WINEESYNC=1
export WINEFSYNC=1
export WINEDEBUG="-all" # Silence terminal spam

# If it's a huge app, allocate more resources
if [ $(stat -c%s "$EXE_PATH") -gt 104857600 ]; then # >100MB
    echo "⚡ Activating high-performance mode for large application"
    # Launch with high scheduling priority
    nice -n -5 wine "$EXE_PATH"
else
    wine "$EXE_PATH"
fi
