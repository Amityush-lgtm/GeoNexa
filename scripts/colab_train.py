"""
╔═══════════════════════════════════════════════════════════════════════╗
║                    GeoNexa — Colab Training Script                   ║
║                                                                      ║
║  Fine-tune RemoteCLIP ViT-B-32 on Google Colab with a T4 GPU        ║
║                                                                      ║
║  Instructions:                                                       ║
║  1. Upload this entire `semantic-eo-search` project to Google Drive  ║
║  2. Open a Colab notebook with T4 GPU runtime                        ║
║  3. Mount Google Drive                                                ║
║  4. Run this script:                                                  ║
║     !python /content/drive/MyDrive/semantic-eo-search/scripts/colab_train.py ║
║                                                                      ║
║  OR copy the Colab cell commands below into notebook cells.           ║
╚═══════════════════════════════════════════════════════════════════════╝

=== COLAB NOTEBOOK CELLS ===

# Cell 1: Mount Drive & Install Dependencies
'''
from google.colab import drive
drive.mount('/content/drive')

# Navigate to project
import os
PROJECT_DIR = '/content/drive/MyDrive/semantic-eo-search'
os.chdir(PROJECT_DIR)

# Install dependencies
!pip install -q open-clip-torch faiss-cpu rasterio scipy pillow torch torchvision
'''

# Cell 2: Prepare Training Data
'''
!python scripts/prepare_training_data.py \\
    --tiles-dir data/public/tiles \\
    --output training_data/ \\
    --captions-per-tile 8
'''

# Cell 3: Fine-Tune RemoteCLIP
'''
!python scripts/colab_train.py
'''

# Cell 4: Export & Download
'''
!python scripts/export_finetuned_model.py \\
    --checkpoint checkpoints/best_model.pt \\
    --output models/remoteclip-vit-b-32-finetuned/RemoteCLIP-ViT-B-32.pt \\
    --verify

# Download the fine-tuned model
from google.colab import files
files.download('models/remoteclip-vit-b-32-finetuned/RemoteCLIP-ViT-B-32.pt')
'''

=== END COLAB CELLS ===
"""

import json
import logging
import os
import sys
import time
from pathlib import Path

# ── Detect environment ─────────────────────────────────────────────────
IN_COLAB = "google.colab" in sys.modules or os.environ.get("COLAB_GPU", "")
PROJECT_ROOT = Path(__file__).resolve().parent.parent

if IN_COLAB:
    # In Colab, project may be in /content/drive/MyDrive/
    possible_roots = [
        Path("/content/drive/MyDrive/semantic-eo-search"),
        Path("/content/drive/MyDrive/GeoNexa/semantic-eo-search"),
        Path("/content/semantic-eo-search"),
        PROJECT_ROOT,
    ]
    for root in possible_roots:
        if root.exists() and (root / "training").exists():
            PROJECT_ROOT = root
            break

sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def check_gpu():
    """Check GPU availability and print info."""
    import torch
    logger.info("═══════════════════════════════════════════════")
    logger.info("  GeoNexa Colab Training Environment Check")
    logger.info("═══════════════════════════════════════════════")
    logger.info(f"  PyTorch version: {torch.__version__}")
    logger.info(f"  CUDA available: {torch.cuda.is_available()}")

    if torch.cuda.is_available():
        logger.info(f"  GPU: {torch.cuda.get_device_name(0)}")
        logger.info(f"  GPU Memory: {torch.cuda.get_device_properties(0).total_mem / 1e9:.1f} GB")
        device = "cuda"
    else:
        logger.warning("  No GPU detected! Training will be very slow on CPU.")
        device = "cpu"

    return device


def step1_prepare_data():
    """Generate training data from tiles."""
    logger.info("\n" + "="*60)
    logger.info("  STEP 1: Preparing Training Data")
    logger.info("="*60)

    tiles_dir = PROJECT_ROOT / "data" / "public" / "tiles"
    output_dir = PROJECT_ROOT / "training_data"

    if not tiles_dir.exists():
        logger.error(f"Tiles directory not found: {tiles_dir}")
        logger.error("Please ensure the project data is accessible.")
        return False

    from training.caption_generator import generate_training_pairs_from_tiles
    from scripts.prepare_training_data import prepare_training_data

    prepare_training_data(
        tiles_dir=tiles_dir,
        output_dir=output_dir,
        captions_per_tile=8,
        val_split=0.15,
        seed=42,
    )

    # Verify
    train_path = output_dir / "train_pairs.json"
    val_path = output_dir / "val_pairs.json"

    if train_path.exists() and val_path.exists():
        with open(train_path) as f:
            train_data = json.load(f)
        with open(val_path) as f:
            val_data = json.load(f)
        logger.info(f"  ✓ Train pairs: {len(train_data['pairs'])}")
        logger.info(f"  ✓ Val pairs: {len(val_data['pairs'])}")
        return True
    else:
        logger.error("  ✗ Failed to generate training data")
        return False


