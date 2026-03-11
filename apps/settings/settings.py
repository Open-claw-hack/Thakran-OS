#!/usr/bin/env python3
"""
============================================================================
Thakran OS — System Settings Application
============================================================================
Central settings application for Thakran OS configuration.

Panels:
  - 🖥️ Display & Appearance (theme, wallpaper, fonts, scaling)
  - 🧠 AI & Models (model management, hardware tuning, subscription)
  - 🔊 Sound (output, input, volume, effects)
  - 📡 Network (WiFi, Bluetooth, VPN)
  - 🔋 Power (battery, performance profiles, sleep)
  - 🔒 Security & Privacy (firewall, permissions, encryption)
  - 📦 Apps & Updates (installed apps, updates, defaults)
  - ⌨️ Keyboard & Input (shortcuts, layouts, touchpad)
  - 👤 Users & Accounts (users, login, cloud accounts)
  - ℹ️ About (system info, hardware, version)
============================================================================
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, GLib, Gio
import json
import os


APP_ID = "dev.thakranos.settings"


class SettingsPanel:
    """Base class for settings panels."""
    
    def __init__(self, title, icon, description=""):
        self.title = title
        self.icon = icon
        self.description = description
    
    def build(self) -> Gtk.Widget:
        """Build the panel UI. Override in subclasses."""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        box.set_margin_top(20)
        box.set_margin_bottom(20)
        box.set_margin_start(20)
        box.set_margin_end(20)
        
        title = Gtk.Label(label=self.title, xalign=0)
        title.add_css_class("settings-panel-title")
        box.append(title)
        
        return box


class DisplayPanel(SettingsPanel):
    """Display & Appearance settings."""
    
    def __init__(self):
        super().__init__("Display & Appearance", "preferences-desktop-display-symbolic",
                         "Theme, wallpaper, fonts, and display scaling")
    
    def build(self) -> Gtk.Widget:
        box = super().build()
        
        # Theme section
        theme_group = Adw.PreferencesGroup(title="Theme")
        
        theme_row = Adw.ActionRow(title="Color Scheme", subtitle="Choose dark or light mode")
        theme_switch = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        
        dark_btn = Gtk.ToggleButton(label="Dark")
        dark_btn.set_active(True)
        dark_btn.add_css_class("theme-btn")
        theme_switch.append(dark_btn)
        
        light_btn = Gtk.ToggleButton(label="Light")
        light_btn.add_css_class("theme-btn")
        theme_switch.append(light_btn)
        
        auto_btn = Gtk.ToggleButton(label="Auto")
        auto_btn.add_css_class("theme-btn")
        theme_switch.append(auto_btn)
        
        theme_row.add_suffix(theme_switch)
        theme_group.add(theme_row)
        
        accent_row = Adw.ActionRow(title="Accent Color", subtitle="Choose your accent color")
        theme_group.add(accent_row)
        
        box.append(theme_group)
        
        # Wallpaper section
        wallpaper_group = Adw.PreferencesGroup(title="Wallpaper")
        wp_row = Adw.ActionRow(title="Desktop Wallpaper", subtitle="Choose from built-in or custom images")
        wp_btn = Gtk.Button(label="Browse...")
        wp_row.add_suffix(wp_btn)
        wallpaper_group.add(wp_row)
        box.append(wallpaper_group)
        
        # Font section
        font_group = Adw.PreferencesGroup(title="Fonts")
        
        interface_font = Adw.ActionRow(title="Interface Font", subtitle="Inter")
        font_group.add(interface_font)
        
        mono_font = Adw.ActionRow(title="Monospace Font", subtitle="JetBrains Mono")
        font_group.add(mono_font)
        
        font_size = Adw.ActionRow(title="Font Size")
        size_spin = Gtk.SpinButton.new_with_range(10, 24, 1)
        size_spin.set_value(14)
        font_size.add_suffix(size_spin)
        font_group.add(font_size)
        
        box.append(font_group)
        
        return box


class AIPanel(SettingsPanel):
    """AI & Models settings."""
    
    def __init__(self):
        super().__init__("AI & Models", "thakran-ai-symbolic",
                         "AI model management, hardware tuning, and subscription")
    
    def build(self) -> Gtk.Widget:
        box = super().build()
        
        # Current model
        model_group = Adw.PreferencesGroup(title="Active Model")
        
        model_row = Adw.ActionRow(
            title="thakran-mini (3B)",
            subtitle="Running on CPU • 2.0 GB • Q4_K_M"
        )
        switch_btn = Gtk.Button(label="Switch")
        switch_btn.add_css_class("accent-btn")
        model_row.add_suffix(switch_btn)
        model_group.add(model_row)
        box.append(model_group)
        
        # Hardware
        hw_group = Adw.PreferencesGroup(title="Hardware Acceleration")
        
        device_row = Adw.ActionRow(title="Inference Device", subtitle="Auto-detected")
        device_dropdown = Gtk.DropDown.new_from_strings(["Auto", "CPU", "CUDA", "ROCm", "Vulkan"])
        device_row.add_suffix(device_dropdown)
        hw_group.add(device_row)
        
        threads_row = Adw.ActionRow(title="CPU Threads", subtitle="For CPU inference")
        threads_spin = Gtk.SpinButton.new_with_range(1, 64, 1)
        threads_spin.set_value(6)
        threads_row.add_suffix(threads_spin)
        hw_group.add(threads_row)
        
        ctx_row = Adw.ActionRow(title="Context Length", subtitle="Maximum tokens per conversation")
        ctx_dropdown = Gtk.DropDown.new_from_strings(["1024", "2048", "4096", "8192"])
        ctx_dropdown.set_selected(1)
        ctx_row.add_suffix(ctx_dropdown)
        hw_group.add(ctx_row)
        
        box.append(hw_group)
        
        # Subscription
        sub_group = Adw.PreferencesGroup(title="Cloud AI Subscription")
        
        status_row = Adw.ActionRow(title="Status", subtitle="Not subscribed")
        subscribe_btn = Gtk.Button(label="Subscribe")
        subscribe_btn.add_css_class("suggested-action")
        status_row.add_suffix(subscribe_btn)
        sub_group.add(status_row)
        
        cloud_row = Adw.ActionRow(title="Cloud Models", subtitle="Access GPT-4, Claude, and more")
        sub_group.add(cloud_row)
        
        box.append(sub_group)

        # GitHub Copilot Integration
        copilot_group = Adw.PreferencesGroup(title="GitHub Copilot Integration")
        
        copilot_row = Adw.ActionRow(title="Status", subtitle="Not connected")
        
        def on_copilot_auth(*args):
            # In a real app this triggers the GitHub Device Flow Auth (Oauth)
            # and stores the token in the OS secure keyring.
            dialog = Adw.MessageDialog(heading="GitHub Copilot Authentication")
            dialog.set_body("To route Thakran OS AI requests through Copilot, please visit:\n\nhttps://github.com/login/device\n\nAnd enter code: B8F2-A79X")
            dialog.add_response("cancel", "Cancel")
            dialog.add_response("done", "Done")
            dialog.present()

        auth_btn = Gtk.Button(label="Sign In with GitHub")
        auth_btn.add_css_class("suggested-action")
        auth_btn.connect("clicked", on_copilot_auth)
        copilot_row.add_suffix(auth_btn)
        copilot_group.add(copilot_row)

        copilot_features_row = Adw.ActionRow(title="Use Copilot for system-wide AI", subtitle="Replaces local model for Terminal, File Manager, and Assistant")
        copilot_switch = Gtk.Switch()
        copilot_switch.set_valign(Gtk.Align.CENTER)
        copilot_features_row.add_suffix(copilot_switch)
        copilot_group.add(copilot_features_row)
        
        box.append(copilot_group)
        
        return box


class ThakranSettings(Adw.Application):
    """The Thakran OS Settings application."""
    
    PANELS = [
        DisplayPanel(),
        AIPanel(),
        SettingsPanel("Sound", "audio-volume-high-symbolic", "Output, input, and volume"),
        SettingsPanel("Network", "network-wireless-symbolic", "WiFi, Bluetooth, and VPN"),
        SettingsPanel("Power", "battery-full-symbolic", "Battery, profiles, and sleep"),
        SettingsPanel("Security & Privacy", "security-high-symbolic", "Firewall, permissions"),
        SettingsPanel("Apps & Updates", "system-software-install-symbolic", "Installed apps, updates"),
        SettingsPanel("Keyboard & Input", "input-keyboard-symbolic", "Shortcuts, layouts"),
        SettingsPanel("Users & Accounts", "system-users-symbolic", "Users, login options"),
        SettingsPanel("About", "help-about-symbolic", "System info, hardware"),
    ]
    
    def __init__(self):
        super().__init__(application_id=APP_ID)
        self.connect("activate", self._on_activate)
    
    def _on_activate(self, app):
        window = Adw.ApplicationWindow(application=app)
        window.set_title("Settings")
        window.set_default_size(900, 640)
        
        # Navigation split view
        split = Adw.NavigationSplitView()
        
        # Sidebar
        sidebar_page = Adw.NavigationPage(title="Settings")
        sidebar_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        
        # Search
        search = Gtk.SearchEntry()
        search.set_placeholder_text("Search settings...")
        search.set_margin_top(8)
        search.set_margin_bottom(8)
        search.set_margin_start(8)
        search.set_margin_end(8)
        sidebar_box.append(search)
        
        # Panel list
        listbox = Gtk.ListBox()
        listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        listbox.add_css_class("navigation-sidebar")
        
        for panel in self.PANELS:
            row = Adw.ActionRow(title=panel.title, subtitle=panel.description)
            row.add_prefix(Gtk.Image.new_from_icon_name(panel.icon))
            row.set_activatable(True)
            row.panel = panel
            listbox.append(row)
        
        sidebar_box.append(listbox)
        sidebar_page.set_child(sidebar_box)
        split.set_sidebar(sidebar_page)
        
        # Content area
        self.content_page = Adw.NavigationPage(title="Display & Appearance")
        content_scroll = Gtk.ScrolledWindow()
        self.content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        
        # Show first panel by default
        self.content_box.append(self.PANELS[0].build())
        content_scroll.set_child(self.content_box)
        self.content_page.set_child(content_scroll)
        split.set_content(self.content_page)
        
        # Handle panel selection
        def on_row_selected(listbox, row):
            if row and hasattr(row, 'panel'):
                # Clear content
                while True:
                    child = self.content_box.get_first_child()
                    if child is None:
                        break
                    self.content_box.remove(child)
                
                self.content_box.append(row.panel.build())
                self.content_page.set_title(row.panel.title)
                split.set_show_content(True)
        
        listbox.connect("row-activated", on_row_selected)
        
        window.set_content(split)
        window.present()


def main():
    app = ThakranSettings()
    app.run()


if __name__ == "__main__":
    main()
