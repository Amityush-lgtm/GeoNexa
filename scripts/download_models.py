"""
Model Downloader for Offline Operation.

Downloads and saves CLIP ViT-B/32 model weights and tokenizer/preprocessor
to the local `models/clip-vit-b-32` directory.

After running this script once with an internet connection, the system can operate
completely offline without internet access.
"""

import os
import sys
from pathlib import Path

# Setup paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TARGET_MODEL_DIR = PROJECT_ROOT / "models" / "clip-vit-b-32"


def download_clip_model(target_dir: Path):
    """Download CLIP model and processor to the target directory."""
    print(f"Target directory: {target_dir}")
    target_dir.mkdir(parents=True, exist_ok=True)

    try:
        from transformers import CLIPModel, CLIPProcessor

        model_id = "openai/clip-vit-base-patch32"
        print(f"Downloading HuggingFace CLIP model: {model_id}...")

        model = CLIPModel.from_pretrained(model_id)
        processor = CLIPProcessor.from_pretrained(model_id)

        print(f"Saving model and processor to {target_dir}...")
        model.save_pretrained(target_dir)
        processor.save_pretrained(target_dir)

        print(f"Model successfully saved to {target_dir}")
        print("System is now ready for 100% offline operation.")

    except ImportError:
        print(
            "Error: 'transformers' or 'torch' package not found.\n"
            "Please install requirements: pip install -r requirements.txt"
        )
        sys.exit(1)
    except Exception as e:
        print(f"Failed to download model: {e}")
        sys.exit(1)


if __name__ == "__main__":
    download_clip_model(TARGET_MODEL_DIR)
