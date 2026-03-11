#!/usr/bin/env python3
"""
============================================================================
Thakran AI Daemon (thakran-aid)
============================================================================
The core AI service for Thakran OS. Runs as a system daemon providing:

  - Local AI model inference (llama.cpp / ONNX Runtime)
  - Hardware-optimized model loading and execution
  - Multi-model management (load, switch, unload)
  - System-wide AI API via Unix socket and HTTP
  - AI agent execution environment
  - Online AI proxy for subscription users

This daemon starts at boot and provides AI capabilities to all
Thakran OS applications through a unified API.
============================================================================
"""

import asyncio
import json
import logging
import os
import signal
import sys
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import yaml

# ─── Constants ──────────────────────────────────────────────────────────────

VERSION = "0.1.0-alpha"
DEFAULT_CONFIG = "/etc/thakran/ai/config.yaml"
SOCKET_PATH = "/run/thakran/ai.sock"
PID_FILE = "/run/thakran/thakran-aid.pid"
MODEL_CACHE = "/var/cache/thakran/models"
DATA_DIR = "/var/lib/thakran/ai"
LOG_DIR = "/var/log/thakran"

# ─── Logging ────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [thakran-aid] %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("thakran-aid")


# ─── Enums ──────────────────────────────────────────────────────────────────

class ModelBackend(Enum):
    LLAMA_CPP = "llama.cpp"
    ONNX = "onnxruntime"
    WHISPER = "whisper.cpp"
    STABLE_DIFFUSION = "stable-diffusion.cpp"


class DeviceType(Enum):
    CPU = "cpu"
    CUDA = "cuda"
    ROCM = "rocm"
    VULKAN = "vulkan"
    NPU = "npu"
    AUTO = "auto"


class ModelStatus(Enum):
    UNLOADED = "unloaded"
    LOADING = "loading"
    READY = "ready"
    ERROR = "error"


# ─── Data Classes ───────────────────────────────────────────────────────────

@dataclass
class HardwareProfile:
    """Detected hardware capabilities."""
    cpu_name: str = "Unknown"
    cpu_cores: int = 1
    cpu_threads: int = 1
    cpu_features: list = field(default_factory=list)  # AVX2, AVX512, etc.
    ram_total_gb: float = 0.0
    ram_available_gb: float = 0.0
    gpu_name: str = "None"
    gpu_vram_gb: float = 0.0
    gpu_type: str = "none"  # nvidia, amd, intel, none
    npu_available: bool = False
    npu_name: str = "None"
    recommended_device: DeviceType = DeviceType.CPU
    max_model_size_gb: float = 0.0
    recommended_context_length: int = 2048
    recommended_batch_size: int = 8

    def to_dict(self) -> dict:
        return {
            "cpu": {
                "name": self.cpu_name,
                "cores": self.cpu_cores,
                "threads": self.cpu_threads,
                "features": self.cpu_features,
            },
            "ram": {
                "total_gb": self.ram_total_gb,
                "available_gb": self.ram_available_gb,
            },
            "gpu": {
                "name": self.gpu_name,
                "vram_gb": self.gpu_vram_gb,
                "type": self.gpu_type,
            },
            "npu": {
                "available": self.npu_available,
                "name": self.npu_name,
            },
            "recommendations": {
                "device": self.recommended_device.value,
                "max_model_size_gb": self.max_model_size_gb,
                "context_length": self.recommended_context_length,
                "batch_size": self.recommended_batch_size,
            },
        }


@dataclass
class ModelInfo:
    """Information about a loaded or available model."""
    name: str
    path: str
    backend: ModelBackend
    size_gb: float
    status: ModelStatus = ModelStatus.UNLOADED
    device: DeviceType = DeviceType.AUTO
    context_length: int = 2048
    loaded_at: Optional[float] = None
    requests_served: int = 0
    avg_tokens_per_sec: float = 0.0


# ─── Hardware Profiler ──────────────────────────────────────────────────────

