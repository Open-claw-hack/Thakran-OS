#!/usr/bin/env python3
"""
============================================================================
Thakran OS — Hardware Profiler & Optimizer
============================================================================
Comprehensive hardware detection and AI inference optimization.

Detects:
  - CPU: model, cores, threads, instruction sets (AVX2, AVX512, AMX)
  - RAM: total, available, speed
  - GPU: NVIDIA (CUDA), AMD (ROCm), Intel (Arc/UHD)
  - NPU: Intel NPU, Qualcomm NPU, Google Coral
  - Storage: NVMe, SSD, HDD speeds

Outputs:
  - /var/lib/thakran/hardware/profile.json
  - /var/lib/thakran/hardware/optimization.json
  - Recommended AI model + inference settings
============================================================================
"""

import json
import os
import platform
import subprocess
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional


# ─── Constants ──────────────────────────────────────────────────────────────

OUTPUT_DIR = "/var/lib/thakran/hardware"
PROFILE_FILE = f"{OUTPUT_DIR}/profile.json"
OPTIMIZATION_FILE = f"{OUTPUT_DIR}/optimization.json"


# ─── Data Models ────────────────────────────────────────────────────────────

@dataclass
class CPUInfo:
    name: str = "Unknown"
    vendor: str = "Unknown"
    cores: int = 1
    threads: int = 1
    max_frequency_mhz: float = 0.0
    architecture: str = "x86_64"
    features: list = field(default_factory=list)
    cache_l3_mb: float = 0.0


@dataclass
class RAMInfo:
    total_gb: float = 0.0
    available_gb: float = 0.0
    speed_mhz: int = 0
    type_: str = "Unknown"  # DDR4, DDR5, etc.
    channels: int = 1


@dataclass
class GPUInfo:
    name: str = "None"
    vendor: str = "none"  # nvidia, amd, intel, none
    vram_gb: float = 0.0
    driver_version: str = "N/A"
    compute_capability: str = "N/A"
    cuda_cores: int = 0
    supports_fp16: bool = False
    supports_int8: bool = False


@dataclass
class NPUInfo:
    available: bool = False
    name: str = "None"
    vendor: str = "none"
    tops: float = 0.0  # Tera Operations Per Second


@dataclass
class StorageInfo:
    type_: str = "Unknown"  # nvme, ssd, hdd
    total_gb: float = 0.0
    available_gb: float = 0.0
    read_speed_mbps: float = 0.0


@dataclass
class HardwareProfile:
    cpu: CPUInfo = field(default_factory=CPUInfo)
    ram: RAMInfo = field(default_factory=RAMInfo)
    gpu: GPUInfo = field(default_factory=GPUInfo)
    npu: NPUInfo = field(default_factory=NPUInfo)
    storage: StorageInfo = field(default_factory=StorageInfo)
    os_info: dict = field(default_factory=dict)
    profiled_at: str = ""


@dataclass
class OptimizationProfile:
    """Recommended settings for AI inference on this hardware."""
    recommended_device: str = "cpu"
    recommended_model: str = "thakran-mini"
    recommended_quantization: str = "Q4_K_M"
    
    # Inference settings
    max_context_length: int = 2048
    batch_size: int = 8
    thread_count: int = 4
    gpu_layers: int = 0
    
    # Memory settings
    use_mmap: bool = True
    use_mlock: bool = False
    max_model_size_gb: float = 2.0
    
    # Performance flags
    use_flash_attention: bool = False
    use_fp16: bool = False
    use_int8: bool = False
    
    # Power profile
    power_mode: str = "balanced"  # performance, balanced, efficiency
    
    tier: str = "basic"  # basic, standard, performance, ultra


# ─── Profiler ──────────────────────────────────────────────────────────────

