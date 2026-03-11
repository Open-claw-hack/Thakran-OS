#!/usr/bin/env python3
"""
============================================================================
Thakran OS — Adaptive AI Scaler
============================================================================
Automatically selects the right AI model and inference settings based on
available hardware. This is what makes Thakran OS run on everything from
a Raspberry Pi to a workstation.

Performance Tiers:
  🌱 Nano  (512MB-1GB) → Cloud AI only, or thakran-nano (50MB ONNX)
  🌿 Lite  (2-4GB)     → thakran-tiny (700MB GGUF, Q2_K)
  🌳 Std   (8-16GB)    → thakran-standard (4.5GB GGUF, Q4_K_M)
  🏔 Ultra (32GB+)     → thakran-pro/ultra (8-20GB, Q6_K/Q8_0)
============================================================================
"""

import json
import os
import platform
import subprocess
from dataclasses import dataclass


@dataclass
class HardwareProfile:
    """Detected hardware capabilities."""
    arch: str                # x86_64, aarch64
    cpu_cores: int
    cpu_name: str
    ram_total_mb: int
    ram_available_mb: int
    gpu_type: str            # nvidia, amd, intel, mali, videocore, apple, none
    gpu_name: str
    gpu_vram_mb: int
    has_neon: bool           # ARM NEON SIMD
    has_avx2: bool           # x86 AVX2
    has_npu: bool
    storage_type: str        # nvme, ssd, hdd, sdcard, emmc
    is_battery: bool


@dataclass
class AIConfig:
    """Generated AI configuration for this hardware."""
    tier: str                # nano, lite, standard, ultra
    model_id: str
    model_file: str
    model_size_mb: int
    backend: str             # cpu, cuda, rocm, vulkan, metal, onnx
    cpu_threads: int
    gpu_layers: int          # How many layers to offload to GPU
    context_length: int
    batch_size: int
    use_mmap: bool
    use_mlock: bool
    quantization: str
    ram_budget_mb: int       # Max RAM for AI
    desktop_mode: str        # lite, standard, full
    compositor_effects: bool # Blur, shadows, animations


