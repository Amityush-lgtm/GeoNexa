"""
GeoNexa — Earth Observation Fine-Tuning Dataset.

PyTorch Dataset for contrastive fine-tuning of CLIP-based models
on satellite imagery with auto-generated and curated text captions.

Supports:
  - Loading image-text pairs from JSON manifest
  - Satellite-specific augmentations (rotation, flip, spectral jitter)
  - Hard negative sampling within the batch
  - Multi-resolution tile support (GeoTIFF and standard images)
"""

import json
import logging
import random
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import torch
from PIL import Image
from torch.utils.data import Dataset

logger = logging.getLogger(__name__)


class EOFineTuneDataset(Dataset):
    """
    Earth Observation image-text contrastive learning dataset.

    Each item returns:
        - image: Tensor (3, H, W) — preprocessed satellite tile
        - text:  str — matching caption
        - metadata: dict — tile_id, land_cover, etc.
    """

    def __init__(
        self,
        pairs_json: str,
        image_transform=None,
        tokenizer=None,
        max_text_len: int = 77,
        positive_only: bool = True,
        augment: bool = True,
    ):
        """
        Args:
            pairs_json: Path to JSON file with image-text pairs.
            image_transform: CLIP image preprocessing transform.
            tokenizer: CLIP text tokenizer.
            max_text_len: Maximum text token length.
            positive_only: If True, only load positive (matching) pairs.
            augment: Apply satellite-specific augmentations.
        """
        self.image_transform = image_transform
        self.tokenizer = tokenizer
        self.max_text_len = max_text_len
        self.augment = augment

        # Load pairs
        with open(pairs_json, "r") as f:
            data = json.load(f)

        all_pairs = data["pairs"]
        if positive_only:
            self.pairs = [p for p in all_pairs if p.get("label", 1) == 1]
        else:
            self.pairs = all_pairs

        # Group by tile for hard negative mining
        self._tile_to_captions: Dict[str, List[str]] = {}
        for p in all_pairs:
            tid = p["tile_id"]
            if tid not in self._tile_to_captions:
                self._tile_to_captions[tid] = []
            self._tile_to_captions[tid].append(p["caption"])

        logger.info(
            f"Loaded {len(self.pairs)} pairs from {pairs_json} "
            f"({len(self._tile_to_captions)} unique tiles)"
        )

    def __len__(self) -> int:
        return len(self.pairs)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, str, dict]:
        pair = self.pairs[idx]
        image_path = pair["image_path"]
        caption = pair["caption"]

        # Load image
        image = self._load_image(image_path)

        # Apply satellite-specific augmentation
        if self.augment and image is not None:
            image = self._satellite_augment(image)

        # Apply CLIP preprocessing
        if self.image_transform is not None and image is not None:
            image_tensor = self.image_transform(image)
        elif image is not None:
            # Fallback: convert to tensor
            img_array = np.array(image).astype(np.float32) / 255.0
            image_tensor = torch.from_numpy(img_array).permute(2, 0, 1)
        else:
            # Black placeholder
            image_tensor = torch.zeros(3, 224, 224)

        metadata = {
            "tile_id": pair.get("tile_id", ""),
            "scene_id": pair.get("scene_id", ""),
            "land_cover": pair.get("land_cover", "unknown"),
            "label": pair.get("label", 1),
        }

        return image_tensor, caption, metadata

    def _load_image(self, path: str) -> Optional[Image.Image]:
        """Load a tile image as PIL Image."""
        try:
            p = Path(path)
            if p.suffix.lower() in (".tif", ".tiff"):
                return self._load_geotiff_as_pil(p)
            else:
                return Image.open(path).convert("RGB")
        except Exception as e:
            logger.warning(f"Failed to load image {path}: {e}")
            return None

    def _load_geotiff_as_pil(self, path: Path) -> Optional[Image.Image]:
        """Load a GeoTIFF tile and convert to PIL RGB Image."""
        try:
            import rasterio
            with rasterio.open(str(path)) as ds:
                bands = min(ds.count, 3)
                data = ds.read(list(range(1, bands + 1)))

                if bands == 1:
                    data = np.repeat(data, 3, axis=0)
                elif bands == 2:
                    data = np.concatenate([data, np.zeros_like(data[:1])], axis=0)

                image = np.transpose(data, (1, 2, 0))  # CHW → HWC

                # Normalize to 0-255
                if image.dtype != np.uint8:
                    valid = image[image > 0]
                    if len(valid) > 0:
                        vmin = np.percentile(valid, 2)
                        vmax = np.percentile(valid, 98)
                    else:
                        vmin, vmax = 0, 1
                    if vmax > vmin:
                        image = np.clip(
                            (image - vmin) / (vmax - vmin) * 255, 0, 255
                        ).astype(np.uint8)
                    else:
                        image = np.zeros_like(image, dtype=np.uint8)

                return Image.fromarray(image)
        except Exception as e:
            logger.warning(f"Could not load GeoTIFF {path}: {e}")
            return None

    def _satellite_augment(self, image: Image.Image) -> Image.Image:
        """
        Apply satellite-specific augmentations.

        Unlike natural photos, satellite images:
        - Have no canonical "up" direction → random 90° rotations are valid
        - Can be flipped horizontally and vertically
        - Have spectral variations from atmosphere and sensor
        """
        # Random 90° rotation (0, 90, 180, 270)
        k = random.choice([0, 1, 2, 3])
        if k > 0:
            image = image.rotate(k * 90, expand=False)

        # Random horizontal flip
        if random.random() > 0.5:
            image = image.transpose(Image.FLIP_LEFT_RIGHT)

        # Random vertical flip
        if random.random() > 0.5:
            image = image.transpose(Image.FLIP_TOP_BOTTOM)

        # Subtle color jitter (simulates atmospheric variation)
        if random.random() > 0.3:
            image = self._spectral_jitter(image)

        return image

    def _spectral_jitter(self, image: Image.Image, intensity: float = 0.1) -> Image.Image:
        """
        Apply subtle spectral jitter simulating atmospheric/sensor variation.

        This is different from natural photo color jitter — it models
        per-band gain shifts typical of satellite sensor calibration differences.
        """
        arr = np.array(image).astype(np.float32)

        # Per-channel multiplicative gain (simulates different atmospheric windows)
        for c in range(min(3, arr.shape[2])):
            gain = 1.0 + random.uniform(-intensity, intensity)
            arr[:, :, c] = np.clip(arr[:, :, c] * gain, 0, 255)

        # Small additive offset (simulates dark current / atmospheric scattering)
        offset = random.uniform(-10, 10)
        arr = np.clip(arr + offset, 0, 255)

        return Image.fromarray(arr.astype(np.uint8))

    def get_all_captions(self) -> List[str]:
        """Return all unique captions in the dataset."""
        return list(set(p["caption"] for p in self.pairs))

    def get_class_distribution(self) -> Dict[str, int]:
        """Return count of pairs per land cover class."""
        dist = {}
        for p in self.pairs:
            lc = p.get("land_cover", "unknown")
            dist[lc] = dist.get(lc, 0) + 1
        return dist


