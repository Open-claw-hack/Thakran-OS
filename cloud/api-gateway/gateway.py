#!/usr/bin/env python3
"""
============================================================================
Thakran OS — Cloud AI API Gateway
============================================================================
Routes AI requests to cloud providers for premium subscriptions.
Acts as a proxy between the local thakran-aid daemon and cloud APIs.

Supported providers:
  - OpenAI (GPT-4, GPT-4o)
  - Anthropic (Claude Sonnet, Opus)
  - Google (Gemini Pro, Ultra)

Features:
  - Authentication & token management
  - Request routing by model
  - Usage tracking & rate limiting
  - Automatic fallback to local models
  - Response caching
============================================================================
"""

import asyncio
import json
import os
import time
from pathlib import Path


# ─── Provider Configuration ────────────────────────────────────────────────

PROVIDERS = {
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "models": {
            "gpt-4o": "gpt-4o",
            "gpt-4": "gpt-4-turbo",
        },
        "auth_header": "Authorization",
        "auth_prefix": "Bearer",
    },
    "anthropic": {
        "base_url": "https://api.anthropic.com/v1",
        "models": {
            "claude-sonnet": "claude-3-5-sonnet-20241022",
            "claude-opus": "claude-3-opus-20240229",
        },
        "auth_header": "x-api-key",
        "auth_prefix": "",
    },
    "google": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "models": {
            "gemini-pro": "gemini-1.5-pro",
            "gemini-ultra": "gemini-1.5-ultra",
        },
        "auth_header": "x-goog-api-key",
        "auth_prefix": "",
    },
    "github-copilot": {
        "base_url": "https://api.githubcopilot.com",
        "models": {
            "copilot-chat": "gpt-4o",
            "copilot-base": "gpt-3.5-turbo",
        },
        "auth_header": "Authorization",
        "auth_prefix": "Bearer",
    },
}


class SubscriptionManager:
    """Manages user subscription and authentication."""
    
    def __init__(self):
        self.token_path = "/var/lib/thakran/cloud/auth.token"
        self.subscription_path = "/var/lib/thakran/cloud/subscription.json"
    
    def is_subscribed(self) -> bool:
        """Check if user has an active subscription."""
        if not os.path.exists(self.subscription_path):
            return False
        
        try:
            with open(self.subscription_path) as f:
                sub = json.load(f)
            # Check expiry
            return sub.get("active", False) and sub.get("expires_at", 0) > time.time()
        except Exception:
            return False
    
    def get_plan(self) -> str:
        """Get current subscription plan."""
        try:
            with open(self.subscription_path) as f:
                return json.load(f).get("plan", "free")
        except Exception:
            return "free"
    
    def get_auth_token(self) -> str:
        """Get authentication token."""
        try:
            with open(self.token_path) as f:
                return f.read().strip()
        except FileNotFoundError:
            return ""
    
    def get_allowed_models(self) -> list:
        """Get models allowed by current subscription."""
        plans_path = Path(__file__).parent.parent / "subscription" / "plans.json"
        plan_id = self.get_plan()
        
        try:
            with open(plans_path) as f:
                plans = json.load(f)
            
            for plan in plans.get("plans", []):
                if plan["id"] == plan_id:
                    return plan["features"].get("cloud_models", [])
        except Exception:
            pass
        
        return []


class UsageTracker:
    """Tracks API usage for rate limiting and billing."""
    
    def __init__(self):
        self.usage_path = "/var/lib/thakran/cloud/usage.json"
        self.usage = self._load()
    
    def _load(self) -> dict:
        """Load usage data."""
        try:
            with open(self.usage_path) as f:
                return json.load(f)
        except Exception:
            return {"requests_today": 0, "tokens_today": 0, "date": ""}
    
    def _save(self):
        """Save usage data."""
        os.makedirs(os.path.dirname(self.usage_path), exist_ok=True)
        with open(self.usage_path, "w") as f:
            json.dump(self.usage, f, indent=2)
    
    def record(self, tokens_used: int):
        """Record an API request."""
        today = time.strftime("%Y-%m-%d")
        
        if self.usage.get("date") != today:
            self.usage = {"requests_today": 0, "tokens_today": 0, "date": today}
        
        self.usage["requests_today"] += 1
        self.usage["tokens_today"] += tokens_used
        self._save()
    
    def check_limit(self, daily_limit: int) -> bool:
        """Check if within daily request limit."""
        today = time.strftime("%Y-%m-%d")
        if self.usage.get("date") != today:
            return True
        return self.usage.get("requests_today", 0) < daily_limit