def step2_train(device: str):
    """Run the fine-tuning training loop."""
    logger.info("\n" + "="*60)
    logger.info("  STEP 2: Fine-Tuning RemoteCLIP")
    logger.info("="*60)

    from training.config import TrainingConfig
    from training.train import RemoteCLIPTrainer

    # Check for pretrained checkpoint
    checkpoint = PROJECT_ROOT / "models" / "remoteclip-vit-b-32" / "RemoteCLIP-ViT-B-32.pt"
    if not checkpoint.exists():
        logger.warning(f"RemoteCLIP checkpoint not found at {checkpoint}")
        logger.info("Will use OpenAI CLIP pretrained weights as fallback")
        checkpoint_str = ""
    else:
        checkpoint_str = str(checkpoint)
        logger.info(f"Using pretrained checkpoint: {checkpoint}")

    # Configure training
    config = TrainingConfig(
        # Model
        model_arch="ViT-B-32",
        pretrained_checkpoint=checkpoint_str,
        output_dir=str(PROJECT_ROOT / "checkpoints"),

        # Data
        train_pairs_json=str(PROJECT_ROOT / "training_data" / "train_pairs.json"),
        val_pairs_json=str(PROJECT_ROOT / "training_data" / "val_pairs.json"),

        # Training hyperparameters — optimized for Colab T4
        epochs=30 if device == "cuda" else 5,       # Fewer epochs on CPU
        batch_size=64 if device == "cuda" else 8,     # Smaller batch on CPU
        learning_rate=1e-5,
        weight_decay=0.01,
        warmup_epochs=3,
        min_lr=1e-7,

        # Loss
        temperature=0.07,
        label_smoothing=0.1,

        # Strategy
        freeze_image_encoder=False,
        freeze_text_encoder=True,
        unfreeze_layers=4,
        gradient_accumulation_steps=1 if device == "cuda" else 4,

        # Augmentation
        use_augmentation=True,

        # Evaluation
        eval_every_n_epochs=5,
        save_every_n_epochs=5,

        # Hardware
        device=device,
        mixed_precision=(device == "cuda"),
        num_workers=2 if device == "cuda" else 0,
        pin_memory=(device == "cuda"),

        # Logging
        log_every_n_steps=5,
        experiment_name="geonexa_remoteclip_colab",
    )

    trainer = RemoteCLIPTrainer(config)
    trainer.train()

    return True


def step3_export():
    """Export the best model for deployment."""
    logger.info("\n" + "="*60)
    logger.info("  STEP 3: Exporting Fine-Tuned Model")
    logger.info("="*60)

    best_checkpoint = PROJECT_ROOT / "checkpoints" / "best_model.pt"
    final_checkpoint = PROJECT_ROOT / "checkpoints" / "final_model.pt"

    # Use best if available, otherwise final
    if best_checkpoint.exists():
        source = best_checkpoint
    elif final_checkpoint.exists():
        source = final_checkpoint
    else:
        logger.error("No checkpoint found! Training may have failed.")
        return False

    from scripts.export_finetuned_model import export_checkpoint, verify_exported_model

    output_path = str(
        PROJECT_ROOT / "models" / "remoteclip-vit-b-32-finetuned" / "RemoteCLIP-ViT-B-32.pt"
    )

    export_checkpoint(
        checkpoint_path=str(source),
        output_path=output_path,
    )

    success = verify_exported_model(output_path)

    if success:
        logger.info("\n  ════════════════════════════════════════════")
        logger.info("  ✓ Fine-tuned model exported successfully!")
        logger.info(f"  ✓ Location: {output_path}")
        logger.info("  ")
        logger.info("  Next steps:")
        logger.info("  1. Download the model from Colab")
        logger.info("  2. Place it in: models/remoteclip-vit-b-32-finetuned/")
        logger.info("  3. Update .env: MODEL_PATH=models/remoteclip-vit-b-32-finetuned")
        logger.info("  4. Rebuild index: python scripts/build_index.py --force-rebuild")
        logger.info("  5. Restart backend: uvicorn app.main:app --reload")
        logger.info("  ════════════════════════════════════════════")

    return success


def main():
    """Run the complete Colab training pipeline."""
    start_time = time.time()

    logger.info("╔═══════════════════════════════════════════════════════╗")
    logger.info("║       GeoNexa — RemoteCLIP Fine-Tuning Pipeline      ║")
    logger.info("║       Contrastive Learning for EO Retrieval           ║")
    logger.info("╠═══════════════════════════════════════════════════════╣")
    logger.info(f"║  Project: {PROJECT_ROOT}")
    logger.info(f"║  Colab: {IN_COLAB}")
    logger.info("╚═══════════════════════════════════════════════════════╝")

    # Check GPU
    device = check_gpu()

    # Step 1: Prepare data
    if not step1_prepare_data():
        logger.error("Data preparation failed. Aborting.")
        return

    # Step 2: Train
    if not step2_train(device):
        logger.error("Training failed. Aborting.")
        return

    # Step 3: Export
    step3_export()

    total_time = time.time() - start_time
    logger.info(f"\nTotal pipeline time: {total_time / 60:.1f} minutes")


if __name__ == "__main__":
    main()