class Profiler:
    """Hardware detection and profiling engine."""

    def run(self) -> HardwareProfile:
        """Run full hardware profile."""
        print("🔍 Thakran Hardware Profiler")
        print("=" * 50)

        profile = HardwareProfile()
        profile.profiled_at = self._timestamp()
        profile.os_info = self._get_os_info()

        print("  Detecting CPU...")
        profile.cpu = self._detect_cpu()
        print(f"    ✓ {profile.cpu.name} ({profile.cpu.cores}C/{profile.cpu.threads}T)")

        print("  Detecting RAM...")
        profile.ram = self._detect_ram()
        print(f"    ✓ {profile.ram.total_gb}GB total, {profile.ram.available_gb}GB available")

        print("  Detecting GPU...")
        profile.gpu = self._detect_gpu()
        print(f"    ✓ {profile.gpu.name} ({profile.gpu.vram_gb}GB VRAM)")

        print("  Detecting NPU...")
        profile.npu = self._detect_npu()
        print(f"    ✓ {'Found: ' + profile.npu.name if profile.npu.available else 'None detected'}")

        print("  Detecting Storage...")
        profile.storage = self._detect_storage()
        print(f"    ✓ {profile.storage.type_}: {profile.storage.total_gb}GB")

        print("=" * 50)
        return profile

    def _detect_cpu(self) -> CPUInfo:
        info = CPUInfo()
        info.cores = os.cpu_count() or 1
        info.threads = info.cores
        info.architecture = platform.machine()

        if os.path.exists("/proc/cpuinfo"):
            with open("/proc/cpuinfo") as f:
                for line in f:
                    if line.startswith("model name"):
                        info.name = line.split(":")[1].strip()
                    elif line.startswith("vendor_id"):
                        info.vendor = line.split(":")[1].strip()
                    elif line.startswith("cpu MHz"):
                        info.max_frequency_mhz = float(line.split(":")[1].strip())
                    elif line.startswith("siblings"):
                        info.threads = int(line.split(":")[1].strip())
                    elif line.startswith("cache size"):
                        cache_str = line.split(":")[1].strip()
                        if "KB" in cache_str:
                            info.cache_l3_mb = int(cache_str.replace(" KB", "")) / 1024
                    elif line.startswith("flags"):
                        flags = line.split(":")[1].strip().split()
                        for feat in ["avx", "avx2", "avx512f", "amx_tile", "amx_int8", "amx_bf16", "sse4_2", "fma", "f16c"]:
                            if feat in flags:
                                info.features.append(feat.upper())
                        break  # Only need first CPU block

        return info

    def _detect_ram(self) -> RAMInfo:
        info = RAMInfo()

        if os.path.exists("/proc/meminfo"):
            with open("/proc/meminfo") as f:
                for line in f:
                    if "MemTotal" in line:
                        info.total_gb = round(int(line.split()[1]) / 1024 / 1024, 1)
                    elif "MemAvailable" in line:
                        info.available_gb = round(int(line.split()[1]) / 1024 / 1024, 1)

        # Try to get RAM speed/type from dmidecode
        try:
            result = subprocess.run(
                ["sudo", "dmidecode", "-t", "memory"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                for line in result.stdout.split("\n"):
                    if "Speed:" in line and "MHz" in line:
                        speed = line.split(":")[1].strip()
                        info.speed_mhz = int(speed.replace(" MHz", ""))
                    elif "Type:" in line and "DDR" in line:
                        info.type_ = line.split(":")[1].strip()
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        return info

    def _detect_gpu(self) -> GPUInfo:
        info = GPUInfo()

        # NVIDIA
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total,driver_version,compute_cap",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                parts = [p.strip() for p in result.stdout.strip().split(",")]
                info.name = parts[0]
                info.vram_gb = round(int(parts[1]) / 1024, 1)
                info.driver_version = parts[2]
                info.compute_capability = parts[3] if len(parts) > 3 else "N/A"
                info.vendor = "nvidia"
                info.supports_fp16 = True
                info.supports_int8 = True
                return info
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        # AMD
        try:
            result = subprocess.run(
                ["rocm-smi", "--showproductname"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                info.vendor = "amd"
                info.name = "AMD GPU (ROCm)"
                info.supports_fp16 = True
                return info
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        # Intel
        if os.path.exists("/sys/class/drm/card0/device/vendor"):
            with open("/sys/class/drm/card0/device/vendor") as f:
                if f.read().strip() == "0x8086":
                    info.vendor = "intel"
                    info.name = "Intel GPU"

        return info

    def _detect_npu(self) -> NPUInfo:
        info = NPUInfo()

        # Intel NPU (Meteor Lake, Arrow Lake, etc.)
        if os.path.exists("/dev/accel/accel0"):
            info.available = True
            info.vendor = "intel"
            info.name = "Intel AI Boost NPU"
            info.tops = 11.0  # Typical Intel NPU

        # Qualcomm NPU (for ARM devices)
        if os.path.exists("/dev/qcom-nsp"):
            info.available = True
            info.vendor = "qualcomm"
            info.name = "Qualcomm Hexagon NPU"
            info.tops = 45.0

        # Google Coral TPU
        if os.path.exists("/dev/apex_0"):
            info.available = True
            info.vendor = "google"
            info.name = "Google Coral Edge TPU"
            info.tops = 4.0

        return info

    def _detect_storage(self) -> StorageInfo:
        info = StorageInfo()

        try:
            result = subprocess.run(["df", "-BG", "/"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                lines = result.stdout.strip().split("\n")
                if len(lines) > 1:
                    parts = lines[1].split()
                    info.total_gb = float(parts[1].replace("G", ""))
                    info.available_gb = float(parts[3].replace("G", ""))
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        # Check if NVMe
        if os.path.exists("/sys/block/nvme0n1"):
            info.type_ = "nvme"
        elif os.path.exists("/sys/block/sda/queue/rotational"):
            with open("/sys/block/sda/queue/rotational") as f:
                info.type_ = "hdd" if f.read().strip() == "1" else "ssd"

        return info

    def _get_os_info(self) -> dict:
        return {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        }

    def _timestamp(self) -> str:
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()


# ─── Optimizer ──────────────────────────────────────────────────────────────

class Optimizer:
    """Generate optimized AI inference settings based on hardware profile."""

    def optimize(self, profile: HardwareProfile) -> OptimizationProfile:
        """Generate optimization profile from hardware profile."""
        opt = OptimizationProfile()

        # ─── Device Selection ───────────────────────────────────────
        if profile.gpu.vendor == "nvidia" and profile.gpu.vram_gb >= 4:
            opt.recommended_device = "cuda"
            opt.gpu_layers = -1  # All layers to GPU
            opt.use_fp16 = profile.gpu.supports_fp16
            opt.use_int8 = profile.gpu.supports_int8
            opt.use_flash_attention = True
        elif profile.gpu.vendor == "amd":
            opt.recommended_device = "rocm"
            opt.gpu_layers = -1
            opt.use_fp16 = profile.gpu.supports_fp16
        elif profile.npu.available:
            opt.recommended_device = "npu"
        elif profile.gpu.vendor == "intel":
            opt.recommended_device = "vulkan"
        else:
            opt.recommended_device = "cpu"

        # ─── Thread Count ───────────────────────────────────────────
        opt.thread_count = max(1, profile.cpu.threads - 2)

        # ─── Memory & Model Size ────────────────────────────────────
        if opt.recommended_device in ("cuda", "rocm"):
            available_vram = profile.gpu.vram_gb * 0.85
            available_ram = profile.ram.available_gb * 0.5
            opt.max_model_size_gb = max(available_vram, available_ram)
        else:
            opt.max_model_size_gb = profile.ram.available_gb * 0.5

        # ─── Model & Quantization Selection ─────────────────────────
        if opt.max_model_size_gb >= 12:
            opt.recommended_model = "thakran-pro"
            opt.recommended_quantization = "Q5_K_M"
            opt.tier = "ultra"
        elif opt.max_model_size_gb >= 6:
            opt.recommended_model = "thakran-standard"
            opt.recommended_quantization = "Q4_K_M"
            opt.tier = "performance"
        elif opt.max_model_size_gb >= 3:
            opt.recommended_model = "thakran-mini"
            opt.recommended_quantization = "Q4_K_M"
            opt.tier = "standard"
        else:
            opt.recommended_model = "thakran-tiny"
            opt.recommended_quantization = "Q4_0"
            opt.tier = "basic"

        # ─── Context Length ─────────────────────────────────────────
        if opt.tier == "ultra":
            opt.max_context_length = 8192
            opt.batch_size = 32
        elif opt.tier == "performance":
            opt.max_context_length = 4096
            opt.batch_size = 16
        elif opt.tier == "standard":
            opt.max_context_length = 2048
            opt.batch_size = 8
        else:
            opt.max_context_length = 1024
            opt.batch_size = 4

        # ─── Memory Mapping ────────────────────────────────────────
        opt.use_mmap = True
        opt.use_mlock = profile.ram.available_gb > opt.max_model_size_gb * 2

        # ─── Power Mode ────────────────────────────────────────────
        # Check if on battery (laptop)
        if os.path.exists("/sys/class/power_supply/BAT0"):
            with open("/sys/class/power_supply/BAT0/status") as f:
                if f.read().strip() == "Discharging":
                    opt.power_mode = "efficiency"
                else:
                    opt.power_mode = "balanced"
        else:
            opt.power_mode = "performance"

        return opt


# ─── Main ──────────────────────────────────────────────────────────────────

def main():
    """Run hardware profiler and generate optimization settings."""
    profiler = Profiler()
    optimizer = Optimizer()

    # Profile hardware
    hw_profile = profiler.run()

    # Generate optimizations
    print("\n⚡ Generating AI optimization profile...")
    opt_profile = optimizer.optimize(hw_profile)

    # Save results
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    with open(PROFILE_FILE, "w") as f:
        json.dump(asdict(hw_profile), f, indent=2, default=str)
    print(f"  ✓ Hardware profile saved: {PROFILE_FILE}")

    with open(OPTIMIZATION_FILE, "w") as f:
        json.dump(asdict(opt_profile), f, indent=2, default=str)
    print(f"  ✓ Optimization profile saved: {OPTIMIZATION_FILE}")

    # Summary
    print(f"\n{'=' * 50}")
    print(f"  📊 Optimization Summary")
    print(f"{'=' * 50}")
    print(f"  Device:          {opt_profile.recommended_device}")
    print(f"  Model:           {opt_profile.recommended_model}")
    print(f"  Quantization:    {opt_profile.recommended_quantization}")
    print(f"  Context Length:  {opt_profile.max_context_length}")
    print(f"  Threads:         {opt_profile.thread_count}")
    print(f"  GPU Layers:      {opt_profile.gpu_layers}")
    print(f"  Max Model Size:  {opt_profile.max_model_size_gb:.1f}GB")
    print(f"  Tier:            {opt_profile.tier.upper()}")
    print(f"  Power Mode:      {opt_profile.power_mode}")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    main()
