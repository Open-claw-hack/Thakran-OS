#!/usr/bin/env python3
"""
============================================================================
Thakran OS — AI Assistant Application
============================================================================
The primary AI chat interface for Thakran OS. Provides:

  - Conversational AI chat (local + cloud models)
  - Voice input/output (Whisper + TTS)
  - System automation via natural language
  - File and app integration
  - Multi-modal support (text, image, voice)
  - Conversation history and context

Built with GTK4 + LibAdwaita for native desktop integration.
============================================================================
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, GLib, Gio, Gdk, Pango
import json
import os
import time
import threading
from datetime import datetime
from pathlib import Path


# ─── Constants ──────────────────────────────────────────────────────────────

APP_ID = "dev.thakranos.assistant"
AI_API_URL = "http://127.0.0.1:11434/api"
HISTORY_DIR = os.path.expanduser("~/.local/share/thakran/assistant/history")


# ─── Data Models ────────────────────────────────────────────────────────────

class Message:
    """A chat message."""
    
    def __init__(self, role: str, content: str, timestamp: float = None):
        self.role = role  # "user", "assistant", "system"
        self.content = content
        self.timestamp = timestamp or time.time()
    
    def to_dict(self):
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
        }


class Conversation:
    """A conversation with the AI."""
    
    def __init__(self, title: str = "New Chat"):
        self.id = f"conv-{int(time.time())}"
        self.title = title
        self.messages: list[Message] = []
        self.model = "thakran-mini"
        self.created_at = time.time()
    
    def add_message(self, role: str, content: str) -> Message:
        msg = Message(role, content)
        self.messages.append(msg)
        
        # Auto-title from first user message
        if len(self.messages) == 1 and role == "user":
            self.title = content[:50] + ("..." if len(content) > 50 else "")
        
        return msg
    
    def to_api_messages(self) -> list[dict]:
        return [
            {"role": "system", "content": self._system_prompt()},
            *[msg.to_dict() for msg in self.messages],
        ]
    
    def _system_prompt(self) -> str:
        return (
            "You are Thakran AI, the built-in assistant for Thakran OS. "
            "You are helpful, concise, and knowledgeable about the system. "
            "You can help users with system settings, file management, "
            "code, creative writing, analysis, and general questions. "
            f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M')}. "
            "System: Thakran OS 0.1.0-alpha."
        )


# ─── AI Client ─────────────────────────────────────────────────────────────

SOCKET_PATH = "/run/thakran/ai.sock"

class AIClient:
    """Client for the Thakran AI daemon via UNIX Socket."""
    
    def chat_stream(self, messages: list[dict], model: str = "thakran-mini"):
        """Send a chat completion request and yield streamed tokens."""
        req = {
            "type": "chat",
            "model": model,
            "messages": messages,
            "stream": True
        }
        
        import socket
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
                s.connect(SOCKET_PATH)
                s.sendall(json.dumps(req).encode() + b'\n')
                
                buffer = ""
                while True:
                    chunk = s.recv(1024).decode()
                    if not chunk:
                        break
                    buffer += chunk
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        if line.strip():
                            try:
                                data = json.loads(line)
                                if "error" in data:
                                    yield f"\n[Error: {data['error']}]"
                                    return
                                if "response" in data:
                                    yield data["response"]
                                if data.get("done", False):
                                    return
                            except ValueError:
                                pass
        except Exception as e:
            yield f"⚠️ Daemon unreachable: {e}"
    
    def get_status(self) -> dict:
        import socket
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
                s.connect(SOCKET_PATH)
                s.sendall(json.dumps({"type": "status"}).encode() + b'\n')
                return json.loads(s.recv(4096).decode())
        except Exception:
            return {"status": "offline"}


# ─── UI Components ─────────────────────────────────────────────────────────

class MessageBubble(Gtk.Box):
    """A chat message bubble."""
    
    def __init__(self, message: Message):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.message = message
        
        is_user = message.role == "user"
        
        self.add_css_class("message-bubble")
        self.add_css_class("message-user" if is_user else "message-assistant")
        
        # Header (role + time)
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        
        role_label = Gtk.Label(
            label="You" if is_user else "Thakran AI"
        )
        role_label.add_css_class("message-role")
        header.append(role_label)
        
        time_str = datetime.fromtimestamp(message.timestamp).strftime("%H:%M")
        time_label = Gtk.Label(label=time_str)
        time_label.add_css_class("message-time")
        header.append(time_label)
        
        self.append(header)
        
        # Content
        content_label = Gtk.Label(label=message.content)
        content_label.set_wrap(True)
        content_label.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        content_label.set_xalign(0)
        content_label.set_selectable(True)
        content_label.add_css_class("message-content")
        self.append(content_label)


class ConversationSidebar(Gtk.Box):
    """Sidebar listing conversations."""
    
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add_css_class("sidebar")
        self.set_size_request(260, -1)
        
        # Header
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        header.add_css_class("sidebar-header")
        
        title = Gtk.Label(label="Conversations")
        title.add_css_class("sidebar-title")
        title.set_hexpand(True)
        title.set_xalign(0)
        header.append(title)
        
        new_btn = Gtk.Button()
        new_btn.set_icon_name("list-add-symbolic")
        new_btn.add_css_class("new-chat-btn")
        new_btn.set_tooltip_text("New conversation")
        header.append(new_btn)
        
        self.append(header)
        
        # Conversation list
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        
        self.list_box = Gtk.ListBox()
        self.list_box.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.list_box.add_css_class("conversation-list")
        scrolled.set_child(self.list_box)
        
        self.append(scrolled)
        
        # Footer (model selector)
        footer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        footer.add_css_class("sidebar-footer")
        
        model_label = Gtk.Label(label="Model", xalign=0)
        model_label.add_css_class("model-label")
        footer.append(model_label)
        
        self.model_dropdown = Gtk.DropDown.new_from_strings([
            "thakran-mini (2GB)",
            "thakran-standard (4.5GB)",
            "thakran-pro (8GB)",
        ])
        self.model_dropdown.add_css_class("model-dropdown")
        footer.append(self.model_dropdown)
        
        self.append(footer)


class ChatView(Gtk.Box):
    """Main chat area."""
    
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_hexpand(True)
        
        self.conversation: Conversation = None
        self.client = AIClient()
        
        # ─── Chat Header ────────────────────────
        self.header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.header.add_css_class("chat-header")
        
        self.chat_title = Gtk.Label(label="New Chat")
        self.chat_title.add_css_class("chat-title")
        self.chat_title.set_hexpand(True)
        self.chat_title.set_xalign(0)
        self.header.append(self.chat_title)
        
        # AI Status dot
        self.status_dot = Gtk.DrawingArea()
        self.status_dot.set_size_request(8, 8)
        self.status_dot.add_css_class("status-dot")
        self.header.append(self.status_dot)
        
        self.status_label = Gtk.Label(label="Ready")
        self.status_label.add_css_class("status-label")
        self.header.append(self.status_label)
        
        self.append(self.header)
        
        # ─── Messages Area ──────────────────────
        self.scrolled = Gtk.ScrolledWindow()
        self.scrolled.set_vexpand(True)
        self.scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        
        self.messages_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.messages_box.add_css_class("messages-container")
        
        # Welcome message
        welcome = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        welcome.add_css_class("welcome-container")
        welcome.set_valign(Gtk.Align.CENTER)
        welcome.set_vexpand(True)
        
        welcome_title = Gtk.Label(label="Thakran AI")
        welcome_title.add_css_class("welcome-title")
        welcome.append(welcome_title)
        
        welcome_sub = Gtk.Label(label="Your intelligent assistant, running locally on your hardware.")
        welcome_sub.add_css_class("welcome-subtitle")
        welcome.append(welcome_sub)
        
        # Suggestion chips
        suggestions = Gtk.FlowBox()
        suggestions.set_max_children_per_line(2)
        suggestions.set_selection_mode(Gtk.SelectionMode.NONE)
        suggestions.add_css_class("suggestions")
        
        suggestion_texts = [
            "🔧 Optimize my system performance",
            "📁 Find large files taking up space",
            "💻 Help me write a Python script",
            "🎨 Customize my desktop theme",
        ]
        
        for text in suggestion_texts:
            chip = Gtk.Button(label=text)
            chip.add_css_class("suggestion-chip")
            suggestions.append(chip)
        
        welcome.append(suggestions)
        self.messages_box.append(welcome)
        
        self.scrolled.set_child(self.messages_box)
        self.append(self.scrolled)
        
        # ─── Input Area ─────────────────────────
        input_frame = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        input_frame.add_css_class("input-frame")
        
        # Attachment button
        attach_btn = Gtk.Button()
        attach_btn.set_icon_name("mail-attachment-symbolic")
        attach_btn.add_css_class("input-action-btn")
        attach_btn.set_tooltip_text("Attach file")
        input_frame.append(attach_btn)
        
        # Text input
        self.input_entry = Gtk.TextView()
        self.input_entry.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.input_entry.add_css_class("chat-input")
        self.input_entry.set_hexpand(True)
        
        input_scroll = Gtk.ScrolledWindow()
        input_scroll.set_max_content_height(120)
        input_scroll.set_propagate_natural_height(True)
        input_scroll.set_child(self.input_entry)
        input_frame.append(input_scroll)
        
        # Voice button
        voice_btn = Gtk.Button()
        voice_btn.set_icon_name("audio-input-microphone-symbolic")
        voice_btn.add_css_class("input-action-btn")
        voice_btn.set_tooltip_text("Voice input")
        input_frame.append(voice_btn)
        
        # Send button
        send_btn = Gtk.Button()
        send_btn.set_icon_name("go-up-symbolic")
        send_btn.add_css_class("send-btn")
        send_btn.set_tooltip_text("Send message")
        send_btn.connect("clicked", self._on_send)
        input_frame.append(send_btn)
        
        self.append(input_frame)
    
    def set_conversation(self, conversation: Conversation):
        """Load a conversation."""
        self.conversation = conversation
        self.chat_title.set_text(conversation.title)
        
        # Clear and reload messages
        while True:
            child = self.messages_box.get_first_child()
            if child is None:
                break
            self.messages_box.remove(child)
        
        for msg in conversation.messages:
            bubble = MessageBubble(msg)
            self.messages_box.append(bubble)
    
    def _on_send(self, button):
        """Send a message."""
        buffer = self.input_entry.get_buffer()
        text = buffer.get_text(
            buffer.get_start_iter(),
            buffer.get_end_iter(),
            False
        ).strip()
        
        if not text:
            return
        
        # Initialize conversation if needed
        if not self.conversation:
            self.conversation = Conversation()
        
        # Add user message
        user_msg = self.conversation.add_message("user", text)
        bubble = MessageBubble(user_msg)
        self.messages_box.append(bubble)
        
        # Clear input
        buffer.set_text("")
        
        # Show typing indicator
        self.status_label.set_text("Thinking...")
        
        # Send to AI in background thread
        thread = threading.Thread(
            target=self._generate_response,
            args=(text,),
            daemon=True,
        )
        thread.start()
    
    def _generate_response(self, user_text):
        """Generate AI response in background."""
        messages = self.conversation.to_api_messages()
        
        # Create an empty message bubble on the main thread first
        GLib.idle_add(self._create_empty_bubble)
        
        # Stream tokens
        for token in self.client.chat_stream(messages, model=self.conversation.model):
            GLib.idle_add(self._append_token, token)
            
        GLib.idle_add(self._finish_stream)
    
    def _create_empty_bubble(self):
        msg = self.conversation.add_message("assistant", "")
        self.current_bubble = MessageBubble(msg)
        self.messages_box.append(self.current_bubble)
        self._scroll_down()
        
    def _append_token(self, token):
        if hasattr(self, 'current_bubble'):
            # The Content label is the last child of the vertical box
            lbl = self.current_bubble.get_last_child()
            current_text = lbl.get_text()
            lbl.set_text(current_text + token)
            self.conversation.messages[-1].content += token
            self._scroll_down()
            
    def _finish_stream(self):
        self.status_label.set_text("Ready")
        self.chat_title.set_text(self.conversation.title)
        
    def _scroll_down(self):
        adj = self.scrolled.get_vadjustment()
        adj.set_value(adj.get_upper())


# ─── Main Application ──────────────────────────────────────────────────────

class ThakranAssistant(Adw.Application):
    """The Thakran AI Assistant application."""
    
    def __init__(self):
        super().__init__(application_id=APP_ID)
        self.connect("activate", self._on_activate)
    
    def _on_activate(self, app):
        """Build and show the assistant."""
        window = Adw.ApplicationWindow(application=app)
        window.set_title("Thakran AI Assistant")
        window.set_default_size(960, 680)
        
        # Main layout
        main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        main_box.add_css_class("assistant-container")
        
        # Sidebar
        sidebar = ConversationSidebar()
        main_box.append(sidebar)
        
        # Separator
        sep = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        main_box.append(sep)
        
        # Chat view
        chat = ChatView()
        main_box.append(chat)
        
        window.set_content(main_box)
        self._load_css()
        window.present()
    
    def _load_css(self):
        """Load application CSS."""
        css = b"""
        .assistant-container {
            background: #0a0a1a;
        }
        
        .sidebar {
            background: #0d0d20;
        }
        
        .sidebar-header {
            padding: 16px;
            border-bottom: 1px solid rgba(255,255,255,0.06);
        }
        
        .sidebar-title {
            color: #f0f0f8;
            font-weight: 700;
            font-size: 16px;
        }
        
        .sidebar-footer {
            padding: 12px 16px;
            border-top: 1px solid rgba(255,255,255,0.06);
        }
        
        .chat-header {
            padding: 12px 20px;
            border-bottom: 1px solid rgba(255,255,255,0.06);
        }
        
        .chat-title {
            color: #f0f0f8;
            font-weight: 600;
            font-size: 15px;
        }
        
        .status-label {
            color: #22c55e;
            font-size: 12px;
        }
        
        .messages-container {
            padding: 20px;
        }
        
        .message-bubble {
            padding: 12px 16px;
            border-radius: 12px;
            max-width: 80%;
        }
        
        .message-user {
            background: rgba(168, 85, 247, 0.15);
            margin-left: 20%;
        }
        
        .message-assistant {
            background: rgba(255, 255, 255, 0.05);
            margin-right: 20%;
        }
        
        .message-role {
            font-weight: 600;
            font-size: 12px;
            color: #a0a0c0;
        }
        
        .message-time {
            font-size: 11px;
            color: #6b6b8e;
        }
        
        .message-content {
            color: #f0f0f8;
            font-size: 14px;
            line-height: 1.6;
        }
        
        .welcome-container {
            padding: 60px 40px;
        }
        
        .welcome-title {
            color: #a855f7;
            font-size: 32px;
            font-weight: 700;
        }
        
        .welcome-subtitle {
            color: #6b6b8e;
            font-size: 16px;
        }
        
        .suggestion-chip {
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.08);
            color: #a0a0c0;
            border-radius: 12px;
            padding: 8px 16px;
            font-size: 13px;
        }
        
        .suggestion-chip:hover {
            background: rgba(168, 85, 247, 0.1);
            border-color: rgba(168, 85, 247, 0.3);
            color: #c084fc;
        }
        
        .input-frame {
            padding: 12px 16px;
            margin: 8px 16px 16px;
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 16px;
        }
        
        .chat-input {
            background: transparent;
            color: #f0f0f8;
            font-size: 14px;
            border: none;
            min-height: 24px;
        }
        
        .send-btn {
            background: #a855f7;
            color: white;
            border-radius: 50%;
            min-width: 36px;
            min-height: 36px;
            padding: 0;
        }
        
        .send-btn:hover {
            background: #9333ea;
        }
        
        .input-action-btn {
            background: transparent;
            border: none;
            color: #6b6b8e;
            min-width: 32px;
        }
        
        .input-action-btn:hover {
            color: #a0a0c0;
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
    """Run the assistant."""
    app = ThakranAssistant()
    app.run()


if __name__ == "__main__":
    main()
