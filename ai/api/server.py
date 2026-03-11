#!/usr/bin/env python3
"""
============================================================================
Thakran OS — Local AI API Server
============================================================================
FastAPI-based REST API exposing AI capabilities to all Thakran OS apps.
Compatible with Ollama API format for ecosystem compatibility.

Endpoints:
  POST /api/generate       - Text generation
  POST /api/chat           - Chat completion
  POST /api/embeddings     - Text embeddings
  GET  /api/tags           - List available models
  POST /api/pull           - Download a model
  GET  /api/status         - Daemon status
  GET  /api/hardware       - Hardware profile
  POST /api/transcribe     - Speech-to-text (Whisper)

  # Thakran-specific extensions
  POST /api/system/command  - AI-powered system commands
  POST /api/files/search    - Semantic file search
  GET  /api/agents          - List AI agents
  POST /api/agents/run      - Run an AI agent
============================================================================
"""

import asyncio
import json
import time
import os
from typing import AsyncGenerator, Optional
from contextlib import asynccontextmanager

# ─── App Setup ──────────────────────────────────────────────────────────────

# In production, these would be proper FastAPI imports
# For the skeleton, we define the API structure

API_VERSION = "0.1.0"
API_PREFIX = "/api"


class ThakranAPIServer:
    """REST API server for the Thakran AI daemon."""

    def __init__(self, daemon=None):
        self.daemon = daemon
        self.start_time = time.time()
        self.request_count = 0

    # ─── Core AI Endpoints ──────────────────────────────────────────────

    async def generate(self, request: dict) -> dict:
        """
        POST /api/generate
        Text generation endpoint (Ollama-compatible).
        
        Request:
            {
                "model": "thakran-mini",
                "prompt": "Explain quantum computing",
                "stream": false,
                "options": {
                    "temperature": 0.7,
                    "max_tokens": 512,
                    "top_p": 0.9
                }
            }
        """
        self.request_count += 1
        model = request.get("model", "thakran-mini")
        prompt = request.get("prompt", "")
        stream = request.get("stream", False)
        options = request.get("options", {})

        if not prompt:
            return {"error": "Prompt is required", "status": 400}

        if self.daemon:
            result = await self.daemon.model_manager.generate(prompt, **options)
            return result

        return {
            "model": model,
            "created_at": time.time(),
            "response": f"[Thakran AI] Generated response for: {prompt[:100]}",
            "done": True,
        }

    async def chat(self, request: dict) -> dict:
        """
        POST /api/chat
        Chat completion endpoint (Ollama-compatible).
        
        Request:
            {
                "model": "thakran-mini",
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Hello!"}
                ],
                "stream": false
            }
        """
        self.request_count += 1
        messages = request.get("messages", [])
        model = request.get("model", "thakran-mini")

        # Convert chat messages to a single prompt
        prompt = self._format_chat(messages)

        if self.daemon:
            result = await self.daemon.model_manager.generate(prompt, **request.get("options", {}))
            return {
                "model": model,
                "message": {
                    "role": "assistant",
                    "content": result.get("response", ""),
                },
                "done": True,
            }

        return {
            "model": model,
            "message": {
                "role": "assistant",
                "content": "[Thakran AI] Chat response",
            },
            "done": True,
        }

    async def embeddings(self, request: dict) -> dict:
        """
        POST /api/embeddings
        Generate text embeddings for semantic search.
        """
        self.request_count += 1
        text = request.get("prompt", request.get("input", ""))
        model = request.get("model", "thakran-embed")

        # In production, this would use a real embedding model
        return {
            "model": model,
            "embedding": [0.0] * 384,  # Placeholder 384-dim embedding
        }

    # ─── Model Management ──────────────────────────────────────────────

    async def list_models(self) -> dict:
        """
        GET /api/tags
        List available models.
        """
        if self.daemon:
            models = self.daemon.model_manager.list_available_models()
            return {"models": models}

        return {
            "models": [
                {
                    "name": "thakran-mini",
                    "size_gb": 2.0,
                    "description": "Fast, lightweight model for everyday tasks",
                    "quantization": "Q4_K_M",
                },
                {
                    "name": "thakran-standard",
                    "size_gb": 4.5,
                    "description": "Balanced model for general use",
                    "quantization": "Q4_K_M",
                },
                {
                    "name": "thakran-pro",
                    "size_gb": 8.0,
                    "description": "High-capability model for complex tasks",
                    "quantization": "Q5_K_M",
                },
            ]
        }

    async def pull_model(self, request: dict) -> dict:
        """
        POST /api/pull
        Download a model.
        """
        model_name = request.get("name", "")
        if not model_name:
            return {"error": "Model name is required", "status": 400}

        return {
            "status": "downloading",
            "model": model_name,
            "message": f"Downloading {model_name}...",
        }

    # ─── Thakran Extensions ────────────────────────────────────────────

    async def system_command(self, request: dict) -> dict:
        """
        POST /api/system/command
        AI-powered system commands — natural language to system actions.
        
        Request:
            {"command": "open my downloads folder"}
            {"command": "reduce screen brightness to 50%"}
            {"command": "install firefox"}
        """
        command = request.get("command", "")

        return {
            "input": command,
            "interpreted_action": "system.file_manager.open",
            "parameters": {"path": "~/Downloads"},
            "confidence": 0.95,
            "requires_confirmation": False,
        }

    async def file_search(self, request: dict) -> dict:
        """
        POST /api/files/search
        Semantic file search — find files by description.
        
        Request:
            {"query": "the presentation I made last week about AI"}
        """
        query = request.get("query", "")

        return {
            "query": query,
            "results": [],
            "search_time_ms": 0,
        }

    async def list_agents(self) -> dict:
        """
        GET /api/agents
        List available AI agents.
        """
        return {
            "agents": [
                {
                    "name": "system-optimizer",
                    "description": "Continuously optimizes system performance",
                    "status": "active",
                },
                {
                    "name": "file-organizer",
                    "description": "AI-powered file organization and cleanup",
                    "status": "available",
                },
                {
                    "name": "code-assistant",
                    "description": "Programming help and code generation",
                    "status": "available",
                },
                {
                    "name": "notification-filter",
                    "description": "Smart notification prioritization",
                    "status": "active",
                },
            ]
        }

    async def run_agent(self, request: dict) -> dict:
        """
        POST /api/agents/run
        Execute an AI agent with given parameters.
        """
        agent = request.get("agent", "")
        params = request.get("params", {})

        return {
            "agent": agent,
            "status": "started",
            "task_id": f"agent-{int(time.time())}",
        }

    # ─── Status & Info ─────────────────────────────────────────────────

    async def status(self) -> dict:
        """
        GET /api/status
        Get daemon and system status.
        """
        uptime = time.time() - self.start_time

        status = {
            "version": API_VERSION,
            "status": "running",
            "uptime_seconds": round(uptime, 1),
            "requests_served": self.request_count,
        }

        if self.daemon:
            status.update(self.daemon.get_daemon_status())

        return status

    async def hardware(self) -> dict:
        """
        GET /api/hardware
        Get hardware profile and capabilities.
        """
        if self.daemon:
            return self.daemon.hw_profile.to_dict()

        return {"message": "Hardware profiler not initialized"}

    # ─── Helpers ────────────────────────────────────────────────────────

    def _format_chat(self, messages: list) -> str:
        """Format chat messages into a single prompt string."""
        formatted = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                formatted.append(f"System: {content}")
            elif role == "user":
                formatted.append(f"User: {content}")
            elif role == "assistant":
                formatted.append(f"Assistant: {content}")
        formatted.append("Assistant:")
        return "\n".join(formatted)


