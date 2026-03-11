#!/usr/bin/env python3
"""
============================================================================
Thakran OS — System Panel (Taskbar)
============================================================================
The top panel for the Thakran desktop environment.

Features:
  - App menu / activities button
  - AI status indicator (model, inference activity)
  - System tray (network, bluetooth, battery, volume)
  - Clock with calendar popup
  - Notification center
  - Workspace switcher

Built with GTK4 + LibAdwaita for native Wayland rendering.
============================================================================
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, GLib, Gio, Gdk
import json
import os
import socket
import time
from datetime import datetime


class AIStatusIndicator(Gtk.Box):
    """Shows current AI model status and activity."""
    
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.add_css_class("ai-indicator")
        
        # AI dot (pulsing when active)
        self.dot = Gtk.DrawingArea()
        self.dot.set_size_request(8, 8)
        self.dot.set_draw_func(self._draw_dot)
        self.dot.add_css_class("ai-dot")
        self.append(self.dot)
        
        # Status label
        self.label = Gtk.Label(label="AI Ready")
        self.label.add_css_class("ai-label")
        self.append(self.label)
        
        # State
        self.model_name = "thakran-mini"
        self.is_active = False
        self.tokens_per_sec = 0.0
        
        # Poll AI daemon status every 5 seconds
        GLib.timeout_add_seconds(5, self._update_status)
    
    def _draw_dot(self, area, cr, width, height):
        """Draw the AI status dot."""
        cr.set_source_rgba(0.66, 0.33, 0.97, 1.0)  # Purple
        cr.arc(width / 2, height / 2, 4, 0, 2 * 3.14159)
        cr.fill()
    
    def _update_status(self):
        """Poll the AI daemon for current status."""
        try:
            # Connect to the AI daemon socket
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.settimeout(1)
            sock.connect("/run/thakran/ai.sock")
            sock.send(b'{"action": "status"}')
            response = json.loads(sock.recv(4096))
            sock.close()
            
            active_model = response.get("active_model", "none")
            self.model_name = active_model
            
            if active_model != "none":
                self.label.set_text(f"AI: {active_model}")
            else:
                self.label.set_text("AI: Idle")
                
        except (ConnectionRefusedError, FileNotFoundError, socket.timeout):
            self.label.set_text("AI: Offline")
        except Exception:
            pass
        
        return True  # Continue polling


class SystemTray(Gtk.Box):
    """System tray with network, bluetooth, volume, and battery."""
    
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.add_css_class("system-tray")
        
        # Network
        self.network_icon = Gtk.Image.new_from_icon_name("network-wireless-symbolic")
        self.network_btn = Gtk.Button(child=self.network_icon)
        self.network_btn.add_css_class("tray-button")
        self.network_btn.set_tooltip_text("Network")
        self.append(self.network_btn)
        
        # Bluetooth
        self.bt_icon = Gtk.Image.new_from_icon_name("bluetooth-symbolic")
        self.bt_btn = Gtk.Button(child=self.bt_icon)
        self.bt_btn.add_css_class("tray-button")
        self.bt_btn.set_tooltip_text("Bluetooth")
        self.append(self.bt_btn)
        
        # Volume
        self.vol_icon = Gtk.Image.new_from_icon_name("audio-volume-high-symbolic")
        self.vol_btn = Gtk.Button(child=self.vol_icon)
        self.vol_btn.add_css_class("tray-button")
        self.vol_btn.set_tooltip_text("Volume")
        self.append(self.vol_btn)
        
        # Battery (only on laptops)
        if os.path.exists("/sys/class/power_supply/BAT0"):
            self.bat_icon = Gtk.Image.new_from_icon_name("battery-full-symbolic")
            self.bat_btn = Gtk.Button(child=self.bat_icon)
            self.bat_btn.add_css_class("tray-button")
            self.bat_btn.set_tooltip_text("Battery")
            self.append(self.bat_btn)
            GLib.timeout_add_seconds(30, self._update_battery)
    
    def _update_battery(self):
        """Update battery icon."""
        try:
            with open("/sys/class/power_supply/BAT0/capacity") as f:
                percent = int(f.read().strip())
            
            if percent > 80:
                icon = "battery-full-symbolic"
            elif percent > 50:
                icon = "battery-good-symbolic"
            elif percent > 20:
                icon = "battery-low-symbolic"
            else:
                icon = "battery-caution-symbolic"
            
            self.bat_icon.set_from_icon_name(icon)
            self.bat_btn.set_tooltip_text(f"Battery: {percent}%")
        except Exception:
            pass
        return True


class PanelClock(Gtk.Button):
    """Clock widget with date popup."""
    
    def __init__(self):
        super().__init__()
        self.add_css_class("panel-clock")
        
        self.label = Gtk.Label()
        self.set_child(self.label)
        
        self._update_time()
        GLib.timeout_add_seconds(1, self._update_time)
    
    def _update_time(self):
        """Update the clock display."""
        now = datetime.now()
        self.label.set_text(now.strftime("%H:%M"))
        self.set_tooltip_text(now.strftime("%A, %B %d, %Y"))
        return True


class NotificationButton(Gtk.Button):
    """Notification center toggle."""
    
    def __init__(self):
        super().__init__()
        self.add_css_class("notification-button")
        
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        icon = Gtk.Image.new_from_icon_name("preferences-system-notifications-symbolic")
        box.append(icon)
        
        self.badge = Gtk.Label(label="")
        self.badge.add_css_class("notification-badge")
        self.badge.set_visible(False)
        box.append(self.badge)
        
        self.set_child(box)
        self.notification_count = 0
    
    def set_count(self, count):
        """Update notification count badge."""
        self.notification_count = count
        if count > 0:
            self.badge.set_text(str(min(count, 99)))
            self.badge.set_visible(True)
        else:
            self.badge.set_visible(False)


class WorkspaceSwitcher(Gtk.Box):
    """Workspace indicator and switcher."""
    
    def __init__(self, count=4):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.add_css_class("workspace-switcher")
        
        self.workspace_count = count
        self.active_workspace = 0
        self.dots = []
        
        for i in range(count):
            dot = Gtk.Button()
            dot.set_size_request(8, 8)
            dot.add_css_class("workspace-dot")
            if i == 0:
                dot.add_css_class("workspace-active")
            dot.connect("clicked", self._on_workspace_click, i)
            self.dots.append(dot)
            self.append(dot)
    
    def _on_workspace_click(self, button, index):
        """Switch to workspace."""
        self.dots[self.active_workspace].remove_css_class("workspace-active")
        self.active_workspace = index
        self.dots[index].add_css_class("workspace-active")


class ThakranPanel(Adw.Application):
    """Main panel application."""
    
    def __init__(self):
        super().__init__(application_id="dev.thakranos.panel")
        self.connect("activate", self._on_activate)
    
    def _on_activate(self, app):
        """Build and show the panel."""
        # Create window
        window = Gtk.Window(application=app)
        window.set_title("Thakran Panel")
        window.set_default_size(-1, 48)
        window.set_decorated(False)
        
        # Main container
        panel_box = Gtk.CenterBox()
        panel_box.add_css_class("thakran-panel")
        
        # ─── Left Section ─────────────────────────
        left = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        
        # Activities button
        activities_btn = Gtk.Button(label="Activities")
        activities_btn.add_css_class("activities-button")
        left.append(activities_btn)
        
        # AI Status
        ai_status = AIStatusIndicator()
        left.append(ai_status)
        
        panel_box.set_start_widget(left)
        
        # ─── Center Section ───────────────────────
        center = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        
        clock = PanelClock()
        center.append(clock)
        
        panel_box.set_center_widget(center)
        
        # ─── Right Section ────────────────────────
        right = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        
        workspace_switcher = WorkspaceSwitcher(4)
        right.append(workspace_switcher)
        
        system_tray = SystemTray()
        right.append(system_tray)
        
        notifications = NotificationButton()
        right.append(notifications)
        
        panel_box.set_end_widget(right)
        
        # Apply panel
        window.set_child(panel_box)
        
        # Load CSS
        self._load_css()
        
        window.present()
    
    def _load_css(self):
        """Load panel stylesheet."""
        css = b"""
        .thakran-panel {
            background: rgba(10, 10, 26, 0.85);
            padding: 0 16px;
            min-height: 48px;
        }
        
        .activities-button {
            background: transparent;
            border: none;
            color: #f0f0f8;
            font-weight: 600;
            font-size: 14px;
            padding: 4px 12px;
            border-radius: 8px;
        }
        
        .activities-button:hover {
            background: rgba(168, 85, 247, 0.2);
        }
        
        .ai-indicator {
            padding: 4px 8px;
            border-radius: 12px;
            background: rgba(168, 85, 247, 0.1);
        }
        
        .ai-label {
            color: #c084fc;
            font-size: 12px;
            font-weight: 500;
        }
        
        .tray-button {
            background: transparent;
            border: none;
            padding: 4px;
            border-radius: 6px;
            min-width: 24px;
            min-height: 24px;
        }
        
        .tray-button:hover {
            background: rgba(255, 255, 255, 0.1);
        }
        
        .panel-clock {
            background: transparent;
            border: none;
            color: #f0f0f8;
            font-weight: 600;
            font-size: 14px;
        }
        
        .notification-badge {
            background: #ef4444;
            color: white;
            border-radius: 9999px;
            font-size: 10px;
            font-weight: 700;
            padding: 1px 5px;
            min-width: 16px;
        }
        
        .workspace-dot {
            background: rgba(255, 255, 255, 0.2);
            border: none;
            border-radius: 9999px;
            min-width: 8px;
            min-height: 8px;
            padding: 0;
        }
        
        .workspace-active {
            background: #a855f7;
        }
        """
        
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )


def main():
    """Run the panel."""
    app = ThakranPanel()
    app.run()


if __name__ == "__main__":
    main()