class HardwareProfiler:
    """Detects and profiles hardware capabilities for optimal AI inference."""

    @staticmethod
    def profile() -> HardwareProfile:
        """Detect hardware and generate optimization profile."""
        profile = HardwareProfile()

        try:
            # CPU Detection
            profile.cpu_cores = os.cpu_count() or 1
            profile.cpu_threads = profile.cpu_cores  # Simplified

            if os.path.exists("/proc/cpuinfo"):
                with open("/proc/cpuinfo") as f:
                    cpuinfo = f.read()
                    for line in cpuinfo.split("\n"):
                        if "model name" in line:
                            profile.cpu_name = line.split(":")[1].strip()
                            break
                        if "flags" in line:
                            flags = line.split(":")[1].strip().split()
                            if "avx2" in flags:
                                profile.cpu_features.append("AVX2")
                            if "avx512f" in flags:
                                profile.cpu_features.append("AVX512")
                            if "amx_tile" in flags:
                                profile.cpu_features.append("AMX")

            # RAM Detection
            if os.path.exists("/proc/meminfo"):
                with open("/proc/meminfo") as f:
                    meminfo = f.read()
                    for line in meminfo.split("\n"):
                        if "MemTotal" in line:
                            kb = int(line.split()[1])
                            profile.ram_total_gb = round(kb / 1024 / 1024, 1)
                        if "MemAvailable" in line:
                            kb = int(line.split()[1])
                            profile.ram_available_gb = round(kb / 1024 / 1024, 1)

            # GPU Detection
            profile._detect_gpu(profile)

            # NPU Detection
            profile._detect_npu(profile)

            # Calculate recommendations
            HardwareProfiler._compute_recommendations(profile)

        except Exception as e:
            log.warning(f"Hardware profiling error: {e}")

        return profile

    @staticmethod
    def _detect_gpu(profile: HardwareProfile):
        """Detect GPU type and VRAM."""
        import subprocess

        # Try NVIDIA
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                parts = result.stdout.strip().split(", ")
                profile.gpu_name = parts[0]
                profile.gpu_vram_gb = round(int(parts[1]) / 1024, 1)
                profile.gpu_type = "nvidia"
                return
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        # Try AMD ROCm
        try:
            result = subprocess.run(
                ["rocm-smi", "--showmeminfo", "vram"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                profile.gpu_type = "amd"
                profile.gpu_name = "AMD GPU"
                return
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        # Check for Intel GPU
        if os.path.exists("/sys/class/drm/card0/device/vendor"):
            with open("/sys/class/drm/card0/device/vendor") as f:
                vendor = f.read().strip()
                if vendor == "0x8086":
                    profile.gpu_type = "intel"
                    profile.gpu_name = "Intel Integrated GPU"

    @staticmethod
    def _detect_npu(profile: HardwareProfile):
        """Detect Neural Processing Unit."""
        # Intel NPU
        if os.path.exists("/dev/accel/accel0"):
            profile.npu_available = True
            profile.npu_name = "Intel NPU"

        # Check for other accelerators
        if os.path.exists("/dev/apex_0"):
            profile.npu_available = True
            profile.npu_name = "Google Coral TPU"

    @staticmethod
    def _compute_recommendations(profile: HardwareProfile):
        """Compute optimal inference settings based on hardware."""
        # Device recommendation
        if profile.gpu_type == "nvidia" and profile.gpu_vram_gb >= 4:
            profile.recommended_device = DeviceType.CUDA
        elif profile.gpu_type == "amd":
            profile.recommended_device = DeviceType.ROCM
        elif profile.npu_available:
            profile.recommended_device = DeviceType.NPU
        elif profile.gpu_type != "none":
            profile.recommended_device = DeviceType.VULKAN
        else:
            profile.recommended_device = DeviceType.CPU

        # Max model size (leave headroom for system)
        if profile.recommended_device in (DeviceType.CUDA, DeviceType.ROCM):
            profile.max_model_size_gb = profile.gpu_vram_gb * 0.85
        else:
            profile.max_model_size_gb = profile.ram_available_gb * 0.5

        # Context length based on available memory
        if profile.max_model_size_gb >= 16:
            profile.recommended_context_length = 8192
        elif profile.max_model_size_gb >= 8:
            profile.recommended_context_length = 4096
        else:
            profile.recommended_context_length = 2048

        # Batch size
        if profile.recommended_device != DeviceType.CPU:
            profile.recommended_batch_size = 16
        else:
            profile.recommended_batch_size = 4


# ─── Model Manager ─────────────────────────────────────────────────────────

class ModelManager:
    """Manages AI model lifecycle: download, load, inference, unload."""

    def __init__(self, config: dict, hw_profile: HardwareProfile):
        self.config = config
        self.hw_profile = hw_profile
        self.models: dict[str, ModelInfo] = {}
        self.active_model: Optional[str] = None
        self._inference_engine = None
        self.model_dir = Path(config.get("model_dir", MODEL_CACHE))
        self.model_dir.mkdir(parents=True, exist_ok=True)

    def list_available_models(self) -> list[dict]:
        """List all available models from the registry."""
        registry_path = Path(__file__).parent.parent / "models" / "model-registry.json"
        if registry_path.exists():
            with open(registry_path) as f:
                registry = json.load(f)
            return [
                {
                    **model,
                    "compatible": model["size_gb"] <= self.hw_profile.max_model_size_gb,
                    "recommended_device": self.hw_profile.recommended_device.value,
                }
                for model in registry.get("models", [])
            ]
        return []

    async def load_model(self, model_name: str) -> bool:
        """Load a model into memory for inference."""
        log.info(f"Loading model: {model_name}")

        # Find model in registry
        available = self.list_available_models()
        model_data = next((m for m in available if m["name"] == model_name), None)

        if not model_data:
            log.error(f"Model not found: {model_name}")
            return False

        if not model_data.get("compatible", False):
            log.warning(f"Model {model_name} may be too large for this hardware")

        model_info = ModelInfo(
            name=model_name,
            path=str(self.model_dir / model_data.get("filename", f"{model_name}.gguf")),
            backend=ModelBackend(model_data.get("backend", "llama.cpp")),
            size_gb=model_data.get("size_gb", 0),
            status=ModelStatus.LOADING,
            device=self.hw_profile.recommended_device,
            context_length=min(
                model_data.get("max_context", 4096),
                self.hw_profile.recommended_context_length,
            ),
        )

        self.models[model_name] = model_info

        try:
            # Initialize the inference engine based on backend
            await self._init_engine(model_info)
            model_info.status = ModelStatus.READY
            model_info.loaded_at = time.time()
            self.active_model = model_name
            log.info(f"Model {model_name} loaded successfully on {model_info.device.value}")
            return True
        except Exception as e:
            model_info.status = ModelStatus.ERROR
            log.error(f"Failed to load model {model_name}: {e}")
            return False

    async def _init_engine(self, model: ModelInfo):
        """Initialize the inference engine for a model."""
        if model.backend == ModelBackend.LLAMA_CPP:
            await self._init_llama_cpp(model)
        elif model.backend == ModelBackend.ONNX:
            await self._init_onnx(model)
        elif model.backend == ModelBackend.WHISPER:
            await self._init_whisper(model)

    async def _init_llama_cpp(self, model: ModelInfo):
        """Initialize llama.cpp backend."""
        try:
            from llama_cpp import Llama
        except ImportError:
            log.error("llama-cpp-python is not installed. Run: pip install llama-cpp-python")
            raise ImportError("llama-cpp-python missing")

        engine_config = {
            "model_path": model.path,
            "n_ctx": model.context_length,
            "n_batch": self.hw_profile.recommended_batch_size,
            "n_threads": max(1, self.hw_profile.cpu_threads - 2),
            "n_gpu_layers": -1 if model.device in (DeviceType.CUDA, DeviceType.ROCM, DeviceType.VULKAN) else 0,
            "use_mmap": True,
            "use_mlock": False,
            "verbose": False,
        }
        log.info(f"llama.cpp config: {json.dumps(engine_config, indent=2)}")
        self._inference_engine = Llama(**engine_config)

    async def _init_onnx(self, model: ModelInfo):
        """Initialize ONNX Runtime backend."""
        log.info(f"Initializing ONNX Runtime for {model.name}")
        # In production: ort.InferenceSession(model.path, providers=[...])

    async def _init_whisper(self, model: ModelInfo):
        """Initialize Whisper.cpp backend for speech-to-text."""
        log.info(f"Initializing Whisper.cpp for {model.name}")

    async def generate(self, prompt: str, **kwargs) -> Any:
        """Generate text using the active model. Returns dict or AsyncGenerator if streaming."""
        
        # Check for GitHub Copilot / Cloud API override first
        cloud_auth_path = "/var/lib/thakran/cloud/auth.token"
        if os.path.exists(cloud_auth_path):
            try:
                # Import Gateway dynamically to avoid circular dependencies
                sys.path.append(os.path.join(os.path.dirname(__file__), "../../cloud/api-gateway"))
                from gateway import CloudAIGateway
                gateway = CloudAIGateway()
                
                # Format request for the gateway
                request = {
                    "model": "copilot-chat", # Default to highest tier Copilot model
                    "messages": [{"role": "user", "content": prompt}],
                    "options": {
                        "max_tokens": kwargs.get("max_tokens", 1024),
                        "temperature": kwargs.get("temperature", 0.7),
                    }
                }
                
                start_time = time.time()
                result = await gateway.route_request(request)
                elapsed = time.time() - start_time
                
                if "error" not in result:
                    # Successfully routed via Copilot
                    return {
                        "status": "success",
                        "model": "github-copilot",
                        "device": "cloud",
                        "response": result.get("message", {}).get("content", ""),
                        "usage": result.get("usage", {}),
                        "timing": {"total_ms": round(elapsed * 1000, 2)},
                    }
                else:
                    log.warning(f"Cloud API Failed, falling back to local: {result.get('error')}")
            except Exception as e:
                log.error(f"Failed to route via Cloud Gateway: {e}")

        # Fallback to local inference
        if not self.active_model or self.active_model not in self.models:
            return {"error": "No model loaded", "status": "error"}

        model = self.models[self.active_model]
        if model.status != ModelStatus.READY:
            return {"error": f"Model not ready: {model.status.value}", "status": "error"}

        start_time = time.time()

        # Default generation parameters
        params = {
            "max_tokens": kwargs.get("max_tokens", 512),
            "temperature": kwargs.get("temperature", 0.7),
            "top_p": kwargs.get("top_p", 0.9),
            "top_k": kwargs.get("top_k", 40),
            "repeat_penalty": kwargs.get("repeat_penalty", 1.1),
            "stream": kwargs.get("stream", False),
        }

        try:
            if model.backend == ModelBackend.LLAMA_CPP and self._inference_engine:
                loop = asyncio.get_event_loop()
                
                if params["stream"]:
                    async def stream_generator():
                        # We must run the initial generator creation in an executor
                        def get_iterator():
                            return self._inference_engine(prompt, **params)
                        
                        iterator = await loop.run_in_executor(None, get_iterator)
                        
                        # Yield tokens as they arrive
                        try:
                            # It's a sync generator, so we iterate in an executor too
                            while True:
                                def get_next():
                                    return next(iterator)
                                chunk = await loop.run_in_executor(None, get_next)
                                yield chunk
                        except StopIteration:
                            model.requests_served += 1
                    return stream_generator()
                else:
                    def run_inference():
                        return self._inference_engine(prompt, **params)
                    
                    result = await loop.run_in_executor(None, run_inference)
                    elapsed = time.time() - start_time
                    model.requests_served += 1
                    
                    return {
                        "status": "success",
                        "model": model.name,
                        "device": model.device.value,
                        "response": result["choices"][0]["text"],
                        "usage": result["usage"],
                        "timing": {"total_ms": round(elapsed * 1000, 2)},
                    }

            # Fallback for mock/other backends
            elapsed = time.time() - start_time
            model.requests_served += 1
            return {
                "status": "success",
                "model": model.name,
                "device": model.device.value,
                "response": f"[Thakran AI - {model.name}] Mock response to: {prompt[:50]}...",
                "usage": {"prompt_tokens": len(prompt.split()), "completion_tokens": params["max_tokens"], "total_tokens": len(prompt.split()) + params["max_tokens"]},
                "timing": {"total_ms": round(elapsed * 1000, 2)},
            }
        except Exception as e:
            log.error(f"Generation error: {e}")
            return {"error": str(e), "status": "error"}

    async def unload_model(self, model_name: str):
        """Unload a model from memory."""
        if model_name in self.models:
            self.models[model_name].status = ModelStatus.UNLOADED
            if self.active_model == model_name:
                self.active_model = None
            log.info(f"Model {model_name} unloaded")

    def get_status(self) -> dict:
        """Get current status of all models."""
        return {
            "active_model": self.active_model,
            "models": {
                name: {
                    "status": m.status.value,
                    "device": m.device.value,
                    "size_gb": m.size_gb,
                    "requests_served": m.requests_served,
                    "loaded_at": m.loaded_at,
                }
                for name, m in self.models.items()
            },
            "hardware": self.hw_profile.to_dict(),
        }


# ─── AI Daemon ──────────────────────────────────────────────────────────────

class ThakranAIDaemon:
    """Main daemon process orchestrating all AI services."""

    def __init__(self, config_path: str = DEFAULT_CONFIG):
        self.config = self._load_config(config_path)
        self.hw_profile = HardwareProfiler.profile()
        self.model_manager = ModelManager(self.config, self.hw_profile)
        self.running = False
        self._server = None
        self.start_time = 0.0

    def _load_config(self, config_path: str) -> dict:
        """Load daemon configuration."""
        if os.path.exists(config_path):
            with open(config_path) as f:
                return yaml.safe_load(f) or {}
        log.warning(f"Config not found at {config_path}, using defaults")
        return {
            "api": {
                "host": "127.0.0.1",
                "port": 11434,
                "socket": SOCKET_PATH,
            },
            "models": {
                "default": "thakran-mini",
                "auto_load": True,
            },
            "performance": {
                "max_concurrent": 4,
                "request_timeout": 120,
            },
        }

    async def start(self):
        """Start the AI daemon."""
        self.running = True
        self.start_time = time.time()

        log.info("=" * 60)
        log.info(f"  Thakran AI Daemon v{VERSION}")
        log.info(f"  Hardware: {self.hw_profile.cpu_name}")
        log.info(f"  RAM: {self.hw_profile.ram_total_gb}GB total, "
                 f"{self.hw_profile.ram_available_gb}GB available")
        log.info(f"  GPU: {self.hw_profile.gpu_name} ({self.hw_profile.gpu_vram_gb}GB)")
        log.info(f"  NPU: {self.hw_profile.npu_name}")
        log.info(f"  Recommended device: {self.hw_profile.recommended_device.value}")
        log.info(f"  Max model size: {self.hw_profile.max_model_size_gb}GB")
        log.info("=" * 60)

        # Register signal handlers
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)

        # Write PID file
        os.makedirs(os.path.dirname(PID_FILE), exist_ok=True)
        with open(PID_FILE, "w") as f:
            f.write(str(os.getpid()))

        # Auto-load default model if configured
        if self.config.get("models", {}).get("auto_load", True):
            default_model = self.config.get("models", {}).get("default", "thakran-mini")
            log.info(f"Auto-loading default model: {default_model}")
            await self.model_manager.load_model(default_model)

        # Start API server
        api_config = self.config.get("api", {})
        host = api_config.get("host", "127.0.0.1")
        port = api_config.get("port", 11434)

        log.info(f"Starting API server on {host}:{port}")
        log.info(f"Unix socket: {api_config.get('socket', SOCKET_PATH)}")

        # Notify systemd that we're ready
        self._notify_systemd("READY=1")

        # Keep running
        try:
            while self.running:
                await asyncio.sleep(1)
                # Periodic health check / watchdog
                self._notify_systemd("WATCHDOG=1")
        except asyncio.CancelledError:
            pass
        finally:
            await self.shutdown()

    async def shutdown(self):
        """Graceful shutdown."""
        log.info("Shutting down Thakran AI Daemon...")
        self.running = False

        # Unload all models
        for name in list(self.model_manager.models.keys()):
            await self.model_manager.unload_model(name)

        # Clean up PID file
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)

        uptime = time.time() - self.start_time
        log.info(f"Thakran AI Daemon stopped. Uptime: {uptime:.0f}s")

    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signals."""
        self.running = False

    def _notify_systemd(self, state: str):
        """Send notification to systemd."""
        notify_socket = os.environ.get("NOTIFY_SOCKET")
        if notify_socket:
            import socket as sock
            s = sock.socket(sock.AF_UNIX, sock.SOCK_DGRAM)
            try:
                s.connect(notify_socket)
                s.sendall(state.encode())
            finally:
                s.close()

    def get_daemon_status(self) -> dict:
        """Get comprehensive daemon status."""
        return {
            "version": VERSION,
            "uptime_seconds": round(time.time() - self.start_time, 1),
            "pid": os.getpid(),
            "models": self.model_manager.get_status(),
        }


# ─── Entry Point ────────────────────────────────────────────────────────────

def main():
    """Main entry point for the Thakran AI Daemon."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Thakran AI Daemon — Local AI inference service",
        prog="thakran-aid",
    )
    parser.add_argument(
        "--config", "-c",
        default=DEFAULT_CONFIG,
        help=f"Path to config file (default: {DEFAULT_CONFIG})"
    )
    parser.add_argument(
        "--version", "-v",
        action="version",
        version=f"thakran-aid {VERSION}"
    )

    args = parser.parse_args()

    daemon = ThakranAIDaemon(config_path=args.config)

    try:
        asyncio.run(daemon.start())
    except KeyboardInterrupt:
        log.info("Interrupted by user")
    except Exception as e:
        log.critical(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
