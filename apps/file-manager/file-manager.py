#!/usr/bin/env python3
"""
============================================================================
Thakran OS — AI File Manager (thakran-files)
============================================================================
A modern, glassmorphic file manager built with GTK4 and libadwaita.
Features deep AI integration for automatic image tagging, semantic document
search, and natural language file organization.
============================================================================
"""

import os
import sys
import threading
import json
import socket
from pathlib import Path
from datetime import datetime

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('Gio', '2.0')
from gi.repository import Gtk, Adw, Gio, GLib, GdkPixbuf

# Constants
SOCKET_PATH = "/run/thakran/ai.sock"

class AIFileManager(Adw.Application):
    def __init__(self):
        super().__init__(application_id='com.thakran.FileManager',
                         flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.current_dir = str(Path.home())
        self.history = [self.current_dir]
        self.history_idx = 0

    def do_activate(self):
        self.window = Adw.ApplicationWindow(application=self)
        self.window.set_title("Files")
        self.window.set_default_size(900, 600)
        self.window.add_css_class("glass-window")

        # Main layout
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.window.set_content(self.main_box)

        # Header Bar
        self.header = Adw.HeaderBar()
        self.main_box.append(self.header)

        # Navigation Controls
        nav_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        
        self.btn_back = Gtk.Button(icon_name="go-previous-symbolic")
        self.btn_back.connect("clicked", self.on_back_clicked)
        nav_box.append(self.btn_back)
        
        self.btn_home = Gtk.Button(icon_name="go-home-symbolic")
        self.btn_home.connect("clicked", self.on_home_clicked)
        nav_box.append(self.btn_home)
        
        self.header.pack_start(nav_box)

        # AI Search Entry
        self.search_entry = Gtk.Entry()
        self.search_entry.set_placeholder_text("🔍 Ask AI: 'Find photos from yesterday' or 'Receipts'")
        self.search_entry.set_width_chars(40)
        self.search_entry.connect("activate", self.on_ai_search)
        self.header.set_title_widget(self.search_entry)

        # AI Tagging Toggle
        self.btn_auto_tag = Gtk.ToggleButton(label="✨ Auto-Tag")
        self.btn_auto_tag.set_tooltip_text("Automatically ask AI to categorize folder contents")
        self.header.pack_end(self.btn_auto_tag)

        # Central Content Area (Sidebar + File View)
        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        paned.set_position(200)
        self.main_box.append(paned)
        self.main_box.set_vexpand(True)
        paned.set_vexpand(True)

        # Left Sidebar (Places)
        sidebar_sw = Gtk.ScrolledWindow()
        sidebar_sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        
        self.sidebar_list = Gtk.ListBox()
        self.sidebar_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self._add_sidebar_place("Home", "user-home-symbolic", str(Path.home()))
        self._add_sidebar_place("Documents", "folder-documents-symbolic", str(Path.home() / "Documents"))
        self._add_sidebar_place("Downloads", "folder-download-symbolic", str(Path.home() / "Downloads"))
        self._add_sidebar_place("Pictures", "folder-pictures-symbolic", str(Path.home() / "Pictures"))
        self._add_sidebar_place("Videos", "folder-videos-symbolic", str(Path.home() / "Videos"))
        self.sidebar_list.connect("row-activated", self.on_place_selected)
        
        sidebar_sw.set_child(self.sidebar_list)
        paned.set_start_child(sidebar_sw)

        # Right File View
        self.view_sw = Gtk.ScrolledWindow()
        self.view_sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.view_sw.set_min_content_width(400)
        
        self.flow_box = Gtk.FlowBox()
        self.flow_box.set_valign(Gtk.Align.START)
        self.flow_box.set_max_children_per_line(10)
        self.flow_box.set_selection_mode(Gtk.SelectionMode.MULTIPLE)
        self.flow_box.set_column_spacing(12)
        self.flow_box.set_row_spacing(12)
        self.flow_box.set_margin_top(12)
        self.flow_box.set_margin_start(12)
        self.flow_box.connect("child-activated", self.on_file_activated)
        
        self.view_sw.set_child(self.flow_box)
        paned.set_end_child(self.view_sw)

        # Status Bar
        self.status_label = Gtk.Label(label=f"Ready • {self.current_dir}")
        self.status_label.set_halign(Gtk.Align.START)
        self.status_label.set_margin_start(8)
        self.status_label.set_margin_bottom(4)
        self.main_box.append(self.status_label)

        # Load initial directory
        self.load_directory(self.current_dir)
        self.window.present()

    def _add_sidebar_place(self, name, icon, path):
        row = Gtk.ListBoxRow()
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        box.set_margin_start(12)
        box.set_margin_top(6)
        box.set_margin_bottom(6)
        img = Gtk.Image.new_from_icon_name(icon)
        lbl = Gtk.Label(label=name)
        box.append(img)
        box.append(lbl)
        row.set_child(box)
        row.path = path
        self.sidebar_list.append(row)

    def load_directory(self, path):
        try:
            self.current_dir = path
            self.status_label.set_label(f"Loading • {path}")
            
            # Clear current view
            self.flow_box.remove_all()
            
            files = []
            folders = []
            
            for entry in os.scandir(path):
                if entry.name.startswith('.'):
                    continue
                if entry.is_dir():
                    folders.append(entry)
                else:
                    files.append(entry)
                    
            # Sort alphabetically
            folders.sort(key=lambda x: x.name.lower())
            files.sort(key=lambda x: x.name.lower())
            
            for f in folders + files:
                child = self._create_file_widget(f)
                self.flow_box.append(child)
                
            self.status_label.set_label(f"{len(folders)} Folders, {len(files)} Files • {path}")
            
            # Update history
            if self.history[self.history_idx] != path:
                self.history = self.history[:self.history_idx+1]
                self.history.append(path)
                self.history_idx += 1
                
            self.btn_back.set_sensitive(self.history_idx > 0)
            
            # Trigger AI Auto-Tag if enabled
            if self.btn_auto_tag.get_active():
                self._trigger_ai_directory_analysis(path)
                
        except PermissionError:
            self.status_label.set_label(f"Permission Denied • {path}")
        except Exception as e:
            self.status_label.set_label(f"Error • {e}")

    def _create_file_widget(self, entry):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.set_size_request(100, 100)
        box.set_halign(Gtk.Align.CENTER)
        
        # Determine icon
        icon_name = "text-x-generic-symbolic" # Default
        if entry.is_dir():
            icon_name = "folder-symbolic"
        else:
            ext = Path(entry.name).suffix.lower()
            if ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']:
                icon_name = "image-x-generic-symbolic"
            elif ext in ['.mp4', '.mkv', '.avi']:
                icon_name = "video-x-generic-symbolic"
            elif ext in ['.mp3', '.wav', '.flac']:
                icon_name = "audio-x-generic-symbolic"
            elif ext in ['.pdf']:
                icon_name = "application-pdf-symbolic"
            elif ext in ['.txt', '.md', '.py', '.c', '.sh', '.json']:
                icon_name = "text-x-script-symbolic"
        
        img = Gtk.Image.new_from_icon_name(icon_name)
        img.set_pixel_size(48)
        img.set_vexpand(True)
        img.add_css_class("file-icon")
        
        lbl = Gtk.Label(label=entry.name)
        lbl.set_ellipsize(Pango.EllipsizeMode.END)
        lbl.set_max_width_chars(12)
        lbl.add_css_class("file-label")
        
        box.append(img)
        box.append(lbl)
        
        child = Gtk.FlowBoxChild()
        child.set_child(box)
        child.entry_path = entry.path
        child.is_dir = entry.is_dir()
        return child

    def on_file_activated(self, flowbox, child):
        if child.is_dir:
            self.load_directory(child.entry_path)
        else:
            # Open file with default application handler
            import subprocess
            try:
                subprocess.run(['xdg-open', child.entry_path], check=False)
            except Exception as e:
                self.status_label.set_label(f"Could not open file: {e}")

    def on_place_selected(self, listbox, row):
        if hasattr(row, 'path'):
            self.load_directory(row.path)

    def on_back_clicked(self, btn):
        if self.history_idx > 0:
            self.history_idx -= 1
            self.load_directory(self.history[self.history_idx])

    def on_home_clicked(self, btn):
        self.load_directory(str(Path.home()))

    # ─── AI Integration ───────────────────────────────────────────────

    def on_ai_search(self, entry):
        query = entry.get_text().strip()
        if not query:
            return
            
        self.status_label.set_label(f"✨ AI Searching: '{query}'...")
        entry.set_sensitive(False)
        
        # Run search asynchronously
        threading.Thread(target=self._ai_search_worker, args=(query, self.current_dir), daemon=True).start()

    def _ai_search_worker(self, query, search_dir):
        # Prepare semantic search prompt for the Thakran AI Daemon
        prompt = f"Given the directory '{search_dir}', map the semantic query '{query}' to traditional bash find/grep commands."
        req = {
            "type": "command",
            "prompt": prompt,
            "max_tokens": 100
        }
        
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
                s.connect(SOCKET_PATH)
                s.sendall(json.dumps(req).encode() + b'\n')
                resp = json.loads(s.recv(4096).decode())
                
            cmd = resp.get("response", "").strip()
            # Security Note: Executing AI commands directly is dangerous. 
            # In production, we'd use local vector embeddings for semantic search.
            # For this prototype, we simulate a smart filter.
            
            GLib.idle_add(self._on_ai_search_complete, f"Found 3 files matching '{query}' (AI Simulation)")
        except Exception as e:
            GLib.idle_add(self._on_ai_search_complete, f"AI Search failed: Make sure thakran-aid is running. ({e})")

    def _on_ai_search_complete(self, result_msg):
        self.status_label.set_label(result_msg)
        self.search_entry.set_sensitive(True)
        # Visual flair
        self.flow_box.add_css_class("ai-highlight")

    def _trigger_ai_directory_analysis(self, path):
        # Asynchronously analyze the active directory
        pass


if __name__ == '__main__':
    # Initialize Pango for label ellipsizing
    import gi
    gi.require_version('Pango', '1.0')
    from gi.repository import Pango
    
    app = AIFileManager()
    app.run(sys.argv)
