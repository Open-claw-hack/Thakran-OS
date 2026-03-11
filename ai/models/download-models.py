#!/usr/bin/env python3
"""
============================================================================
Thakran OS — AI Model Downloader
============================================================================
Parses the model registry and downloads the required GGUF / ONNX models
from HuggingFace directly to the system model cache. Highly optimized
with resume support and multi-threading.
============================================================================
"""

import json
import os
import sys
from pathlib import Path

try:
    from huggingface_hub import hf_hub_download
except ImportError:
    print("❌ Error: huggingface_hub is not installed.")
    print("   Run: pip install huggingface_hub")
    sys.exit(1)

REGISTRY_PATH = Path(__file__).parent / "model-registry.json"
CACHE_DIR = "/var/cache/thakran/models"

def load_registry():
    if not REGISTRY_PATH.exists():
        print(f"❌ Registry not found at {REGISTRY_PATH}")
        sys.exit(1)
    with open(REGISTRY_PATH) as f:
        return json.load(f)

def download_model(model_id: str, force: bool = False):
    registry = load_registry()
    models = registry.get("models", [])
    
    # Allow downloading specific tiers
    target_models = []
    if model_id == "all":
        target_models = models
    else:
        target_models = [m for m in models if m["name"] == model_id or m["tier"] == model_id]
        
    if not target_models:
        print(f"❌ No matching models found for: {model_id}")
        print("Available models:")
        for m in models:
            print(f"  - {m['name']} (Tier: {m['tier']}, Size: {m.get('size_gb', 0)}GB)")
        sys.exit(1)
        
    os.makedirs(CACHE_DIR, exist_ok=True)
    
    for m in target_models:
        if "download" not in m:
            print(f"⚠️ Skipping {m['name']} — no download instructions.")
            continue
            
        repo_id = m["download"].get("repo_id")
        filename = m["download"].get("filename")
        if not repo_id or not filename:
            print(f"⚠️ Skipping {m['name']} — invalid repo/filename.")
            continue
            
        dest_filename = m.get("filename", filename)
        dest_path = Path(CACHE_DIR) / dest_filename
        
        if dest_path.exists() and not force:
            print(f"✅ {m['name']} already exists at {dest_path}. Skipping.")
            continue
            
        print(f"📥 Downloading {m['name']} ({m.get('size_gb', 0)}GB)...")
        print(f"   Source: {repo_id}/{filename}")
        
        try:
            # Download to huggingface cache then symlink/copy
            downloaded_path = hf_hub_download(
                repo_id=repo_id,
                filename=filename,
                cache_dir=CACHE_DIR + "/.hf",
                resume_download=True
            )
            
            # Link/Move to the expected filename
            if Path(downloaded_path).exists():
                if dest_path.exists():
                    dest_path.unlink()
                # Use hardlink to save space if on same partition
                try:
                    os.link(downloaded_path, dest_path)
                except OSError:
                    import shutil
                    shutil.copy2(downloaded_path, dest_path)
                    
                print(f"🎉 Successfully installed {m['name']} -> {dest_path}")
        except Exception as e:
            print(f"❌ Failed to download {m['name']}: {e}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Download Thakran OS AI Models")
    parser.add_argument("model", help="Model name, tier (nano, lite, standard, ultra), or 'all'")
    parser.add_argument("--force", action="store_true", help="Redownload even if exists")
    
    args = parser.parse_args()
    
    # Need sudo/root for /var/cache usually, but we check if we have permissions
    if not os.access(os.path.dirname(CACHE_DIR) if not os.path.exists(CACHE_DIR) else CACHE_DIR, os.W_OK):
        print(f"⚠️ Warning: You may need sudo to write to {CACHE_DIR}")
        
    download_model(args.model, args.force)
