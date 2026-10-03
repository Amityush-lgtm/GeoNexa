"""
GeoNexa — 1-Click Local GPU / Colab Fine-Tuning Runner.

Usage:
    python scripts/train_local_gpu.py --epochs 20 --batch-size 32
"""

import sys
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

def main():
    import argparse
    parser = argparse.ArgumentParser(description="GeoNexa 1-Click Fine-Tuner")
    parser.add_argument("--epochs", type=int, default=20, help="Number of epochs (default: 20)")
    parser.add_argument("--batch-size", type=int, default=32, help="Batch size (default: 32)")
    parser.add_argument("--lr", type=float, default=2e-5, help="Learning rate (default: 2e-5)")
    args = parser.parse_args()

    print("=" * 60)
    print("🛰️ GeoNexa — Starting All-Domain Multi-Spectral Fine-Tuning")
    print(f"   Epochs: {args.epochs} | Batch size: {args.batch_size} | LR: {args.lr}")
    print("=" * 60)

    # Step 1: Generate all-domain training dataset
    print("\n[Step 1/3] Generating 4,100+ domain contrastive training pairs...")
    subprocess.run([sys.executable, str(PROJECT_ROOT / "scripts" / "generate_all_queries_dataset.py")], check=True)

    # Step 2: Run training
    print(f"\n[Step 2/3] Training RemoteCLIP ViT-B-32 on GPU for {args.epochs} epochs...")
    train_cmd = [
        sys.executable, "-m", "training.train",
        "--train-data", str(PROJECT_ROOT / "training_data" / "train_pairs.json"),
        "--val-data", str(PROJECT_ROOT / "training_data" / "val_pairs.json"),
        "--checkpoint", str(PROJECT_ROOT / "models" / "RemoteCLIP-ViT-B-32-finetuned.pt"),
        "--output-dir", str(PROJECT_ROOT / "checkpoints"),
        "--epochs", str(args.epochs),
        "--batch-size", str(args.batch_size),
        "--lr", str(args.lr),
        "--device", "cuda",
        "--num-workers", "0",
        "--eval-every", "2",
        "--save-every", "2"
    ]
    subprocess.run(train_cmd, check=True)

    # Step 3: Deploy & Re-index
    print("\n[Step 3/3] Deploying best checkpoint and rebuilding FAISS vector index...")
    import shutil
    best_ckpt = PROJECT_ROOT / "checkpoints" / "best_model.pt"
    target_ckpt = PROJECT_ROOT / "models" / "RemoteCLIP-ViT-B-32-finetuned.pt"
    if best_ckpt.exists():
        shutil.copyfile(best_ckpt, target_ckpt)
        print(f"✅ Deployed {best_ckpt} -> {target_ckpt}")

    subprocess.run([sys.executable, str(PROJECT_ROOT / "scripts" / "rebuild_finetuned_index.py")], check=True)

    print("\n🎉 All-Domain Fine-Tuning & Re-indexing Complete!")

if __name__ == "__main__":
    main()
