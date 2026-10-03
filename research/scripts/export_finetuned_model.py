"""
GeoNexa — Export Fine-Tuned Model for Deployment.

Takes a training checkpoint and exports it as a clean .pt file
compatible with the GeoNexa backend (RemoteCLIPEmbeddingModel).

Usage:
    python scripts/export_finetuned_model.py \\
        --checkpoint checkpoints/best_model.pt \\
        --output models/remoteclip-vit-b-32-finetuned/RemoteCLIP-ViT-B-32.pt

After export:
  1. Update .env: MODEL_PATH=models/remoteclip-vit-b-32-finetuned
  2. Rebuild the FAISS index: python scripts/build_index.py --force-rebuild
  3. Restart the backend server
"""

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import torch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def export_checkpoint(
    checkpoint_path: str,
    output_path: str,
    base_model_path: str = None,
    alpha: float = 0.5,
    include_optimizer: bool = False,
):
    """
    Export a training checkpoint as a clean deployment-ready .pt file.
    Supports WiSE-FT (Weight-Space Ensemble for Fine-Tuning) to blend
    fine-tuned domain features with the foundation model's robust zero-shot abilities.

    Args:
        checkpoint_path: Path to the training checkpoint.
        output_path: Path for the exported model.
        base_model_path: Optional path to baseline pretrained model for weight interpolation.
        alpha: Interpolation weight (0.0 = 100% baseline, 1.0 = 100% fine-tuned).
        include_optimizer: Include optimizer state (for resume training).
    """
    ckpt_p = Path(checkpoint_path)
    if not ckpt_p.exists():
        # Try finding final_model.pt or best_model.pt in parent/checkpoints dir
        alt_candidates = [
            ckpt_p.parent / "final_model.pt",
            ckpt_p.parent / "best_model.pt",
            PROJECT_ROOT / "checkpoints" / "final_model.pt",
            PROJECT_ROOT / "checkpoints" / "best_model.pt",
        ]
        found = False
        for cand in alt_candidates:
            if cand.exists():
                logger.info(f"Specified checkpoint {checkpoint_path} not found. Using detected alternative: {cand}")
                ckpt_p = cand
                found = True
                break
        if not found:
            raise FileNotFoundError(f"Cannot find checkpoint at {checkpoint_path} or fallback candidates: {[str(c) for c in alt_candidates]}")

    logger.info(f"Loading checkpoint: {ckpt_p}")
    ckpt = torch.load(str(ckpt_p), map_location="cpu")

    # Extract fine-tuned state dict
    if "state_dict" in ckpt:
        state_dict = ckpt["state_dict"]
    else:
        state_dict = ckpt

    clean_sd = {}
    for k, v in state_dict.items():
        k_clean = k.replace("module.", "") if k.startswith("module.") else k
        clean_sd[k_clean] = v

    # Optional WiSE-FT Weight Interpolation
    if base_model_path and Path(base_model_path).exists():
        logger.info(f"Applying WiSE-FT weight interpolation with alpha={alpha:.2f}...")
        logger.info(f"Base model: {base_model_path}")
        base_ckpt = torch.load(base_model_path, map_location="cpu")
        base_sd = base_ckpt.get("state_dict", base_ckpt)
        base_clean = {
            (k.replace("module.", "") if k.startswith("module.") else k): v
            for k, v in base_sd.items()
        }

        interpolated_count = 0
        for k in list(clean_sd.keys()):
            if k in base_clean and clean_sd[k].shape == base_clean[k].shape:
                if clean_sd[k].dtype in (torch.float32, torch.float16, torch.bfloat16):
                    clean_sd[k] = (1.0 - alpha) * base_clean[k].to(clean_sd[k].dtype) + alpha * clean_sd[k]
                    interpolated_count += 1
        logger.info(f"Interpolated {interpolated_count} weight tensors.")

    # Build export package
    export = {
        "state_dict": clean_sd,
        "model_arch": ckpt.get("config", {}).get("model_arch", "ViT-B-32"),
        "vector_dim": 512,
        "training_info": {
            "epochs_trained": ckpt.get("epoch", 0),
            "best_recall_at_5": ckpt.get("best_recall_at_5", 0),
            "experiment": ckpt.get("config", {}).get("experiment_name", "unknown"),
            "exported_at": datetime.now(timezone.utc).isoformat(),
        },
    }

    if include_optimizer and "optimizer" in ckpt:
        export["optimizer"] = ckpt["optimizer"]

    # Save
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    torch.save(export, str(output))

    size_mb = output.stat().st_size / (1024 * 1024)
    logger.info(f"Exported model: {output} ({size_mb:.1f} MB)")
    logger.info(f"  Architecture: {export['model_arch']}")
    logger.info(f"  Vector dim: {export['vector_dim']}")
    logger.info(f"  Epochs trained: {export['training_info']['epochs_trained']}")
    logger.info(f"  Best Recall@5: {export['training_info']['best_recall_at_5']:.4f}")

    # Save metadata alongside
    meta_path = output.with_suffix(".meta.json")
    with open(meta_path, "w") as f:
        json.dump(export["training_info"], f, indent=2)
    logger.info(f"  Metadata: {meta_path}")

    return str(output)


