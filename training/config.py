"""
GeoNexa — Fine-Tuning Configuration.

Hyperparameters and paths for contrastive fine-tuning of RemoteCLIP ViT-B-32
on domain-specific Earth Observation image-text pairs.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class TrainingConfig:
    """Fine-tuning hyperparameters."""

    # ── Model ──────────────────────────────────────────────
    model_arch: str = "ViT-B-32"
    pretrained_checkpoint: str = ""  # Path to RemoteCLIP-ViT-B-32.pt
    output_dir: str = "checkpoints"

    # ── Data ───────────────────────────────────────────────
    train_data_dir: str = ""        # Directory with training tiles
    train_pairs_json: str = ""      # JSON file with image-text pairs
    val_pairs_json: str = ""        # Validation pairs
    image_size: int = 224           # CLIP input resolution

    # ── Training ───────────────────────────────────────────
    epochs: int = 30
    batch_size: int = 32
    learning_rate: float = 1e-5
    weight_decay: float = 0.01
    warmup_epochs: int = 3
    min_lr: float = 1e-7

    # ── CLIP Contrastive Loss ──────────────────────────────
    temperature: float = 0.07       # Learnable log temperature init
    label_smoothing: float = 0.1

    # ── Fine-tuning Strategy ──────────────────────────────
    freeze_image_encoder: bool = False
    freeze_text_encoder: bool = True   # Text encoder is already strong
    unfreeze_layers: int = 4           # Unfreeze last N transformer blocks
    gradient_accumulation_steps: int = 1

    # ── Augmentation ──────────────────────────────────────
    use_augmentation: bool = True
    random_crop: bool = True
    horizontal_flip: bool = True
    vertical_flip: bool = True       # Satellite images have no "up"
    color_jitter: float = 0.3
    random_rotation: float = 90.0    # Rotation augmentation (degrees)

    # ── Evaluation ─────────────────────────────────────────
    eval_every_n_epochs: int = 5
    save_every_n_epochs: int = 5
    eval_top_k: List[int] = field(default_factory=lambda: [1, 5, 10])

    # ── Hardware ───────────────────────────────────────────
    device: str = "auto"            # "auto", "cpu", "cuda", "cuda:0"
    mixed_precision: bool = True    # fp16 on GPU
    num_workers: int = 4
    pin_memory: bool = True

    # ── Logging ────────────────────────────────────────────
    log_every_n_steps: int = 10
    experiment_name: str = "geonexa_remoteclip_finetune"

    def resolve_device(self) -> str:
        """Resolve 'auto' device to actual device string."""
        if self.device != "auto":
            return self.device
        import torch
        if torch.cuda.is_available():
            return "cuda"
        return "cpu"

    def to_dict(self) -> dict:
        """Serialize config to dict for logging."""
        return {k: str(v) if isinstance(v, Path) else v
                for k, v in self.__dict__.items()}
