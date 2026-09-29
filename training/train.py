"""
GeoNexa — RemoteCLIP Fine-Tuning Training Loop.

End-to-end contrastive fine-tuning of RemoteCLIP ViT-B-32 for
domain-specific Earth Observation semantic retrieval.

Supports:
  - Full fine-tuning or partial unfreezing (last N blocks)
  - Mixed precision (fp16) on GPU
  - Cosine annealing LR schedule with warmup
  - Periodic evaluation with Recall@K metrics
  - Checkpoint saving and resuming
  - Works on CPU (slow) and GPU (Colab T4 / local CUDA)

Usage:
    # Local (CPU — demo/debug only):
    python -m training.train --config training/configs/local_cpu.json

    # Colab (GPU):
    python -m training.train --device cuda --epochs 30 --batch-size 64
"""

import json
import logging
import math
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.cuda.amp import GradScaler, autocast

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from training.config import TrainingConfig
from training.losses import CLIPContrastiveLoss, HardNegativeCLIPLoss
from training.dataset import EOFineTuneDataset, create_dataloaders

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


class RemoteCLIPTrainer:
    """
    Fine-tuning trainer for RemoteCLIP on Earth Observation data.

    Training strategy:
      1. Freeze most of the model, unfreeze last N transformer blocks
      2. Use CLIP contrastive loss with learnable temperature
      3. Cosine annealing schedule with linear warmup
      4. Mixed precision on GPU for speed
      5. Evaluate Recall@K periodically
    """

    def __init__(self, config: TrainingConfig):
        self.config = config
        self.device = config.resolve_device()
        self.start_time = time.time()

        logger.info(f"═══════════════════════════════════════════════")
        logger.info(f"  GeoNexa RemoteCLIP Fine-Tuning")
        logger.info(f"  Device: {self.device}")
        logger.info(f"  Epochs: {config.epochs}")
        logger.info(f"  Batch size: {config.batch_size}")
        logger.info(f"  Learning rate: {config.learning_rate}")
        logger.info(f"  Freeze image encoder: {config.freeze_image_encoder}")
        logger.info(f"  Freeze text encoder: {config.freeze_text_encoder}")
        logger.info(f"  Unfreeze last N layers: {config.unfreeze_layers}")
        logger.info(f"═══════════════════════════════════════════════")

        # Initialize model, optimizer, loss, dataloaders
        self.model = None
        self.preprocess = None
        self.tokenizer = None
        self.optimizer = None
        self.scheduler = None
        self.loss_fn = None
        self.scaler = None
        self.train_loader = None
        self.val_loader = None

        # Training state
        self.current_epoch = 0
        self.global_step = 0
        self.best_recall_at_5 = 0.0
        self.training_history = []

    def setup(self):
        """Initialize all components."""
        self._load_model()
        self._configure_trainable_params()
        self._setup_loss()
        self._setup_optimizer()
        self._setup_dataloaders()

        if self.device == "cuda" and self.config.mixed_precision:
            self.scaler = GradScaler()
            logger.info("Mixed precision training (fp16) enabled")

    def _load_model(self):
        """Load RemoteCLIP model from checkpoint."""
        import open_clip

        model_name = self.config.model_arch
        checkpoint = self.config.pretrained_checkpoint

        logger.info(f"Loading {model_name} architecture...")

        if checkpoint and Path(checkpoint).exists():
            logger.info(f"Loading weights from: {checkpoint}")
            self.model, _, self.preprocess = open_clip.create_model_and_transforms(
                model_name, pretrained=None, device=self.device,
            )
            ckpt = torch.load(checkpoint, map_location=self.device)
            state_dict = ckpt.get("state_dict", ckpt)

            # Clean module prefix
            clean_sd = {}
            for k, v in state_dict.items():
                k_clean = k.replace("module.", "") if k.startswith("module.") else k
                clean_sd[k_clean] = v
            self.model.load_state_dict(clean_sd, strict=False)
        else:
            logger.info(f"Loading {model_name} with OpenAI pretrained weights (fallback)")
            self.model, _, self.preprocess = open_clip.create_model_and_transforms(
                model_name, pretrained="openai", device=self.device,
            )

        self.tokenizer = open_clip.get_tokenizer(model_name)
        self.model.to(self.device)

        total_params = sum(p.numel() for p in self.model.parameters())
        logger.info(f"Model loaded: {total_params / 1e6:.1f}M parameters")

    def _configure_trainable_params(self):
        """
        Configure which parameters are trainable.

        Strategy:
          - Freeze text encoder (already well-trained on natural language)
          - Freeze early visual layers (low-level features transfer well)
          - Unfreeze last N visual transformer blocks (learn domain-specific features)
          - Always unfreeze the projection heads
        """
        # First freeze everything
        for param in self.model.parameters():
            param.requires_grad = False

        trainable_count = 0

        # ── Visual encoder ──
        if not self.config.freeze_image_encoder:
            # Unfreeze last N transformer blocks in visual encoder
            visual = self.model.visual

            # Unfreeze the projection layer (always)
            if hasattr(visual, "proj") and visual.proj is not None:
                visual.proj.requires_grad = True
                trainable_count += visual.proj.numel()

            # Unfreeze layer norm
            if hasattr(visual, "ln_post"):
                for p in visual.ln_post.parameters():
                    p.requires_grad = True
                    trainable_count += p.numel()

            # Unfreeze last N transformer blocks
            if hasattr(visual, "transformer"):
                resblocks = visual.transformer.resblocks
                n_blocks = len(resblocks)
                unfreeze_from = max(0, n_blocks - self.config.unfreeze_layers)

                for i in range(unfreeze_from, n_blocks):
                    for p in resblocks[i].parameters():
                        p.requires_grad = True
                        trainable_count += p.numel()

                logger.info(
                    f"Visual encoder: unfroze blocks [{unfreeze_from}..{n_blocks-1}] "
                    f"of {n_blocks} total"
                )

        # ── Text encoder ──
        if not self.config.freeze_text_encoder:
            # Unfreeze text projection
            if hasattr(self.model, "text_projection") and self.model.text_projection is not None:
                self.model.text_projection.requires_grad = True
                trainable_count += self.model.text_projection.numel()

            # Unfreeze last N text transformer blocks
            if hasattr(self.model, "transformer"):
                resblocks = self.model.transformer.resblocks
                n_blocks = len(resblocks)
                unfreeze_from = max(0, n_blocks - self.config.unfreeze_layers)
                for i in range(unfreeze_from, n_blocks):
                    for p in resblocks[i].parameters():
                        p.requires_grad = True
                        trainable_count += p.numel()

        # ── Logit scale (temperature) ──
        if hasattr(self.model, "logit_scale"):
            self.model.logit_scale.requires_grad = True
            trainable_count += 1

        total_params = sum(p.numel() for p in self.model.parameters())
        logger.info(
            f"Trainable parameters: {trainable_count / 1e6:.2f}M / "
            f"{total_params / 1e6:.1f}M ({100 * trainable_count / total_params:.1f}%)"
        )

    def _setup_loss(self):
        """Initialize contrastive loss function."""
        self.loss_fn = HardNegativeCLIPLoss(
            temperature=self.config.temperature,
            label_smoothing=self.config.label_smoothing,
            hard_negative_weight=2.0,
            learnable_temperature=True,
        ).to(self.device)

    def _setup_optimizer(self):
        """Set up optimizer and LR scheduler."""
        # Collect trainable parameters from model + loss
        params = [
            {"params": [p for p in self.model.parameters() if p.requires_grad],
             "lr": self.config.learning_rate},
            {"params": self.loss_fn.parameters(),
             "lr": self.config.learning_rate * 10},  # Temperature learns faster
        ]

        self.optimizer = optim.AdamW(
            params,
            lr=self.config.learning_rate,
            weight_decay=self.config.weight_decay,
            betas=(0.9, 0.98),
            eps=1e-6,
        )

        # Cosine annealing with linear warmup
        total_steps = self.config.epochs  # We step per epoch
        warmup_steps = self.config.warmup_epochs

        def lr_lambda(current_step):
            if current_step < warmup_steps:
                return float(current_step) / float(max(1, warmup_steps))
            progress = float(current_step - warmup_steps) / float(
                max(1, total_steps - warmup_steps)
            )
            return max(
                self.config.min_lr / self.config.learning_rate,
                0.5 * (1.0 + math.cos(math.pi * progress)),
            )

        self.scheduler = optim.lr_scheduler.LambdaLR(self.optimizer, lr_lambda)

    def _setup_dataloaders(self):
        """Create training and validation dataloaders."""
        self.train_loader, self.val_loader = create_dataloaders(
            train_json=self.config.train_pairs_json,
            val_json=self.config.val_pairs_json if self.config.val_pairs_json else None,
            image_transform=self.preprocess,
            tokenizer=self.tokenizer,
            batch_size=self.config.batch_size,
            num_workers=min(self.config.num_workers, os.cpu_count() or 2),
            pin_memory=self.config.pin_memory and self.device == "cuda",
        )
        logger.info(f"Training batches: {len(self.train_loader)}")
        if self.val_loader:
            logger.info(f"Validation batches: {len(self.val_loader)}")

    def train(self):
        """Run the full training loop."""
        self.setup()
        output_dir = Path(self.config.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save config
        with open(output_dir / "training_config.json", "w") as f:
            json.dump(self.config.to_dict(), f, indent=2)

        logger.info("Starting training...")

        for epoch in range(self.config.epochs):
            self.current_epoch = epoch
            epoch_start = time.time()

            # ── Train one epoch ──
            train_metrics = self._train_epoch(epoch)

            # ── Step scheduler ──
            self.scheduler.step()
            current_lr = self.optimizer.param_groups[0]["lr"]

            epoch_time = time.time() - epoch_start

            logger.info(
                f"Epoch {epoch+1}/{self.config.epochs} | "
                f"Loss: {train_metrics['loss']:.4f} | "
                f"Acc I→T: {train_metrics['accuracy_i2t']:.3f} | "
                f"Acc T→I: {train_metrics['accuracy_t2i']:.3f} | "
                f"Temp: {train_metrics['temperature']:.4f} | "
                f"LR: {current_lr:.2e} | "
                f"Time: {epoch_time:.1f}s"
            )

            # ── Evaluation ──
            if (epoch + 1) % self.config.eval_every_n_epochs == 0:
                val_metrics = self._evaluate(epoch)
                train_metrics.update(val_metrics)

                # Track best model
                recall_5 = val_metrics.get("recall@5", 0)
                if recall_5 > self.best_recall_at_5:
                    self.best_recall_at_5 = recall_5
                    self._save_checkpoint(output_dir / "best_model.pt", is_best=True)
                    logger.info(f"  ★ New best Recall@5: {recall_5:.4f}")

            # ── Save checkpoint ──
            if (epoch + 1) % self.config.save_every_n_epochs == 0:
                self._save_checkpoint(
                    output_dir / f"checkpoint_epoch_{epoch+1}.pt"
                )

            # Record history
            train_metrics["epoch"] = epoch + 1
            train_metrics["lr"] = current_lr
            train_metrics["epoch_time_s"] = epoch_time
            self.training_history.append(train_metrics)

        # ── Save final model ──
        self._save_checkpoint(output_dir / "final_model.pt")
        self._save_training_report(output_dir / "training_report.json")

        total_time = time.time() - self.start_time
        logger.info(f"Training complete! Total time: {total_time / 60:.1f} minutes")
        logger.info(f"Best Recall@5: {self.best_recall_at_5:.4f}")
        logger.info(f"Checkpoints saved in: {output_dir}")

    def _train_epoch(self, epoch: int) -> dict:
        """Train for one epoch."""
        self.model.train()
        total_loss = 0.0
        total_acc_i2t = 0.0
        total_acc_t2i = 0.0
        total_temp = 0.0
        n_batches = 0

        for batch_idx, (images, captions, metadata) in enumerate(self.train_loader):
            images = images.to(self.device)

            # Tokenize captions
            text_tokens = self.tokenizer(captions).to(self.device)

            # Forward pass
            use_amp = self.device == "cuda" and self.config.mixed_precision

            if use_amp:
                with autocast():
                    image_features = self.model.encode_image(images)
                    text_features = self.model.encode_text(text_tokens)

                    # L2 normalize
                    image_features = image_features / image_features.norm(dim=-1, keepdim=True)
                    text_features = text_features / text_features.norm(dim=-1, keepdim=True)

                    loss_dict = self.loss_fn(image_features, text_features)
                    loss = loss_dict["loss"]

                # Backward with gradient scaling
                self.scaler.scale(loss).backward()

                if (batch_idx + 1) % self.config.gradient_accumulation_steps == 0:
                    self.scaler.unscale_(self.optimizer)
                    nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
                    self.scaler.step(self.optimizer)
                    self.scaler.update()
                    self.optimizer.zero_grad()
            else:
                image_features = self.model.encode_image(images)
                text_features = self.model.encode_text(text_tokens)

                image_features = image_features / image_features.norm(dim=-1, keepdim=True)
                text_features = text_features / text_features.norm(dim=-1, keepdim=True)

                loss_dict = self.loss_fn(image_features, text_features)
                loss = loss_dict["loss"]

                loss.backward()

                if (batch_idx + 1) % self.config.gradient_accumulation_steps == 0:
                    nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
                    self.optimizer.step()
                    self.optimizer.zero_grad()

            total_loss += loss_dict["loss"].item()
            total_acc_i2t += loss_dict["accuracy_i2t"]
            total_acc_t2i += loss_dict["accuracy_t2i"]
            total_temp += loss_dict["temperature"]
            n_batches += 1
            self.global_step += 1

            # Log periodically
            if (batch_idx + 1) % self.config.log_every_n_steps == 0:
                avg_loss = total_loss / n_batches
                logger.info(
                    f"  [Epoch {epoch+1} | Step {batch_idx+1}/{len(self.train_loader)}] "
                    f"Loss: {avg_loss:.4f}"
                )

        return {
            "loss": total_loss / max(n_batches, 1),
            "accuracy_i2t": total_acc_i2t / max(n_batches, 1),
            "accuracy_t2i": total_acc_t2i / max(n_batches, 1),
            "temperature": total_temp / max(n_batches, 1),
        }

    @torch.no_grad()
    def _evaluate(self, epoch: int) -> dict:
        """Evaluate Recall@K on validation set."""
        if self.val_loader is None:
            # Evaluate on training set if no validation set
            loader = self.train_loader
            logger.info("  Evaluating on training set (no validation set provided)...")
        else:
            loader = self.val_loader
            logger.info("  Evaluating on validation set...")

        self.model.eval()

        all_image_features = []
        all_text_features = []

        for images, captions, _ in loader:
            images = images.to(self.device)
            text_tokens = self.tokenizer(captions).to(self.device)

            image_features = self.model.encode_image(images)
            text_features = self.model.encode_text(text_tokens)

            image_features = image_features / image_features.norm(dim=-1, keepdim=True)
            text_features = text_features / text_features.norm(dim=-1, keepdim=True)

            all_image_features.append(image_features.cpu())
            all_text_features.append(text_features.cpu())

        all_image_features = torch.cat(all_image_features, dim=0)
        all_text_features = torch.cat(all_text_features, dim=0)

        # Compute similarity matrix
        sim_matrix = all_image_features @ all_text_features.T
        n = sim_matrix.shape[0]

        metrics = {}
        for k in self.config.eval_top_k:
            # Image → Text recall
            top_k_indices = sim_matrix.topk(min(k, n), dim=1).indices
            correct_i2t = sum(
                1 for i in range(n) if i in top_k_indices[i]
            )
            recall_i2t = correct_i2t / n

            # Text → Image recall
            top_k_indices_t2i = sim_matrix.T.topk(min(k, n), dim=1).indices
            correct_t2i = sum(
                1 for i in range(n) if i in top_k_indices_t2i[i]
            )
            recall_t2i = correct_t2i / n

            metrics[f"recall@{k}"] = (recall_i2t + recall_t2i) / 2
            metrics[f"recall@{k}_i2t"] = recall_i2t
            metrics[f"recall@{k}_t2i"] = recall_t2i

        logger.info(
            f"  Recall@1: {metrics.get('recall@1', 0):.4f} | "
            f"Recall@5: {metrics.get('recall@5', 0):.4f} | "
            f"Recall@10: {metrics.get('recall@10', 0):.4f}"
        )

        self.model.train()
        return metrics

    def _save_checkpoint(self, path: Path, is_best: bool = False):
        """Save model checkpoint."""
        path.parent.mkdir(parents=True, exist_ok=True)

        checkpoint = {
            "epoch": self.current_epoch,
            "global_step": self.global_step,
            "state_dict": self.model.state_dict(),
            "optimizer": self.optimizer.state_dict(),
            "scheduler": self.scheduler.state_dict(),
            "best_recall_at_5": self.best_recall_at_5,
            "config": self.config.to_dict(),
            "training_history": self.training_history,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if self.scaler is not None:
            checkpoint["scaler"] = self.scaler.state_dict()

        torch.save(checkpoint, str(path))
        label = " (★ BEST)" if is_best else ""
        logger.info(f"  Checkpoint saved: {path}{label}")

    def _save_training_report(self, path: Path):
        """Save training summary report."""
        report = {
            "experiment": self.config.experiment_name,
            "model": self.config.model_arch,
            "device": self.device,
            "total_epochs": self.config.epochs,
            "best_recall_at_5": self.best_recall_at_5,
            "final_metrics": self.training_history[-1] if self.training_history else {},
            "history": self.training_history,
            "config": self.config.to_dict(),
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }

        with open(path, "w") as f:
            json.dump(report, f, indent=2)
        logger.info(f"Training report saved: {path}")


def main():
    """CLI entry point for fine-tuning."""
    import argparse

    parser = argparse.ArgumentParser(description="GeoNexa RemoteCLIP Fine-Tuning")

    # Required
    parser.add_argument("--train-data", required=True, help="Path to training pairs JSON")

    # Optional
    parser.add_argument("--val-data", default="", help="Path to validation pairs JSON")
    parser.add_argument("--checkpoint", default="", help="Path to pretrained checkpoint (.pt)")
    parser.add_argument("--output-dir", default="checkpoints", help="Output directory")

    # Hyperparameters
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=1e-5)
    parser.add_argument("--unfreeze-layers", "--unfreeze-last-n", dest="unfreeze_layers", type=int, default=4)
    parser.add_argument("--freeze-text", action="store_true", default=True)
    parser.add_argument("--no-freeze-text", dest="freeze_text", action="store_false")

    # Hardware
    parser.add_argument("--device", default="auto", choices=["auto", "cpu", "cuda"])
    parser.add_argument("--mixed-precision", action="store_true", default=True)
    parser.add_argument("--num-workers", type=int, default=4)

    # Training control
    parser.add_argument("--eval-every", type=int, default=5)
    parser.add_argument("--save-every", type=int, default=5)
    parser.add_argument("--experiment-name", default="geonexa_finetune")

    args = parser.parse_args()

    config = TrainingConfig(
        pretrained_checkpoint=args.checkpoint,
        output_dir=args.output_dir,
        train_pairs_json=args.train_data,
        val_pairs_json=args.val_data,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.lr,
        unfreeze_layers=args.unfreeze_layers,
        freeze_text_encoder=args.freeze_text,
        device=args.device,
        mixed_precision=args.mixed_precision,
        num_workers=args.num_workers,
        eval_every_n_epochs=args.eval_every,
        save_every_n_epochs=args.save_every,
        experiment_name=args.experiment_name,
    )

    trainer = RemoteCLIPTrainer(config)
    trainer.train()


if __name__ == "__main__":
    main()
