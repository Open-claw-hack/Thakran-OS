#!/usr/bin/env python3
"""
============================================================================
Thakran OS — Universal App Store (thakran-store)
============================================================================
A graphical software center showcasing Native Linux Apps, Windows Games
(via Proton), Android APKs (via Waydroid), and macOS Apps (via Darling).
============================================================================
"""

import sys
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, GLib

FEATURED_APPS = [
    {
        "name": "Mozilla Firefox",
        "desc": "Native Linux • Fast, private web browser",
        "icon": "firefox-symbolic",
        "platform": "Native",
        "size": "210 MB"
    },
    {
        "name": "WhatsApp",
        "desc": "Android App • Secure messaging",
        "icon": "call-start-symbolic",
        "platform": "Android",
        "size": "56 MB"
    },
    {
        "name": "Steam",
        "desc": "Windows Compatible • Gaming Platform",
        "icon": "input-gaming-symbolic",
        "platform": "Proton",
        "size": "300 MB"
    },
    {
        "name": "Final Cut Pro (Experimental)",
        "desc": "macOS App • Professional Video Editor",
        "icon": "video-display-symbolic",
        "platform": "Darling",
        "size": "3.2 GB"
    },
    {
        "name": "VS Code",
        "desc": "Native Linux • Code Editor",
        "icon": "text-editor-symbolic",
        "platform": "Native",
        "size": "150 MB"
    },
    {
        "name": "Thakran Llama 3 (8B) Ultra",
        "desc": "AI Model • GGUF Intelligence Engine",
        "icon": "brain-symbolic",
        "platform": "AI Daemon",
        "size": "4.2 GB"
    }
]

