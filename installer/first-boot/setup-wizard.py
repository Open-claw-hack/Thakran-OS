#!/usr/bin/env python3
"""
============================================================================
Thakran OS — First Boot Setup Wizard (thakran-wizard)
============================================================================
A GTK4 wizard that runs once after the user installs Thakran OS to their
hard drive and boots it for the first time. It profiles their hardware
and lets them choose their Local AI Engine tier (Nano to Ultra).
============================================================================
"""

import sys
import os
import json
import subprocess
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, GLib, Gdk

class SetupWizard(Adw.Application):
    def __init__(self):
        super().__init__(application_id='com.thakran.SetupWizard',
                         flags=Gio.ApplicationFlags.FLAGS_NONE)

    def do_activate(self):
        self.window = Adw.ApplicationWindow(application=self)
        self.window.set_title("Welcome to Thakran OS")
        self.window.set_default_size(800, 600)
        self.window.add_css_class("glass-window")
        
        # Disable window controls to enforce wizard completion
        self.header = Adw.HeaderBar()
        self.header.set_show_end_title_buttons(False)
        self.header.set_show_start_title_buttons(False)

        # Carousel for wizard steps
        self.carousel = Adw.Carousel()
        self.carousel.set_interactive(False) # Disable manual swipe
        
        self.carousel.append(self._build_welcome_page())
        self.carousel.append(self._build_hardware_page())
        self.carousel.append(self._build_copilot_page())
        self.carousel.append(self._build_subscription_page())
        self.carousel.append(self._build_finish_page())

        # Main Layout
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.window.set_content(self.main_box)
        self.main_box.append(self.header)
        self.main_box.append(self.carousel)
        self.carousel.set_vexpand(True)
        
        # Navigation Bar
        self.nav_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.nav_box.set_margin_top(16)
        self.nav_box.set_margin_bottom(16)
        self.nav_box.set_margin_start(24)
        self.nav_box.set_margin_end(24)
        
        self.btn_next = Gtk.Button(label="Continue")
        self.btn_next.add_css_class("suggested-action")
        self.btn_next.connect("clicked", self.on_next)
        self.btn_next.set_hexpand(True)
        self.btn_next.set_halign(Gtk.Align.END)
        self.nav_box.append(self.btn_next)
        
        self.main_box.append(Gtk.Separator())
        self.main_box.append(self.nav_box)

        self.window.present()

    def _build_welcome_page(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        box.set_valign(Gtk.Align.CENTER)
        box.set_halign(Gtk.Align.CENTER)
        
        logo = Gtk.Image.new_from_icon_name("computer-symbolic") # Placeholder
        logo.set_pixel_size(128)
        logo.add_css_class("accent")
        box.append(logo)
        
        lbl = Gtk.Label(label="Welcome to Thakran OS")
        lbl.add_css_class("title-1")
        box.append(lbl)
        
        sub = Gtk.Label(label="Your intelligent, private, and universal workspace is ready.")
        sub.add_css_class("dim-label")
        box.append(sub)
        
        return box

    def _build_hardware_page(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        box.set_valign(Gtk.Align.CENTER)
        box.set_halign(Gtk.Align.CENTER)
        
        lbl = Gtk.Label(label="Configuring Local AI")
        lbl.add_css_class("title-2")
        box.append(lbl)
        
        # Mock detection
        ram_gb = 16 
        gpu = "Unknown GPU"
        try:
            with open("/proc/meminfo") as f:
                kb = int(f.readline().split()[1])
                ram_gb = round(kb / (1024 * 1024))
            out = subprocess.check_output("lspci | grep -i vga", shell=True).decode()
            gpu = out.split(":")[2].strip()
        except:
            pass

        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        info_box.add_css_class("card")
        info_box.set_padding(16, 16, 16, 16)
        info_box.append(Gtk.Label(label=f"Hardware Detected: {ram_gb}GB RAM • {gpu}"))
        
        tier = "Lite (3B)"
        if ram_gb >= 16: tier = "Standard (8B)"
        if ram_gb >= 32: tier = "Ultra (34B)"
        if ram_gb <= 4: tier = "Nano (1B)"
        
        rec_lbl = Gtk.Label(label=f"Recommended AI Tier: {tier}")
        rec_lbl.add_css_class("accent")
        info_box.append(rec_lbl)
        box.append(info_box)
        
        # Download progress
        self.dl_bar = Gtk.ProgressBar()
        self.dl_bar.set_fraction(0.0)
        box.append(self.dl_bar)
        
        dl_lbl = Gtk.Label(label="We will download your AI model parameters in the background.")
        dl_lbl.add_css_class("dim-label")
        box.append(dl_lbl)
        
        return box

    def _build_copilot_page(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        box.set_valign(Gtk.Align.CENTER)
        box.set_halign(Gtk.Align.CENTER)
        
        lbl = Gtk.Label(label="Connect GitHub Copilot")
        lbl.add_css_class("title-2")
        box.append(lbl)
        
        icon = Gtk.Image.new_from_icon_name("system-software-install-symbolic")
        icon.set_pixel_size(64)
        box.append(icon)
        
        sub = Gtk.Label(label="Thakran OS natively integrates with GitHub Copilot.\nBy signing in, you can use your existing Copilot subscription as your system-wide AI engine.")
        sub.set_wrap(True)
        sub.set_max_width_chars(60)
        sub.set_justify(Gtk.Justification.CENTER)
        box.append(sub)

        auth_btn = Gtk.Button(label="Sign In with GitHub (Device Flow)")
        auth_btn.add_css_class("suggested-action")
        auth_btn.set_size_request(240, 48)
        box.append(auth_btn)

        skip_btn = Gtk.Button(label="Skip (Use Local AI)")
        skip_btn.add_css_class("flat")
        box.append(skip_btn)
        
        return box

    def _build_subscription_page(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        box.set_valign(Gtk.Align.CENTER)
        box.set_halign(Gtk.Align.CENTER)
        
        lbl = Gtk.Label(label="Thakran Cloud AI Gateway")
        lbl.add_css_class("title-2")
        box.append(lbl)
        
        sub = Gtk.Label(label="Enhance your local AI with seamless cloud fallback to OpenAI, Anthropic, and Google architectures directly integrated into your OS UI.")
        sub.set_wrap(True)
        sub.set_max_width_chars(60)
        sub.set_justify(Gtk.Justification.CENTER)
        box.append(sub)
        
        plans = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        
        free = self._plan_card("Basic (Local Only)", "Free", "No cloud dependencies. Private offline AI.")
        pro = self._plan_card("Pro", "$9.99/mo", "Access GPT-4o, Claude 3 directly in desktop widgets.")
        team = self._plan_card("Team", "$24.99/mo", "Shared context APIs and priority remote GPUs.")
        
        plans.append(free)
        plans.append(pro)
        plans.append(team)
        
        box.append(plans)
        
        btn_skip = Gtk.Button(label="Set up later in Settings")
        btn_skip.add_css_class("flat")
        box.append(btn_skip)
        
        return box

    def _plan_card(self, title, price, feature):
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        card.add_css_class("card")
        card.set_margin_top(8)
        card.set_margin_bottom(8)
        card.set_margin_start(8)
        card.set_margin_end(8)
        
        t = Gtk.Label(label=title)
        t.add_css_class("title-4")
        card.append(t)
        
        p = Gtk.Label(label=price)
        p.add_css_class("title-2")
        p.add_css_class("accent")
        card.append(p)
        
        f = Gtk.Label(label=feature)
        f.set_wrap(True)
        f.set_max_width_chars(20)
        card.append(f)
        
        btn = Gtk.Button(label="Select")
        card.append(btn)
        return card

    def _build_finish_page(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        box.set_valign(Gtk.Align.CENTER)
        box.set_halign(Gtk.Align.CENTER)
        
        icon = Gtk.Image.new_from_icon_name("emblem-ok-symbolic")
        icon.set_pixel_size(128)
        icon.add_css_class("success")
        box.append(icon)
        
        lbl = Gtk.Label(label="You're all set!")
        lbl.add_css_class("title-1")
        box.append(lbl)
        
        return box

    def on_next(self, btn):
        pages = self.carousel.get_n_pages()
        current = int(self.carousel.get_position())
        
        if current < pages - 1:
            self.carousel.scroll_to(self.carousel.get_nth_page(current + 1), True)
            if current + 1 == pages - 1:
                self.btn_next.set_label("Start Using Thakran OS")
        else:
            # Mark wizard as complete
            os.makedirs(os.path.expanduser("~/.config/thakran"), exist_ok=True)
            with open(os.path.expanduser("~/.config/thakran/wizard_done"), "w") as f:
                f.write("1")
                
            # Launch desktop and quit wizard
            subprocess.Popen(["systemctl", "--user", "start", "thakran-desktop"])
            self.quit()

if __name__ == '__main__':
    # Add styling for custom padding/cards
    css = b"""
    .card {
        background: rgba(255,255,255,0.05);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 12px;
        padding: 24px;
    }
    """
    provider = Gtk.CssProvider()
    provider.load_from_data(css)
    Gtk.StyleContext.add_provider_for_display(
        Gio.Application.get_default().get_display() if Gio.Application.get_default() else Gdk.Display.get_default(),
        provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )
    
    app = SetupWizard()
    app.run(sys.argv)