# ─── FastAPI App Factory ───────────────────────────────────────────────────

def create_app(daemon=None):
    """
    Create the FastAPI application.
    
    In production, this creates the full FastAPI app with:
    - CORS middleware
    - Request validation
    - Streaming response support
    - WebSocket for real-time AI interaction
    - Unix socket listener
    """
    try:
        from fastapi import FastAPI, HTTPException
        from fastapi.middleware.cors import CORSMiddleware
        from fastapi.responses import StreamingResponse

        api = ThakranAPIServer(daemon)

        @asynccontextmanager
        async def lifespan(app):
            yield

        app = FastAPI(
            title="Thakran AI API",
            description="Local AI inference API for Thakran OS",
            version=API_VERSION,
            lifespan=lifespan,
        )

        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Register routes
        app.post(f"{API_PREFIX}/generate")(api.generate)
        app.post(f"{API_PREFIX}/chat")(api.chat)
        app.post(f"{API_PREFIX}/embeddings")(api.embeddings)
        app.get(f"{API_PREFIX}/tags")(api.list_models)
        app.post(f"{API_PREFIX}/pull")(api.pull_model)
        app.get(f"{API_PREFIX}/status")(api.status)
        app.get(f"{API_PREFIX}/hardware")(api.hardware)
        app.post(f"{API_PREFIX}/system/command")(api.system_command)
        app.post(f"{API_PREFIX}/files/search")(api.file_search)
        app.get(f"{API_PREFIX}/agents")(api.list_agents)
        app.post(f"{API_PREFIX}/agents/run")(api.run_agent)

        return app

    except ImportError:
        print("FastAPI not installed. Install with: pip install fastapi uvicorn")
        return None


if __name__ == "__main__":
    import uvicorn

    app = create_app()
    if app:
        uvicorn.run(app, host="127.0.0.1", port=11434)