class AppStore(Adw.Application):
    def __init__(self):
        super().__init__(application_id='com.thakran.AppStore',
                         flags=Gio.ApplicationFlags.FLAGS_NONE)

    def do_activate(self):
        self.window = Adw.ApplicationWindow(application=self)
        self.window.set_title("Thakran Universal Store")
        self.window.set_default_size(1000, 700)
        self.window.add_css_class("glass-window")

        # Layout
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.window.set_content(self.main_box)

        # Header Bar
        self.header = Adw.HeaderBar()
        self.main_box.append(self.header)

        # View Switcher
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        
        self.switcher = Adw.ViewSwitcher()
        self.switcher.set_stack(self.stack)
        self.header.set_title_widget(self.switcher)
        
        # Search Toggle
        search_btn = Gtk.ToggleButton(icon_name="system-search-symbolic")
        self.header.pack_start(search_btn)

        # --- Discover Page ---
        self.discover_page = self._build_discover_page()
        self.stack.add_titled(self.discover_page, "discover", "Discover")

        # --- Updates Page ---
        self.updates_page = self._build_updates_page()
        self.stack.add_titled(self.updates_page, "updates", "Updates")

        # --- Installed Page ---
        self.installed_page = self._build_installed_page()
        self.stack.add_titled(self.installed_page, "installed", "Installed")

        self.main_box.append(self.stack)
        self.stack.set_vexpand(True)

        self.window.present()

    def _build_discover_page(self):
        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        box.set_margin_top(24)
        box.set_margin_bottom(24)
        box.set_margin_start(36)
        box.set_margin_end(36)
        
        # Featured Banner
        banner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        banner.add_css_class("card")
        banner.set_size_request(-1, 200)
        banner.set_valign(Gtk.Align.CENTER)
        
        lbl_banner = Gtk.Label(label="Any App. Any Platform.")
        lbl_banner.add_css_class("title-1")
        lbl_banner.set_margin_top(48)
        lbl_sub = Gtk.Label(label="Thakran OS runs Native, Windows, Android, and macOS applications seamlessly.")
        lbl_sub.set_margin_bottom(48)
        banner.append(lbl_banner)
        banner.append(lbl_sub)
        box.append(banner)
        
        # App Grid
        grid_lbl = Gtk.Label(label="Recommended for You")
        grid_lbl.set_halign(Gtk.Align.START)
        grid_lbl.add_css_class("title-2")
        box.append(grid_lbl)
        
        flowbox = Gtk.FlowBox()
        flowbox.set_max_children_per_line(3)
        flowbox.set_min_children_per_line(1)
        flowbox.set_selection_mode(Gtk.SelectionMode.NONE)
        flowbox.set_column_spacing(16)
        flowbox.set_row_spacing(16)
        
        for app in FEATURED_APPS:
            card = self._create_app_card(app)
            flowbox.append(card)
            
        box.append(flowbox)
        sw.set_child(box)
        return sw

    def _create_app_card(self, app_data):
        card = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        card.add_css_class("card")
        card.set_margin_top(8)
        card.set_margin_bottom(8)
        card.set_margin_start(8)
        card.set_margin_end(8)
        
        # Icon
        icon = Gtk.Image.new_from_icon_name("application-x-executable-symbolic" if not app_data.get("icon") else app_data["icon"])
        icon.set_pixel_size(64)
        icon.set_margin_start(16)
        card.append(icon)
        
        # Text
        text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        text_box.set_valign(Gtk.Align.CENTER)
        text_box.set_hexpand(True)
        
        title = Gtk.Label(label=app_data["name"])
        title.set_halign(Gtk.Align.START)
        title.add_css_class("title-4")
        
        desc = Gtk.Label(label=app_data["desc"])
        desc.set_halign(Gtk.Align.START)
        desc.set_ellipsize(Pango.EllipsizeMode.END)
        desc.add_css_class("dim-label")
        
        text_box.append(title)
        text_box.append(desc)
        card.append(text_box)
        
        # Install Button
        btn_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        btn_box.set_valign(Gtk.Align.CENTER)
        btn_box.set_margin_end(16)
        
        btn = Gtk.Button(label="Install")
        btn.add_css_class("suggested-action")
        btn.app_data = app_data
        btn.connect("clicked", self.on_install_clicked)
        
        size = Gtk.Label(label=app_data["size"])
        size.add_css_class("caption")
        size.set_margin_top(4)
        
        btn_box.append(btn)
        btn_box.append(size)
        card.append(btn_box)
        
        return card
        
    def _build_updates_page(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.set_valign(Gtk.Align.CENTER)
        box.set_halign(Gtk.Align.CENTER)
        
        icon = Gtk.Image.new_from_icon_name("software-update-available-symbolic")
        icon.set_pixel_size(128)
        icon.add_css_class("dim-label")
        icon.set_margin_bottom(16)
        
        lbl = Gtk.Label(label="System is Up to Date")
        lbl.add_css_class("title-2")
        
        # Hidden progress bar for fake updates
        self.update_spinner = Gtk.Spinner()
        
        btn = Gtk.Button(label="Check for Updates")
        btn.set_margin_top(24)
        btn.set_halign(Gtk.Align.CENTER)
        btn.connect("clicked", lambda x: self.update_spinner.start())
        
        box.append(icon)
        box.append(lbl)
        box.append(self.update_spinner)
        box.append(btn)
        return box

    def _build_installed_page(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.set_valign(Gtk.Align.CENTER)
        box.set_halign(Gtk.Align.CENTER)
        lbl = Gtk.Label(label="No 3rd Party Apps Installed Yet")
        lbl.add_css_class("title-2")
        box.append(lbl)
        return box

    def on_install_clicked(self, btn):
        btn.set_label("Installing...")
        btn.set_sensitive(False)
        app = btn.app_data
        
        def reset_btn():
            btn.set_label("Open")
            btn.remove_css_class("suggested-action")
            btn.set_sensitive(True)
            self._trigger_os_installer(app)
            return False
            
        GLib.timeout_add(2000, reset_btn)

    def _trigger_os_installer(self, app):
        """Mock invocation of the actual background pacman/flatpak/waydroid installer"""
        print(f"Submitting {app['name']} to installation queue using wrapper {app['platform']}")

if __name__ == '__main__':
    gi.require_version('Pango', '1.0')
    from gi.repository import Pango
    app = AppStore()
    app.run(sys.argv)
