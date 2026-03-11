#!/bin/bash
# ============================================================================
# Thakran OS — macOS App Integration (Darling)
# ============================================================================
# Runs macOS executables and .app bundles using Darling translation layer.
# Note: GUI support is currently experimental.
#
# Usage: thakran-run-macos <path-to.app>
# ============================================================================

set -euo pipefail

APP_PATH="$1"

if [ -z "$APP_PATH" ]; then
    echo "Usage: thakran-run-macos <path-to.app>"
    exit 1
fi

echo "🍎 Launching macOS App: $(basename "$APP_PATH")"

# Darling requires an initialized prefix (~/.darling)
if [ ! -d "$HOME/.darling" ]; then
    echo "📦 Initializing macOS compatibility layer..."
    # Darling auto-initializes on first run
    darling shell echo "Prefix initialized"
fi

# If it's a .app bundle, launch using 'open' command inside darling
if [[ "$APP_PATH" == *.app ]]; then
    # Convert Linux absolute path to Darling's /Volumes/SystemRoot/... path
    DARLING_PATH="/Volumes/SystemRoot$(realpath "$APP_PATH")"
    darling shell open "$DARLING_PATH"
else
    # Direct executable
    darling "$APP_PATH"
fi