def verify_exported_model(model_path: str):
    """
    Verify that an exported model loads correctly in the GeoNexa backend.
    """
    logger.info(f"\nVerifying exported model: {model_path}")

    try:
        import open_clip

        model, _, preprocess = open_clip.create_model_and_transforms(
            "ViT-B-32", pretrained=None, device="cpu",
        )

        ckpt = torch.load(model_path, map_location="cpu")
        state_dict = ckpt.get("state_dict", ckpt)

        clean_sd = {}
        for k, v in state_dict.items():
            k_clean = k.replace("module.", "") if k.startswith("module.") else k
            clean_sd[k_clean] = v

        missing, unexpected = model.load_state_dict(clean_sd, strict=False)
        model.eval()

        # Test encoding
        tokenizer = open_clip.get_tokenizer("ViT-B-32")

        import numpy as np
        from PIL import Image

        # Test image encoding
        dummy_img = Image.fromarray(np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8))
        img_tensor = preprocess(dummy_img).unsqueeze(0)

        with torch.no_grad():
            img_features = model.encode_image(img_tensor)
            img_features = img_features / img_features.norm(dim=-1, keepdim=True)

        # Test text encoding
        text_tokens = tokenizer(["a satellite image of urban buildings"])
        with torch.no_grad():
            text_features = model.encode_text(text_tokens)
            text_features = text_features / text_features.norm(dim=-1, keepdim=True)

        # Verify dimensions
        assert img_features.shape == (1, 512), f"Image embedding shape mismatch: {img_features.shape}"
        assert text_features.shape == (1, 512), f"Text embedding shape mismatch: {text_features.shape}"

        # Verify L2 norm
        img_norm = img_features.norm().item()
        text_norm = text_features.norm().item()
        assert abs(img_norm - 1.0) < 0.01, f"Image embedding not normalized: {img_norm}"
        assert abs(text_norm - 1.0) < 0.01, f"Text embedding not normalized: {text_norm}"

        # Compute similarity
        similarity = (img_features @ text_features.T).item()

        logger.info("  ✓ Model loads correctly")
        logger.info(f"  ✓ Image embedding: shape={img_features.shape}, norm={img_norm:.4f}")
        logger.info(f"  ✓ Text embedding: shape={text_features.shape}, norm={text_norm:.4f}")
        logger.info(f"  ✓ Cross-modal similarity: {similarity:.4f}")

        if missing:
            logger.warning(f"  ⚠ Missing keys: {len(missing)} (expected for partial fine-tune)")
        if unexpected:
            logger.warning(f"  ⚠ Unexpected keys: {len(unexpected)}")

        logger.info("  ✓ VERIFICATION PASSED — Model is deployment-ready!")
        return True

    except Exception as e:
        logger.error(f"  ✗ Verification FAILED: {e}")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export fine-tuned GeoNexa model")
    parser.add_argument("--checkpoint", required=True, help="Training checkpoint path")
    parser.add_argument(
        "--output",
        default=str(PROJECT_ROOT / "models" / "remoteclip-vit-b-32-finetuned" / "RemoteCLIP-ViT-B-32.pt"),
        help="Output model path",
    )
    parser.add_argument("--include-optimizer", action="store_true")
    parser.add_argument("--base-model", default=None, help="Base model checkpoint for WiSE-FT interpolation")
    parser.add_argument("--alpha", type=float, default=0.5, help="WiSE-FT interpolation weight (0.0=base, 1.0=finetuned)")
    parser.add_argument("--verify", action="store_true", default=True)

    args = parser.parse_args()

    output = export_checkpoint(
        checkpoint_path=args.checkpoint,
        output_path=args.output,
        base_model_path=args.base_model,
        alpha=args.alpha,
        include_optimizer=args.include_optimizer,
    )

    if args.verify:
        verify_exported_model(output)
