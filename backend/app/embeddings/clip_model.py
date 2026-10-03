"""
RemoteCLIP ViT-B-32 embedding model implementation for Earth Observation.

Loads RemoteCLIP (ViT-B-32) from a local checkpoint with zero runtime internet access.
Inference is 100% on-premises / offline.
"""

import logging
import os
from pathlib import Path
from typing import List, Optional

import numpy as np
import torch
from PIL import Image

from app.embeddings.base import EmbeddingModel

logger = logging.getLogger(__name__)


class RemoteCLIPEmbeddingModel(EmbeddingModel):
    """
    RemoteCLIP ViT-B-32 foundation model for remote sensing cross-modal retrieval.

    Encodes satellite imagery and natural language text into a shared 512-dimensional
    L2-normalized vector space.
    """

    def __init__(self, model_path: str | Path | None = None, device: str = "cpu"):
        """
        Initialize the RemoteCLIP model.

        Args:
            model_path: Path to local model checkpoint (.pt) or weights directory.
            device: 'cpu' or 'cuda'.
        """
        if device == "cuda" and not torch.cuda.is_available():
            device = "cpu"
        self._device = device
        self._model_path = Path(model_path) if model_path else None
        self._model = None
        self._preprocess = None
        self._tokenizer = None
        self._load_model()

    def _find_checkpoint_file(self) -> Optional[Path]:
        """Locate checkpoint file inside model_path."""
        if not self._model_path:
            return None

        if self._model_path.is_file():
            return self._model_path

        if self._model_path.is_dir():
            candidates = [
                self._model_path.parent / "RemoteCLIP-ViT-B-32-finetuned.pt",
                self._model_path / "RemoteCLIP-ViT-B-32-finetuned.pt",
                self._model_path / "RemoteCLIP-ViT-B-32.pt",
                self._model_path / "remoteclip_vit_b32.pt",
                self._model_path / "model.pt",
                self._model_path / "pytorch_model.bin",
            ]
            for c in candidates:
                if c.is_file():
                    return c
            # Find any .pt file in the directory
            pt_files = list(self._model_path.glob("*.pt"))
            if pt_files:
                return pt_files[0]

        return None

    def _load_model(self):
        """Load the RemoteCLIP model weights and transforms locally."""
        try:
            import open_clip

            model_name = "ViT-B-32"
            checkpoint_file = self._find_checkpoint_file()

            if checkpoint_file and checkpoint_file.exists():
                logger.info(f"Loading local RemoteCLIP weights from: {checkpoint_file}")
                # Create architecture without downloading pretrained weights
                self._model, _, self._preprocess = open_clip.create_model_and_transforms(
                    model_name,
                    pretrained=None,
                    device=self._device,
                )
                ckpt = torch.load(str(checkpoint_file), map_location=self._device)
                state_dict = ckpt.get("state_dict", ckpt)
                # Clean prefix if needed
                clean_state_dict = {}
                for k, v in state_dict.items():
                    k_clean = k.replace("module.", "") if k.startswith("module.") else k
                    clean_state_dict[k_clean] = v
                self._model.load_state_dict(clean_state_dict, strict=False)
            else:
                # If checkpoint file is missing, enforce strict offline failure unless test mode
                error_msg = (
                    f"RemoteCLIP checkpoint not found at: {self._model_path}\n"
                    f"Please place 'RemoteCLIP-ViT-B-32.pt' in {self._model_path or 'models/remoteclip-vit-b-32/'}.\n"
                    f"GeoNexa operates in 100% offline mode and strictly refuses to download weights at runtime."
                )
                logger.error(error_msg)
                raise FileNotFoundError(error_msg)

            self._tokenizer = open_clip.get_tokenizer(model_name)
            self._model.eval()
            logger.info(f"Successfully loaded RemoteCLIP {model_name} on {self._device} (Offline Mode)")

        except ImportError:
            logger.error("open_clip not installed. Install with: pip install open-clip-torch")
            raise

    def encode_image(self, image: np.ndarray) -> np.ndarray:
        """
        Encode a single RGB image into an L2-normalized embedding vector.

        Args:
            image: RGB image as numpy array (H, W, 3) with values in [0, 255].

        Returns:
            L2-normalized embedding vector of shape (512,).
        """
        pil_image = Image.fromarray(image.astype(np.uint8))
        image_tensor = self._preprocess(pil_image).unsqueeze(0).to(self._device)

        with torch.no_grad():
            features = self._model.encode_image(image_tensor)
            features = features / features.norm(dim=-1, keepdim=True)

        return features.cpu().numpy().flatten().astype(np.float32)

    def encode_text(self, text: str, ensemble: bool = True) -> np.ndarray:
        """
        Encode a text query into an L2-normalized embedding vector.

        Supports remote sensing prompt ensembling across multiple domain templates
        to significantly boost cross-modal semantic alignment and retrieval precision.

        Args:
            text: Natural language search string.
            ensemble: If True, ensembles multiple domain-adapted prompts.

        Returns:
            L2-normalized embedding vector of shape (512,).
        """
        clean_text = text.strip()
        if not ensemble or len(clean_text) == 0:
            prompts = [clean_text]
        else:
            prompts = [
                clean_text,
                f"a satellite photo of {clean_text}",
                f"satellite imagery showing {clean_text}",
                f"aerial view of {clean_text}",
                f"remote sensing capture of {clean_text}",
            ]

        tokens = self._tokenizer(prompts).to(self._device)

        with torch.no_grad():
            features = self._model.encode_text(tokens)
            features = features / features.norm(dim=-1, keepdim=True)
            if len(prompts) > 1:
                features = features.mean(dim=0, keepdim=True)
                features = features / features.norm(dim=-1, keepdim=True)

        return features.cpu().numpy().flatten().astype(np.float32)

    def encode_images_batch(self, images: List[np.ndarray]) -> np.ndarray:
        """
        Encode a batch of RGB images into an L2-normalized embedding matrix.

        Args:
            images: List of RGB images as numpy arrays (H, W, 3).

        Returns:
            L2-normalized embedding matrix of shape (N, 512).
        """
        if not images:
            return np.empty((0, self.vector_dim), dtype=np.float32)

        tensors = []
        for img in images:
            pil_image = Image.fromarray(img.astype(np.uint8))
            tensors.append(self._preprocess(pil_image))

        batch = torch.stack(tensors).to(self._device)

        with torch.no_grad():
            features = self._model.encode_image(batch)
            features = features / features.norm(dim=-1, keepdim=True)

        return features.cpu().numpy().astype(np.float32)

    @property
    def model_name(self) -> str:
        return "remoteclip-vit-b-32"

    @property
    def model_version(self) -> str:
        return "remoteclip-vit-b-32-v1"

    @property
    def vector_dim(self) -> int:
        return 512

    @property
    def device(self) -> str:
        return self._device


# Alias for backwards compatibility
CLIPEmbeddingModel = RemoteCLIPEmbeddingModel
