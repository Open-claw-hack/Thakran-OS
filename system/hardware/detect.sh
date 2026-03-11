#!/bin/bash
# ============================================================================
# Thakran OS — Hardware Detection Script
# ============================================================================
# Detects all hardware components and writes a machine profile.
# Called by the hardware profiler systemd service at boot.
# ============================================================================

set -euo pipefail

OUTPUT_DIR="/var/lib/thakran/hardware"
PROFILE_FILE="${OUTPUT_DIR}/detected-hardware.json"

mkdir -p "$OUTPUT_DIR"

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║          🔍 Thakran OS Hardware Detection                   ║"
echo "╚══════════════════════════════════════════════════════════════╝"

# ─── CPU ────────────────────────────────────────────────────────────────────
echo "  → Detecting CPU..."
CPU_NAME=$(grep -m1 "model name" /proc/cpuinfo 2>/dev/null | cut -d: -f2 | xargs || echo "Unknown")
CPU_CORES=$(nproc 2>/dev/null || echo 1)
CPU_ARCH=$(uname -m)
HAS_AVX2=$(grep -q avx2 /proc/cpuinfo 2>/dev/null && echo "true" || echo "false")
HAS_AVX512=$(grep -q avx512f /proc/cpuinfo 2>/dev/null && echo "true" || echo "false")

# ─── RAM ────────────────────────────────────────────────────────────────────
echo "  → Detecting RAM..."
RAM_TOTAL_KB=$(grep MemTotal /proc/meminfo 2>/dev/null | awk '{print $2}' || echo 0)
RAM_TOTAL_GB=$(echo "scale=1; $RAM_TOTAL_KB / 1024 / 1024" | bc 2>/dev/null || echo 0)
RAM_AVAIL_KB=$(grep MemAvailable /proc/meminfo 2>/dev/null | awk '{print $2}' || echo 0)
RAM_AVAIL_GB=$(echo "scale=1; $RAM_AVAIL_KB / 1024 / 1024" | bc 2>/dev/null || echo 0)

# ─── GPU ────────────────────────────────────────────────────────────────────
echo "  → Detecting GPU..."
GPU_TYPE="none"
GPU_NAME="None"
GPU_VRAM="0"

# NVIDIA
if command -v nvidia-smi &>/dev/null; then
    GPU_TYPE="nvidia"
    GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1 || echo "NVIDIA GPU")
    GPU_VRAM=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits 2>/dev/null | head -1 || echo 0)
# AMD
elif command -v rocm-smi &>/dev/null; then
    GPU_TYPE="amd"
    GPU_NAME="AMD GPU (ROCm)"
# Intel
elif [ -f /sys/class/drm/card0/device/vendor ]; then
    VENDOR=$(cat /sys/class/drm/card0/device/vendor 2>/dev/null || echo "")
    if [ "$VENDOR" = "0x8086" ]; then
        GPU_TYPE="intel"
        GPU_NAME="Intel GPU"
    fi
fi

# ─── NPU ────────────────────────────────────────────────────────────────────
echo "  → Detecting NPU/AI Accelerator..."
NPU_AVAILABLE="false"
NPU_NAME="None"

if [ -e /dev/accel/accel0 ]; then
    NPU_AVAILABLE="true"
    NPU_NAME="Intel NPU"
elif [ -e /dev/apex_0 ]; then
    NPU_AVAILABLE="true"
    NPU_NAME="Google Coral TPU"
fi

# ─── Storage ────────────────────────────────────────────────────────────────
echo "  → Detecting Storage..."
STORAGE_TYPE="unknown"
if [ -e /sys/block/nvme0n1 ]; then
    STORAGE_TYPE="nvme"
elif [ -f /sys/block/sda/queue/rotational ]; then
    ROT=$(cat /sys/block/sda/queue/rotational 2>/dev/null || echo "1")
    [ "$ROT" = "0" ] && STORAGE_TYPE="ssd" || STORAGE_TYPE="hdd"
fi

ROOT_TOTAL=$(df -BG / 2>/dev/null | tail -1 | awk '{print $2}' | tr -d 'G' || echo 0)
ROOT_AVAIL=$(df -BG / 2>/dev/null | tail -1 | awk '{print $4}' | tr -d 'G' || echo 0)

# ─── Battery ────────────────────────────────────────────────────────────────
echo "  → Detecting Power Source..."
IS_LAPTOP="false"
BATTERY_PERCENT="N/A"

if [ -d /sys/class/power_supply/BAT0 ]; then
    IS_LAPTOP="true"
    BATTERY_PERCENT=$(cat /sys/class/power_supply/BAT0/capacity 2>/dev/null || echo "N/A")
fi

# ─── Write Profile ─────────────────────────────────────────────────────────
echo "  → Writing hardware profile..."

cat > "$PROFILE_FILE" << EOF
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "cpu": {
    "name": "${CPU_NAME}",
    "cores": ${CPU_CORES},
    "architecture": "${CPU_ARCH}",
    "avx2": ${HAS_AVX2},
    "avx512": ${HAS_AVX512}
  },
  "ram": {
    "total_gb": ${RAM_TOTAL_GB},
    "available_gb": ${RAM_AVAIL_GB}
  },
  "gpu": {
    "type": "${GPU_TYPE}",
    "name": "${GPU_NAME}",
    "vram_mb": ${GPU_VRAM}
  },
  "npu": {
    "available": ${NPU_AVAILABLE},
    "name": "${NPU_NAME}"
  },
  "storage": {
    "type": "${STORAGE_TYPE}",
    "total_gb": ${ROOT_TOTAL},
    "available_gb": ${ROOT_AVAIL}
  },
  "power": {
    "is_laptop": ${IS_LAPTOP},
    "battery_percent": "${BATTERY_PERCENT}"
  }
}
EOF

echo ""
echo "  ✓ Hardware detection complete: ${PROFILE_FILE}"
echo "  ✓ CPU: ${CPU_NAME} (${CPU_CORES} cores)"
echo "  ✓ RAM: ${RAM_TOTAL_GB}GB"
echo "  ✓ GPU: ${GPU_NAME} (${GPU_TYPE})"
echo "  ✓ NPU: ${NPU_NAME}"
echo "  ✓ Storage: ${STORAGE_TYPE} (${ROOT_TOTAL}GB)"
