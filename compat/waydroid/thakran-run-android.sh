#!/bin/bash
# ============================================================================
# Thakran OS — Android App Integration (Waydroid)
# ============================================================================
# Seamlessly integrates Android apps (.apk) into the Thakran OS desktop.
# Apps run natively in an LXC container with direct hardware access.
#
# Usage: thakran-run-android <package.name> or <path.apk>
# ============================================================================

set -euo pipefail

TARGET="$1"

if [ -z "$TARGET" ]; then
    echo "Usage: thakran-run-android <package.name | path.apk>"
    exit 1
fi

# ─── Initialize Waydroid if needed ───────────────────────────────────────
if ! systemctl is-active --quiet waydroid-container; then
    echo "🚀 Starting Android subsystem..."
    sudo systemctl start waydroid-container
    
    # Wait for container to boot
    for i in {1..10}; do
        if waydroid status | grep -q "RUNNING"; then break; fi
        sleep 1
    done
fi

# ─── Install APK if path is provided ─────────────────────────────────────
if [[ "$TARGET" == *.apk ]]; then
    echo "📦 Installing Android package: $(basename "$TARGET")"
    waydroid app install "$TARGET"
    
    # Extract package name from dump
    PKG_NAME=$(aapt dump badging "$TARGET" | grep "package: name=" | cut -d"'" -f2)
    echo "✅ Installed: $PKG_NAME"
    TARGET="$PKG_NAME"
fi

# ─── Make Android apps look native ──────────────────────────────────────
# Sync system theme (dark/light mode) to Android
THEME_MODE=$(grep '"mode":' "$HOME/.config/thakran/theme/colors.json" | cut -d'"' -f4 || echo "dark")
if [ "$THEME_MODE" == "dark" ]; then
    waydroid shell cmd uimode night yes
else
    waydroid shell cmd uimode night no
fi

# Enable multi-window mode (freeform windows) to blend with desktop
waydroid prop set persist.waydroid.multi_windows true

# ─── Launch the App ─────────────────────────────────────────────────────
echo "📱 Launching: $TARGET"
waydroid app launch "$TARGET"