def default_eo_collate_fn(batch):
    images, captions, metas = zip(*batch)
    images = torch.stack(images)
    return images, list(captions), list(metas)


def create_dataloaders(
    train_json: str,
    val_json: Optional[str],
    image_transform,
    tokenizer,
    batch_size: int = 32,
    num_workers: int = 4,
    pin_memory: bool = True,
):
    """
    Create train and optional validation DataLoaders.

    Returns:
        Tuple of (train_loader, val_loader or None).
    """
    from torch.utils.data import DataLoader

    train_dataset = EOFineTuneDataset(
        pairs_json=train_json,
        image_transform=image_transform,
        tokenizer=tokenizer,
        augment=True,
    )

    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=num_workers,
        pin_memory=pin_memory,
        collate_fn=default_eo_collate_fn,
        drop_last=True,
    )

    val_loader = None
    if val_json and Path(val_json).exists():
        val_dataset = EOFineTuneDataset(
            pairs_json=val_json,
            image_transform=image_transform,
            tokenizer=tokenizer,
            augment=False,
        )
        val_loader = DataLoader(
            val_dataset,
            batch_size=batch_size,
            shuffle=False,
            num_workers=num_workers,
            pin_memory=pin_memory,
            collate_fn=default_eo_collate_fn,
        )

    return train_loader, val_loader
