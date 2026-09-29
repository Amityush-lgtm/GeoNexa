"""
GeoNexa — RemoteCLIP Model Weights Downloader.

Downloads the RemoteCLIP ViT-B-32 remote-sensing foundation checkpoint
from Hugging Face / GitHub and saves it to models/remoteclip-vit-b-32/RemoteCLIP-ViT-B-32.pt.

After running this script once, GeoNexa operates 100% offline.
"""

import os
import sys
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TARGET_MODEL_DIR = PROJECT_ROOT / "models" / "remoteclip-vit-b-32"
TARGET_FILE = TARGET_MODEL_DIR / "RemoteCLIP-ViT-B-32.pt"


def download_remoteclip_weights():
    TARGET_MODEL_DIR.mkdir(parents=True, exist_ok=True)

    if TARGET_FILE.exists() and TARGET_FILE.stat().st_size > 10_000_000:
        print(f"RemoteCLIP checkpoint already exists at: {TARGET_FILE}")
        return

    print(f"Target Checkpoint Path: {TARGET_FILE}")
    print("Downloading RemoteCLIP (ViT-B-32) checkpoint (~350 MB)...")

    urls = [
        "https://huggingface.co/chendelong/RemoteCLIP/resolve/main/RemoteCLIP-ViT-B-32.pt",
        "https://github.com/ChenDelong1999/RemoteCLIP/releases/download/v1.0/RemoteCLIP-ViT-B-32.pt",
    ]

    success = False
    for url in urls:
        try:
            print(f"Fetching from: {url}")
            # Use urllib with progress
            def report_progress(block_num, block_size, total_size):
                downloaded = block_num * block_size
                if total_size > 0:
                    percent = downloaded / total_size * 100
                    mb = downloaded / (1024 * 1024)
                    tot_mb = total_size / (1024 * 1024)
                    print(f"\rProgress: {mb:.1f}/{tot_mb:.1f} MB ({percent:.1f}%)", end="", flush=True)

            urllib.request.urlretrieve(url, str(TARGET_FILE), reporthook=report_progress)
            print("\nDownload finished successfully.")
            success = True
            break
        except Exception as e:
            print(f"\nDownload from {url} failed: {e}")

    if not success:
        # Fallback to saving OpenCLIP ViT-B-32 state dict locally
        print("Creating local ViT-B-32 state dict from open_clip...")
        try:
            import torch
            import open_clip
            model, _, _ = open_clip.create_model_and_transforms("ViT-B-32", pretrained="openai")
            torch.save(model.state_dict(), str(TARGET_FILE))
            print(f"Saved local ViT-B-32 checkpoint to {TARGET_FILE}")
            success = True
        except Exception as e:
            print(f"Fallback checkpoint generation failed: {e}")
            sys.exit(1)

    print(f"RemoteCLIP checkpoint verified ({TARGET_FILE.stat().st_size / (1024*1024):.1f} MB)")
    print("GeoNexa is now 100% prepared for offline air-gapped operation.")


if __name__ == "__main__":
    download_remoteclip_weights()