class AdaptiveScaler:
    """Auto-scales AI configuration to match hardware."""
    
    def __init__(self):
        self.profile = self._detect_hardware()
        self.config = self._compute_config()
    
    def _detect_hardware(self) -> HardwareProfile:
        """Detect all hardware capabilities."""
        arch = platform.machine()
        
        # CPU
        cpu_cores = os.cpu_count() or 1
        cpu_name = self._get_cpu_name()
        
        # RAM
        ram_total_mb, ram_available_mb = self._get_ram()
        
        # GPU
        gpu_type, gpu_name, gpu_vram_mb = self._detect_gpu()
        
        # SIMD
        has_neon = arch == "aarch64"
        has_avx2 = self._check_avx2() if arch == "x86_64" else False
        
        # NPU
        has_npu = os.path.exists("/dev/accel/accel0") or os.path.exists("/dev/apex_0")
        
        # Storage
        storage_type = self._detect_storage()
        
        # Battery
        is_battery = os.path.exists("/sys/class/power_supply/BAT0")
        
        return HardwareProfile(
            arch=arch, cpu_cores=cpu_cores, cpu_name=cpu_name,
            ram_total_mb=ram_total_mb, ram_available_mb=ram_available_mb,
            gpu_type=gpu_type, gpu_name=gpu_name, gpu_vram_mb=gpu_vram_mb,
            has_neon=has_neon, has_avx2=has_avx2, has_npu=has_npu,
            storage_type=storage_type, is_battery=is_battery,
        )
    
    def _get_cpu_name(self) -> str:
        try:
            with open("/proc/cpuinfo") as f:
                for line in f:
                    if line.startswith("model name") or line.startswith("Model"):
                        return line.split(":")[1].strip()
        except:
            pass
        return platform.processor() or "Unknown CPU"
    
    def _get_ram(self) -> tuple:
        try:
            with open("/proc/meminfo") as f:
                content = f.read()
            total = int([l for l in content.split("\n") if "MemTotal" in l][0].split()[1]) // 1024
            avail = int([l for l in content.split("\n") if "MemAvailable" in l][0].split()[1]) // 1024
            return total, avail
        except:
            return 1024, 512
    
    def _detect_gpu(self) -> tuple:
        # NVIDIA
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                parts = result.stdout.strip().split(", ")
                return "nvidia", parts[0], int(parts[1])
        except:
            pass
        
        # Check DRM for embedded GPUs
        try:
            drm_path = "/sys/class/drm/card0/device"
            if os.path.exists(drm_path):
                vendor = open(f"{drm_path}/vendor").read().strip() if os.path.exists(f"{drm_path}/vendor") else ""
                if vendor == "0x8086":
                    return "intel", "Intel Integrated", 0
                elif vendor == "0x1002":
                    return "amd", "AMD GPU", 0
        except:
            pass
        
        # Raspberry Pi VideoCore
        try:
            result = subprocess.run(["vcgencmd", "get_mem", "gpu"], capture_output=True, text=True, timeout=2)
            if result.returncode == 0:
                mem = result.stdout.strip().split("=")[1].replace("M", "")
                return "videocore", "Broadcom VideoCore", int(mem)
        except:
            pass
        
        # Apple Silicon
        if platform.machine() == "aarch64" and os.path.exists("/sys/module/asahi"):
            return "apple", "Apple Silicon GPU", 0  # Shared memory
        
        return "none", "No GPU", 0
    
    def _check_avx2(self) -> bool:
        try:
            with open("/proc/cpuinfo") as f:
                return "avx2" in f.read()
        except:
            return False
    
    def _detect_storage(self) -> str:
        if os.path.exists("/sys/block/nvme0n1"):
            return "nvme"
        if os.path.exists("/sys/block/mmcblk0"):
            return "sdcard"
        try:
            rot = open("/sys/block/sda/queue/rotational").read().strip()
            return "hdd" if rot == "1" else "ssd"
        except:
            return "unknown"
    
    def _compute_config(self) -> AIConfig:
        """Determine the optimal AI configuration for this hardware."""
        ram = self.profile.ram_total_mb
        cores = self.profile.cpu_cores
        gpu_vram = self.profile.gpu_vram_mb
        
        # ── Tier: Nano (512MB - 1GB RAM) ──────────────────────────
        if ram < 1500:
            return AIConfig(
                tier="nano",
                model_id="thakran-nano",
                model_file="thakran-nano-150m-q4.onnx",
                model_size_mb=50,
                backend="onnx",           # ONNX is lighter than llama.cpp
                cpu_threads=max(1, cores - 1),
                gpu_layers=0,
                context_length=256,
                batch_size=1,
                use_mmap=True,            # Don't load entire model into RAM
                use_mlock=False,
                quantization="Q4_0",
                ram_budget_mb=min(256, ram // 3),
                desktop_mode="lite",
                compositor_effects=False,  # No blur/shadows on low RAM
            )
        
        # ── Tier: Lite (2-4GB RAM) ────────────────────────────────
        elif ram < 5000:
            return AIConfig(
                tier="lite",
                model_id="thakran-tiny",
                model_file="thakran-tiny-1b-q2_k.gguf",
                model_size_mb=700,
                backend="cpu",
                cpu_threads=max(2, cores - 1),
                gpu_layers=0,
                context_length=1024,
                batch_size=4,
                use_mmap=True,
                use_mlock=False,
                quantization="Q2_K",
                ram_budget_mb=min(1024, ram // 3),
                desktop_mode="standard",
                compositor_effects=ram >= 3000,
            )
        
        # ── Tier: Standard (8-16GB RAM) ───────────────────────────
        elif ram < 24000:
            gpu_layers_count = 0
            backend = "cpu"
            
            if self.profile.gpu_type == "nvidia" and gpu_vram >= 4000:
                backend = "cuda"
                gpu_layers_count = 32
            elif self.profile.gpu_type == "amd" and gpu_vram >= 4000:
                backend = "rocm"
                gpu_layers_count = 32
            elif self.profile.gpu_type in ("apple",):
                backend = "metal"
                gpu_layers_count = 32
            
            return AIConfig(
                tier="standard",
                model_id="thakran-standard",
                model_file="thakran-standard-7b-q4_k_m.gguf",
                model_size_mb=4500,
                backend=backend,
                cpu_threads=max(4, cores - 2),
                gpu_layers=gpu_layers_count,
                context_length=4096,
                batch_size=16,
                use_mmap=True,
                use_mlock=True,
                quantization="Q4_K_M",
                ram_budget_mb=min(6000, ram // 2),
                desktop_mode="full",
                compositor_effects=True,
            )
        
        # ── Tier: Ultra (32GB+ RAM) ───────────────────────────────
        else:
            gpu_layers_count = 0
            backend = "cpu"
            model_id = "thakran-pro"
            model_file = "thakran-pro-13b-q6_k.gguf"
            model_size_mb = 8000
            quantization = "Q6_K"
            
            if self.profile.gpu_type == "nvidia":
                backend = "cuda"
                gpu_layers_count = 48
                if gpu_vram >= 16000:
                    model_id = "thakran-ultra"
                    model_file = "thakran-ultra-34b-q4_k_m.gguf"
                    model_size_mb = 20000
                    quantization = "Q4_K_M"
            elif self.profile.gpu_type == "amd":
                backend = "rocm"
                gpu_layers_count = 48
            elif self.profile.gpu_type == "apple":
                backend = "metal"
                gpu_layers_count = 48
            
            return AIConfig(
                tier="ultra",
                model_id=model_id,
                model_file=model_file,
                model_size_mb=model_size_mb,
                backend=backend,
                cpu_threads=max(8, cores - 4),
                gpu_layers=gpu_layers_count,
                context_length=8192,
                batch_size=32,
                use_mmap=True,
                use_mlock=True,
                quantization=quantization,
                ram_budget_mb=min(16000, ram // 2),
                desktop_mode="full",
                compositor_effects=True,
            )
    
    def generate_config_file(self) -> dict:
        """Generate the runtime config for thakran-aid."""
        return {
            "tier": self.config.tier,
            "hardware": {
                "arch": self.profile.arch,
                "cpu": {
                    "name": self.profile.cpu_name,
                    "cores": self.profile.cpu_cores,
                    "avx2": self.profile.has_avx2,
                    "neon": self.profile.has_neon,
                },
                "ram_total_mb": self.profile.ram_total_mb,
                "gpu": {
                    "type": self.profile.gpu_type,
                    "name": self.profile.gpu_name,
                    "vram_mb": self.profile.gpu_vram_mb,
                },
                "npu": self.profile.has_npu,
                "storage": self.profile.storage_type,
                "is_laptop": self.profile.is_battery,
            },
            "ai": {
                "model": self.config.model_id,
                "model_file": self.config.model_file,
                "model_size_mb": self.config.model_size_mb,
                "backend": self.config.backend,
                "cpu_threads": self.config.cpu_threads,
                "gpu_layers": self.config.gpu_layers,
                "context_length": self.config.context_length,
                "batch_size": self.config.batch_size,
                "use_mmap": self.config.use_mmap,
                "use_mlock": self.config.use_mlock,
                "quantization": self.config.quantization,
                "ram_budget_mb": self.config.ram_budget_mb,
            },
            "desktop": {
                "mode": self.config.desktop_mode,
                "compositor_effects": self.config.compositor_effects,
                "blur": self.config.compositor_effects,
                "shadows": self.config.compositor_effects,
                "animations": self.config.compositor_effects,
                "corner_radius": 12 if self.config.compositor_effects else 0,
            },
        }
    
    def print_summary(self):
        """Print a human-readable summary."""
        tier_emoji = {"nano": "🌱", "lite": "🌿", "standard": "🌳", "ultra": "🏔️"}
        
        print(f"\n╔══════════════════════════════════════════════════════════╗")
        print(f"║  {tier_emoji.get(self.config.tier, '?')} Thakran OS — Performance Tier: {self.config.tier.upper():>10}  ║")
        print(f"╠══════════════════════════════════════════════════════════╣")
        print(f"║  CPU: {self.profile.cpu_name[:45]:<46}║")
        print(f"║  RAM: {self.profile.ram_total_mb:,} MB ({self.profile.ram_available_mb:,} MB available)         ║")
        print(f"║  GPU: {self.profile.gpu_name[:45]:<46}║")
        print(f"║  Arch: {self.profile.arch:<44}  ║")
        print(f"╠══════════════════════════════════════════════════════════╣")
        print(f"║  AI Model: {self.config.model_id:<40}  ║")
        print(f"║  Backend: {self.config.backend:<41}  ║")
        print(f"║  Context: {self.config.context_length} tokens                              ║")
        print(f"║  GPU Layers: {self.config.gpu_layers:<38}  ║")
        print(f"║  Desktop: {self.config.desktop_mode:<32}        ║")
        print(f"╚══════════════════════════════════════════════════════════╝\n")


def main():
    """Run the scaler and output the config."""
    scaler = AdaptiveScaler()
    scaler.print_summary()
    
    config = scaler.generate_config_file()
    
    # Write config
    output_path = "/var/lib/thakran/hardware/adaptive-config.json"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, "w") as f:
        json.dump(config, f, indent=2)
    
    print(f"Config written to: {output_path}")


if __name__ == "__main__":
    main()