class CloudAIGateway:
    """Routes AI requests to cloud providers."""
    
    def __init__(self):
        self.subscription = SubscriptionManager()
        self.usage = UsageTracker()
    
    def _get_provider(self, model: str) -> tuple:
        """Find which provider handles this model."""
        for provider_name, config in PROVIDERS.items():
            if model in config["models"]:
                return provider_name, config
        return None, None
    
    async def route_request(self, request: dict) -> dict:
        """Route a chat/generate request to the appropriate cloud provider."""
        model = request.get("model", "")
        
        # Check subscription
        if not self.subscription.is_subscribed():
            return {
                "error": "No active subscription",
                "message": "Subscribe to Pro or Team to access cloud AI models.",
                "fallback": "local",
            }
        
        # Check model access
        allowed = self.subscription.get_allowed_models()
        if allowed != "all" and model not in allowed:
            return {
                "error": f"Model '{model}' not available on your plan",
                "allowed_models": allowed,
            }
        
        # Check rate limit
        if not self.usage.check_limit(1000):
            return {
                "error": "Daily request limit reached",
                "fallback": "local",
            }
        
        # Find provider
        provider_name, provider_config = self._get_provider(model)
        if not provider_config:
            return {"error": f"Unknown model: {model}"}
        
        # Route to provider
        result = await self._call_provider(
            provider_name, provider_config, model, request
        )
        
        # Track usage
        tokens = result.get("usage", {}).get("total_tokens", 0)
        self.usage.record(tokens)
        
        return result
    
    async def _call_provider(self, provider_name: str, config: dict,
                              model: str, request: dict) -> dict:
        """Call a cloud provider's API."""
        import urllib.request
        
        api_model = config["models"][model]
        token = self.subscription.get_auth_token()
        
        headers = {
            "Content-Type": "application/json",
        }
        
        auth_prefix = config.get("auth_prefix", "")
        auth_value = f"{auth_prefix} {token}".strip() if auth_prefix else token
        headers[config["auth_header"]] = auth_value
        
        # Build request based on provider
        if provider_name == "openai":
            url = f"{config['base_url']}/chat/completions"
            payload = {
                "model": api_model,
                "messages": request.get("messages", []),
                "max_tokens": request.get("options", {}).get("max_tokens", 1024),
                "temperature": request.get("options", {}).get("temperature", 0.7),
            }
        elif provider_name == "anthropic":
            url = f"{config['base_url']}/messages"
            payload = {
                "model": api_model,
                "messages": request.get("messages", []),
                "max_tokens": request.get("options", {}).get("max_tokens", 1024),
            }
        elif provider_name == "google":
            url = f"{config['base_url']}/models/{api_model}:generateContent"
            payload = {
                "contents": [
                    {"parts": [{"text": m.get("content", "")}]}
                    for m in request.get("messages", [])
                ],
            }
        elif provider_name == "github-copilot":
            url = f"{config['base_url']}/chat/completions"
            headers["Editor-Version"] = "vscode/1.90.0"
            headers["Editor-Plugin-Version"] = "copilot-chat/0.17.0"
            payload = {
                "model": api_model,
                "messages": request.get("messages", []),
                "max_tokens": request.get("options", {}).get("max_tokens", 1024),
                "temperature": request.get("options", {}).get("temperature", 0.7),
            }
        else:
            return {"error": f"Unsupported provider: {provider_name}"}
        
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode(),
                headers=headers,
            )
            
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read())
            
            # Normalize response
            return self._normalize_response(provider_name, data, model)
            
        except Exception as e:
            return {
                "error": f"Cloud API error: {str(e)}",
                "provider": provider_name,
                "fallback": "local",
            }
    
    def _normalize_response(self, provider: str, data: dict, model: str) -> dict:
        """Normalize provider responses to Thakran format."""
        if provider == "openai":
            choice = data.get("choices", [{}])[0]
            return {
                "model": model,
                "message": choice.get("message", {}),
                "usage": data.get("usage", {}),
                "provider": "cloud:openai",
                "done": True,
            }
        elif provider == "anthropic":
            content = data.get("content", [{}])[0]
            return {
                "model": model,
                "message": {
                    "role": "assistant",
                    "content": content.get("text", ""),
                },
                "usage": data.get("usage", {}),
                "provider": "cloud:anthropic",
                "done": True,
            }
        elif provider == "google":
            candidates = data.get("candidates", [{}])
            content = candidates[0].get("content", {}).get("parts", [{}])[0]
            return {
                "model": model,
                "message": {
                    "role": "assistant",
                    "content": content.get("text", ""),
                },
                "provider": "cloud:google",
                "done": True,
            }
        elif provider == "github-copilot":
            choice = data.get("choices", [{}])[0]
            return {
                "model": model,
                "message": choice.get("message", {}),
                "usage": data.get("usage", {}),
                "provider": "cloud:github-copilot",
                "done": True,
            }
        
        return data


def main():
    """Run the gateway as a standalone service (for testing)."""
    gateway = CloudAIGateway()
    print(f"Cloud AI Gateway initialized")
    print(f"Subscription: {gateway.subscription.get_plan()}")
    print(f"Active: {gateway.subscription.is_subscribed()}")


if __name__ == "__main__":
    main()
