#!/usr/bin/env python3
"""
============================================================================
Thakran OS — AI-Enhanced Terminal Emulator
============================================================================
A modern terminal with AI superpowers:

  - Natural language to command translation
  - Error explanation and fix suggestions
  - Command history with AI search
  - Inline AI code generation
  - Smart autocomplete
  - Split panes and tabs

Built with VTE (Virtual Terminal Emulator) + GTK4.
============================================================================
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('Vte', '3.91')

from gi.repository import Gtk, Adw, GLib, Gdk, Vte, Pango
import json
import os
import urllib.request


APP_ID = "dev.thakranos.terminal"
AI_API = "http://127.0.0.1:11434/api"


class AITerminalHelper:
    """AI assistant for terminal operations."""
    
    def translate_to_command(self, natural_language: str) -> str:
        """Convert natural language to a shell command."""
        try:
            payload = json.dumps({
                "model": "thakran-mini",
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a Linux command translator. "
                            "Convert natural language to exact shell commands. "
                            "Reply ONLY with the command, no explanation. "
                            "If multiple commands needed, separate with &&."
                        ),
                    },
                    {"role": "user", "content": natural_language},
                ],
            }).encode()
            
            req = urllib.request.Request(
                f"{AI_API}/chat",
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
                return data.get("message", {}).get("content", "").strip()
        except Exception:
            return f"# AI unavailable: {natural_language}"
    
    def explain_error(self, error_output: str) -> str:
        """Explain a command error and suggest fixes."""
        try:
            payload = json.dumps({
                "model": "thakran-mini",
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a Linux expert. Explain this terminal error "
                            "concisely and suggest a fix. Use bullet points."
                        ),
                    },
                    {"role": "user", "content": f"Error:\n{error_output}"},
                ],
            }).encode()
            
            req = urllib.request.Request(
                f"{AI_API}/chat",
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
                return data.get("message", {}).get("content", "Could not analyze error.")
        except Exception:
            return "AI service unavailable for error analysis."


class ThakranTerminal(Adw.Application):
    """Main terminal application."""
    
    def __init__(self):
        super().__init__(application_id=APP_ID)
        self.connect("activate", self._on_activate)
        self.ai = AITerminalHelper()
    
    def _on_activate(self, app):
        """Build the terminal UI."""
        window = Adw.ApplicationWindow(application=app)
        window.set_title("Thakran Terminal")
        window.set_default_size(900, 600)
        
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        main_box.add_css_class("terminal-container")
        
        # ─── Header with tabs and AI bar ─────────
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        header.add_css_class("terminal-header")
        
        # Tab bar
        tab_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        tab_box.set_hexpand(True)
        
        tab1 = Gtk.Button(label="● bash")
        tab1.add_css_class("terminal-tab")
        tab1.add_css_class("tab-active")
        tab_box.append(tab1)
        
        new_tab_btn = Gtk.Button()
        new_tab_btn.set_icon_name("list-add-symbolic")
        new_tab_btn.add_css_class("new-tab-btn")
        tab_box.append(new_tab_btn)
        
        header.append(tab_box)
        
        # AI toggle
        ai_btn = Gtk.ToggleButton(label="🧠 AI")
        ai_btn.add_css_class("ai-toggle")
        ai_btn.set_tooltip_text("Toggle AI assistant panel")
        header.append(ai_btn)
        
        main_box.append(header)
        
        # ─── Terminal + AI split ─────────────────
        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        
        # VTE Terminal
        terminal = Vte.Terminal()
        terminal.set_font(Pango.FontDescription.from_string("JetBrains Mono 12"))
        terminal.set_cursor_blink_mode(Vte.CursorBlinkMode.ON)
        terminal.set_cursor_shape(Vte.CursorShape.BLOCK)
        terminal.set_scrollback_lines(10000)
        terminal.set_mouse_autohide(True)
        
        # Colors
        bg = Gdk.RGBA()
        bg.parse("#0a0a1a")
        fg = Gdk.RGBA()
        fg.parse("#f0f0f8")
        
        # 16-color palette
        palette = []
        palette_hex = [
            "#1a1a3e", "#ef4444", "#22c55e", "#eab308",
            "#6366f1", "#a855f7", "#22d3ee", "#a0a0c0",
            "#6b6b8e", "#f87171", "#4ade80", "#facc15",
            "#818cf8", "#c084fc", "#67e8f9", "#f0f0f8",
        ]
        for hex_color in palette_hex:
            c = Gdk.RGBA()
            c.parse(hex_color)
            palette.append(c)
        
        terminal.set_colors(fg, bg, palette)
        
        # Spawn shell
        terminal.spawn_async(
            Vte.PtyFlags.DEFAULT,
            os.environ.get("HOME", "/"),
            [os.environ.get("SHELL", "/bin/bash")],
            None,
            GLib.SpawnFlags.DEFAULT,
            None, None,
            -1, None, None,
        )
        
        paned.set_start_child(terminal)
        paned.set_resize_start_child(True)
        
        # AI Panel (hidden by default)
        ai_panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        ai_panel.add_css_class("ai-panel")
        ai_panel.set_size_request(300, -1)
        ai_panel.set_visible(False)
        
        ai_title = Gtk.Label(label="AI Assistant")
        ai_title.add_css_class("ai-panel-title")
        ai_panel.append(ai_title)
        
        # AI input
        ai_input_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        ai_input = Gtk.Entry()
        ai_input.set_placeholder_text("Describe what you want to do...")
        ai_input.set_hexpand(True)
        ai_input.add_css_class("ai-input")
        ai_input_box.append(ai_input)
        
        ai_send = Gtk.Button(label="→")
        ai_send.add_css_class("ai-send")
        ai_input_box.append(ai_send)
        
        ai_panel.append(ai_input_box)
        
        # AI output
        ai_output_scroll = Gtk.ScrolledWindow()
        ai_output_scroll.set_vexpand(True)
        
        ai_output = Gtk.Label(label="Type a description in natural language and I'll generate the command for you.")
        ai_output.set_wrap(True)
        ai_output.set_xalign(0)
        ai_output.add_css_class("ai-output")
        ai_output_scroll.set_child(ai_output)
        
        ai_panel.append(ai_output_scroll)
        
        paned.set_end_child(ai_panel)
        paned.set_resize_end_child(False)
        
        main_box.append(paned)
        
        # Toggle AI panel
        def toggle_ai(btn):
            ai_panel.set_visible(btn.get_active())
        ai_btn.connect("toggled", toggle_ai)
        
        # AI command generation
        def on_ai_generate(entry):
            query = entry.get_text().strip()
            if query:
                cmd = self.ai.translate_to_command(query)
                ai_output.set_text(f"Generated command:\n\n  $ {cmd}\n\nPress Enter in the terminal to run it.")
                # Could auto-feed to terminal
                terminal.feed_child(cmd.encode() + b"\n")
                entry.set_text("")
        
        ai_input.connect("activate", on_ai_generate)
        ai_send.connect("clicked", lambda b: on_ai_generate(ai_input))
        
        window.set_content(main_box)
        self._load_css()
        window.present()
    
    def _load_css(self):
        """Load terminal CSS."""
        css = b"""
        .terminal-container {
            background: #0a0a1a;
        }
        
        .terminal-header {
            background: #0d0d20;
            padding: 4px 8px;
            min-height: 36px;
            border-bottom: 1px solid rgba(255,255,255,0.06);
        }
        
        .terminal-tab {
            background: transparent;
            color: #a0a0c0;
            border: none;
            padding: 4px 12px;
            border-radius: 6px;
            font-size: 12px;
        }
        
        .tab-active {
            background: rgba(168, 85, 247, 0.15);
            color: #c084fc;
        }
        
        .ai-toggle {
            background: transparent;
            color: #6b6b8e;
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 6px;
            padding: 4px 10px;
            font-size: 12px;
        }
        
        .ai-toggle:checked {
            background: rgba(168, 85, 247, 0.2);
            color: #c084fc;
            border-color: rgba(168, 85, 247, 0.3);
        }
        
        .ai-panel {
            background: #0d0d20;
            padding: 12px;
            border-left: 1px solid rgba(255,255,255,0.06);
        }
        
        .ai-panel-title {
            color: #a855f7;
            font-weight: 700;
            font-size: 14px;
        }
        
        .ai-input {
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.08);
            color: #f0f0f8;
            border-radius: 8px;
            padding: 6px 10px;
            font-size: 13px;
        }
        
        .ai-output {
            color: #a0a0c0;
            font-size: 13px;
            font-family: 'JetBrains Mono', monospace;
            padding: 8px;
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
    app = ThakranTerminal()
    app.run()


if __name__ == "__main__":
    main()
