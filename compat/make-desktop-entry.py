#!/usr/bin/env python3
"""
============================================================================
Thakran OS — Desktop App Generator
============================================================================
Automatically generates native .desktop shortcuts for apps installed via
our compatibility layers (Wine, Waydroid, Darling, PWA).
Makes universal apps searchable in the Launcher and launchable via Panel.
============================================================================
"""

import os
import sys
import uuid
import subprocess
from pathlib import Path


DESKTOP_ENTRY_TEMPLATE = """[Desktop Entry]
Version=1.0
Type=Application
Name={name}
Comment={comment}
Exec={exec_cmd}
Icon={icon}
Categories={categories}
Terminal=false
StartupWMClass={wmclass}
"""

def generate_entry(app_type: str, source_path: str, name: str, icon: str = ""):
    desktop_dir = Path.home() / ".local" / "share" / "applications" / "thakran-compat"
    desktop_dir.mkdir(parents=True, exist_ok=True)
    
    safe_name = name.lower().replace(" ", "-").replace("/", "")
    desktop_file = desktop_dir / f"{app_type}-{safe_name}.desktop"
    
    if app_type == "windows":
        exec_cmd = f"thakran-run-windows '{os.path.abspath(source_path)}'"
        comment = "Windows Application (Wine)"
        categories = "Wine;Windows;"
        icon = icon or "application-x-executable-symbolic" # Could extract .exe icon here
        wmclass = safe_name
        
    elif app_type == "android":
        # For Android, source_path is the package name (e.g. com.whatsapp)
        exec_cmd = f"thakran-run-android {source_path}"
        comment = "Android Application (Waydroid)"
        categories = "Android;"
        icon = icon or f"waydroid.{source_path}"
        wmclass = source_path
        
    elif app_type == "macos":
        exec_cmd = f"thakran-run-macos '{os.path.abspath(source_path)}'"
        comment = "macOS Application (Darling)"
        categories = "macOS;"
        icon = icon or "apple-symbolic"
        wmclass = safe_name
        
    elif app_type == "ios" or app_type == "pwa":
        # iOS/Web apps run as chromeless browser instances
        exec_cmd = f"epiphany --application-mode '{source_path}'" # source_path is URL
        comment = "Web Application (PWA)"
        categories = "Network;WebBrowser;"
        icon = icon or "web-browser-symbolic"
        wmclass = f"epiphany-{safe_name}"
    else:
        print(f"Unknown app type: {app_type}")
        sys.exit(1)
        
    content = DESKTOP_ENTRY_TEMPLATE.format(
        name=name,
        comment=comment,
        exec_cmd=exec_cmd,
        icon=icon,
        categories=categories,
        wmclass=wmclass
    )
    
    with open(desktop_file, "w") as f:
        f.write(content)
        
    # Make executable
    os.chmod(desktop_file, 0o755)
    
    print(f"✅ Created native desktop shortcut: {desktop_file}")
    
    # Reload desktop database
    try:
        subprocess.run(["update-desktop-database", str(desktop_dir)], check=False)
    except FileNotFoundError:
        pass


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: make-desktop-entry.py <type: windows|android|macos|pwa> <path_or_url> <App Name> [icon_name]")
        sys.exit(1)
        
    app_type = sys.argv[1]
    source = sys.argv[2]
    name = sys.argv[3]
    icon = sys.argv[4] if len(sys.argv) > 4 else ""
    
    generate_entry(app_type, source, name, icon)
