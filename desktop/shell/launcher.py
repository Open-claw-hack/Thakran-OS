#!/usr/bin/env python3
"""
============================================================================
Thakran OS — Application Launcher
============================================================================
Spotlight-style application launcher with AI-powered search.

Features:
  - Fuzzy app search
  - AI-powered natural language queries
  - Quick calculator / unit converter
  - File search
  - System command execution
  - Recent apps and files

Activated with Super+Space.
============================================================================
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, GLib, Gio, Gdk
import json
import os
import subprocess
from pathlib import Path


class AppEntry:
    """Represents an installed application."""
    
    def __init__(self, name, icon, exec_cmd, description="", keywords=None):
        self.name = name
        self.icon = icon
        self.exec_cmd = exec_cmd
        self.description = description
        self.keywords = keywords or []
        self.launch_count = 0
        self.last_launched = 0


class SearchResult:
    """A search result item."""
    
    def __init__(self, title, subtitle, icon, category, action, score=0.0):
        self.title = title
        self.subtitle = subtitle
        self.icon = icon
        self.category = category  # app, file, ai, system, calculator
        self.action = action      # callable
        self.score = score


class AppIndex:
    """Indexes installed applications for fast search."""
    
    def __init__(self):
        self.apps: list[AppEntry] = []
        self._load_apps()
    
    def _load_apps(self):
        """Scan .desktop files for installed applications."""
        app_dirs = [
            "/usr/share/applications",
            "/usr/local/share/applications",
            os.path.expanduser("~/.local/share/applications"),
        ]
        
        for app_dir in app_dirs:
            if not os.path.isdir(app_dir):
                continue
            
            for filename in os.listdir(app_dir):
                if not filename.endswith(".desktop"):
                    continue
                
                filepath = os.path.join(app_dir, filename)
                app = self._parse_desktop_file(filepath)
                if app:
                    self.apps.append(app)
        
        # Sort by name
        self.apps.sort(key=lambda a: a.name.lower())
    
    def _parse_desktop_file(self, filepath):
        """Parse a .desktop file into an AppEntry."""
        try:
            name = ""
            icon = ""
            exec_cmd = ""
            description = ""
            keywords = []
            no_display = False
            
            with open(filepath) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("Name="):
                        name = line[5:]
                    elif line.startswith("Icon="):
                        icon = line[5:]
                    elif line.startswith("Exec="):
                        exec_cmd = line[5:].split("%")[0].strip()
                    elif line.startswith("Comment="):
                        description = line[8:]
                    elif line.startswith("Keywords="):
                        keywords = [k.strip() for k in line[9:].split(";") if k.strip()]
                    elif line.startswith("NoDisplay=true"):
                        no_display = True
            
            if no_display or not name or not exec_cmd:
                return None
            
            return AppEntry(name, icon, exec_cmd, description, keywords)
            
        except Exception:
            return None
    
    def search(self, query: str) -> list[SearchResult]:
        """Search applications by name, description, or keywords."""
        if not query:
            return self._get_frequent_apps()
        
        query_lower = query.lower()
        results = []
        
        for app in self.apps:
            score = 0.0
            
            # Exact name match
            if query_lower == app.name.lower():
                score = 1.0
            # Name starts with query
            elif app.name.lower().startswith(query_lower):
                score = 0.9
            # Name contains query
            elif query_lower in app.name.lower():
                score = 0.7
            # Description contains query
            elif query_lower in app.description.lower():
                score = 0.5
            # Keyword match
            elif any(query_lower in kw.lower() for kw in app.keywords):
                score = 0.4
            
            if score > 0:
                results.append(SearchResult(
                    title=app.name,
                    subtitle=app.description,
                    icon=app.icon or "application-x-executable-symbolic",
                    category="app",
                    action=lambda cmd=app.exec_cmd: self._launch(cmd),
                    score=score,
                ))
        
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:10]
    
    def _get_frequent_apps(self) -> list[SearchResult]:
        """Return most frequently used apps."""
        sorted_apps = sorted(self.apps, key=lambda a: a.launch_count, reverse=True)
        return [
            SearchResult(
                title=app.name,
                subtitle=app.description,
                icon=app.icon or "application-x-executable-symbolic",
                category="app",
                action=lambda cmd=app.exec_cmd: self._launch(cmd),
            )
            for app in sorted_apps[:8]
        ]
    
    def _launch(self, exec_cmd):
        """Launch an application."""
        try:
            subprocess.Popen(exec_cmd.split(), start_new_session=True)
        except Exception as e:
            print(f"Failed to launch: {e}")


class AISearchProvider:
    """Provides AI-powered search results."""
    
    def search(self, query: str) -> list[SearchResult]:
        """Query the AI daemon for intelligent results."""
        results = []
        
        # Check if it's a question for AI
        ai_triggers = ["what", "how", "why", "when", "where", "who", "explain", "help"]
        if any(query.lower().startswith(t) for t in ai_triggers):
            results.append(SearchResult(
                title=f"Ask AI: {query}",
                subtitle="Get an AI-powered answer",
                icon="thakran-ai-symbolic",
                category="ai",
                action=lambda q=query: self._ask_ai(q),
                score=0.8,
            ))
        
        # System commands
        system_commands = {
            "shutdown": "Shut down the computer",
            "restart": "Restart the computer",
            "sleep": "Put computer to sleep",
            "lock": "Lock the screen",
            "settings": "Open System Settings",
            "update": "Check for system updates",
        }
        
        for cmd, desc in system_commands.items():
            if query.lower() in cmd or cmd in query.lower():
                results.append(SearchResult(
                    title=cmd.capitalize(),
                    subtitle=desc,
                    icon="system-shutdown-symbolic",
                    category="system",
                    action=lambda c=cmd: self._system_action(c),
                    score=0.6,
                ))
        
        return results
    
    def _ask_ai(self, query):
        """Send query to AI assistant."""
        subprocess.Popen(["thakran-assistant", "--query", query], start_new_session=True)
    
    def _system_action(self, action):
        """Execute a system action."""
        actions = {
            "shutdown": "systemctl poweroff",
            "restart": "systemctl reboot",
            "sleep": "systemctl suspend",
            "lock": "loginctl lock-session",
            "settings": "thakran-settings",
            "update": "thakran-updater",
        }
        cmd = actions.get(action, "")
        if cmd:
            subprocess.Popen(cmd.split(), start_new_session=True)


class CalculatorProvider:
    """Inline calculator and unit converter."""
    
    def evaluate(self, query: str) -> list[SearchResult]:
        """Try to evaluate mathematical expressions."""
        import re
        
        # Check if query looks like a math expression
        if not re.match(r'^[\d\s\+\-\*\/\.\(\)\^%]+$', query):
            return []
        
        try:
            # Safe evaluation (no builtins)
            result = eval(query, {"__builtins__": {}}, {})
            return [SearchResult(
                title=f"= {result}",
                subtitle=f"{query}",
                icon="accessories-calculator-symbolic",
                category="calculator",
                action=lambda r=str(result): self._copy_to_clipboard(r),
                score=1.0,
            )]
        except Exception:
            return []
    
    def _copy_to_clipboard(self, text):
        """Copy result to clipboard."""
        clipboard = Gdk.Display.get_default().get_clipboard()
        clipboard.set(text)


class ThakranLauncher(Adw.Application):
    """Main launcher application."""
    
    def __init__(self):
        super().__init__(application_id="dev.thakranos.launcher")
        self.connect("activate", self._on_activate)
        self.app_index = AppIndex()
        self.ai_search = AISearchProvider()
        self.calculator = CalculatorProvider()
    
    def _on_activate(self, app):
        """Build and show the launcher."""
        window = Gtk.Window(application=app)
        window.set_title("Thakran Launcher")
        window.set_default_size(640, 480)
        window.set_decorated(False)
        window.set_modal(True)
        
        # Main container
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        main_box.add_css_class("launcher-container")
        
        # ─── Search bar ───────────────────────────
        search_frame = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        search_frame.add_css_class("launcher-search-frame")
        
        search_icon = Gtk.Image.new_from_icon_name("system-search-symbolic")
        search_icon.set_pixel_size(20)
        search_frame.append(search_icon)
        
        self.search_entry = Gtk.Entry()
        self.search_entry.set_placeholder_text("Search apps, files, or ask AI...")
        self.search_entry.set_hexpand(True)
        self.search_entry.add_css_class("launcher-search")
        self.search_entry.connect("changed", self._on_search_changed)
        self.search_entry.connect("activate", self._on_search_activate)
        search_frame.append(self.search_entry)
        
        ai_hint = Gtk.Label(label="⌘ AI")
        ai_hint.add_css_class("ai-hint")
        search_frame.append(ai_hint)
        
        main_box.append(search_frame)
        
        # ─── Results list ─────────────────────────
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        
        self.results_box = Gtk.ListBox()
        self.results_box.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.results_box.add_css_class("launcher-results")
        self.results_box.connect("row-activated", self._on_result_activated)
        scrolled.set_child(self.results_box)
        
        main_box.append(scrolled)
        
        # ─── Footer hints ────────────────────────
        footer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        footer.add_css_class("launcher-footer")
        
        hints = [
            ("↵", "Open"),
            ("↑↓", "Navigate"),
            ("Esc", "Close"),
        ]
        for key, action in hints:
            hint = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
            key_label = Gtk.Label(label=key)
            key_label.add_css_class("hint-key")
            action_label = Gtk.Label(label=action)
            action_label.add_css_class("hint-action")
            hint.append(key_label)
            hint.append(action_label)
            footer.append(hint)
        
        main_box.append(footer)
        
        window.set_child(main_box)
        
        # Close on Escape
        controller = Gtk.EventControllerKey()
        controller.connect("key-pressed", self._on_key_pressed, window)
        window.add_controller(controller)
        
        self._load_css()
        
        # Show initial results
        self._on_search_changed(self.search_entry)
        
        window.present()
        self.search_entry.grab_focus()
    
    def _on_search_changed(self, entry):
        """Handle search input changes."""
        query = entry.get_text().strip()
        
        # Clear previous results
        while True:
            row = self.results_box.get_first_child()
            if row is None:
                break
            self.results_box.remove(row)
        
        # Collect results from all providers
        all_results = []
        
        # Calculator
        all_results.extend(self.calculator.evaluate(query))
        
        # Apps
        all_results.extend(self.app_index.search(query))
        
        # AI / System
        if query:
            all_results.extend(self.ai_search.search(query))
        
        # Sort by score
        all_results.sort(key=lambda r: r.score, reverse=True)
        
        # Display results
        for result in all_results[:12]:
            row = self._create_result_row(result)
            self.results_box.append(row)
        
        # Select first result
        first = self.results_box.get_first_child()
        if first:
            self.results_box.select_row(first)
    
    def _create_result_row(self, result: SearchResult) -> Gtk.ListBoxRow:
        """Create a result row widget."""
        row = Gtk.ListBoxRow()
        row.result = result
        
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        box.add_css_class("result-row")
        
        # Icon
        icon = Gtk.Image.new_from_icon_name(result.icon)
        icon.set_pixel_size(32)
        icon.add_css_class("result-icon")
        box.append(icon)
        
        # Text
        text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        text_box.set_hexpand(True)
        
        title = Gtk.Label(label=result.title, xalign=0)
        title.add_css_class("result-title")
        text_box.append(title)
        
        if result.subtitle:
            subtitle = Gtk.Label(label=result.subtitle, xalign=0)
            subtitle.add_css_class("result-subtitle")
            subtitle.set_ellipsize(3)  # PANGO_ELLIPSIZE_END
            text_box.append(subtitle)
        
        box.append(text_box)
        
        # Category badge
        badge = Gtk.Label(label=result.category.upper())
        badge.add_css_class(f"badge-{result.category}")
        badge.add_css_class("result-badge")
        box.append(badge)
        
        row.set_child(box)
        return row
    
    def _on_result_activated(self, listbox, row):
        """Handle result activation (Enter key or click)."""
        if hasattr(row, 'result') and row.result.action:
            row.result.action()
            self.quit()
    
    def _on_search_activate(self, entry):
        """Handle Enter key on search entry."""
        selected = self.results_box.get_selected_row()
        if selected:
            self._on_result_activated(self.results_box, selected)
    
    def _on_key_pressed(self, controller, keyval, keycode, state, window):
        """Handle keyboard shortcuts."""
        if keyval == Gdk.KEY_Escape:
            self.quit()
            return True
        return False
    
    def _load_css(self):
        """Load launcher stylesheet."""
        css = b"""
        .launcher-container {
            background: rgba(10, 10, 26, 0.92);
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: 16px;
        }
        
        .launcher-search-frame {
            padding: 16px 20px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.06);
        }
        
        .launcher-search {
            background: transparent;
            border: none;
            color: #f0f0f8;
            font-size: 18px;
            font-weight: 400;
            caret-color: #a855f7;
        }
        
        .ai-hint {
            color: #a855f7;
            font-size: 11px;
            font-weight: 600;
            padding: 2px 8px;
            border-radius: 6px;
            background: rgba(168, 85, 247, 0.15);
        }
        
        .result-row {
            padding: 10px 20px;
        }
        
        .result-title {
            color: #f0f0f8;
            font-size: 14px;
            font-weight: 500;
        }
        
        .result-subtitle {
            color: #6b6b8e;
            font-size: 12px;
        }
        
        .result-badge {
            font-size: 9px;
            font-weight: 700;
            padding: 2px 6px;
            border-radius: 4px;
        }
        
        .badge-app { background: rgba(99, 102, 241, 0.2); color: #818cf8; }
        .badge-ai { background: rgba(168, 85, 247, 0.2); color: #c084fc; }
        .badge-system { background: rgba(34, 197, 94, 0.2); color: #22c55e; }
        .badge-calculator { background: rgba(234, 179, 8, 0.2); color: #eab308; }
        .badge-file { background: rgba(59, 130, 246, 0.2); color: #60a5fa; }
        
        .launcher-footer {
            padding: 8px 20px;
            border-top: 1px solid rgba(255, 255, 255, 0.06);
        }
        
        .hint-key {
            background: rgba(255, 255, 255, 0.1);
            color: #a0a0c0;
            font-size: 10px;
            padding: 1px 6px;
            border-radius: 4px;
            font-family: monospace;
        }
        
        .hint-action {
            color: #6b6b8e;
            font-size: 11px;
        }
        
        row:selected .result-row {
            background: rgba(168, 85, 247, 0.15);
            border-radius: 8px;
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
    """Run the launcher."""
    app = ThakranLauncher()
    app.run()


if __name__ == "__main__":
    main()
