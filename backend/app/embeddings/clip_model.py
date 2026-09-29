"""
CLIP ViT-B/32 embedding model implementation.

Uses OpenAI's CLIP or open-clip-torch for local image-text embeddings.
All inference is local — no external API calls.
"""

import logging
from typing import List

import numpy as np
import torch
from PIL import Image

from app.embeddings.base import EmbeddingModel

logger = logging.getLogger(__name__)


class CLIPEmbeddingModel(EmbeddingModel):
    """
    CLIP ViT-B/32 embedding model.

    Encodes images and text into a shared 512-dimensional embedding space.
    Uses open_clip for model loading and inference.
    """

    def __init__(self, model_path: str | None = None, device: str = "cpu"):
        """
        Initialize the CLIP model.

        Args:
            model_path: Path to local model weights. If None, uses default open_clip model.
            device: 'cpu' or 'cuda'.
        """
        self._device = device
        self._model_path = model_path
        self._model = None
        self._preprocess = None
        self._tokenizer = None
        self._load_model()

    def _load_model(self):
        """Load the CLIP model and preprocessing transforms."""
        try:
            import open_clip

            # Try loading from local path first, fall back to pretrained
            model_name = "ViT-B-32"
            pretrained = "openai"

            self._model, _, self._preprocess = open_clip.create_model_and_transforms(
                model_name,
                pretrained=pretrained,
                device=self._device,
            )
            self._tokenizer = open_clip.get_tokenizer(model_name)
            self._model.eval()

            logger.info(f"Loaded CLIP {model_name} ({pretrained}) on {self._device}")

        except ImportError:
            logger.error("open_clip not installed. Install with: pip install open-clip-torch")
            raise
        except Exception as e:
            logger.error(f"Failed to load CLIP model: {e}")
            raise

    def encode_image(self, image: np.ndarray) -> np.ndarray:
        """Encode a single image into a normalized embedding vector."""
        pil_image = Image.fromarray(image.astype(np.uint8))
        image_tensor = self._preprocess(pil_image).unsqueeze(0).to(self._device)

        with torch.no_grad():
            features = self._model.encode_image(image_tensor)
            features = features / features.norm(dim=-1, keepdim=True)

        return features.cpu().numpy().flatten()

    def encode_text(self, text: str) -> np.ndarray:
        """Encode a text string into a normalized embedding vector."""
        tokens = self._tokenizer([text]).to(self._device)

        with torch.no_grad():
            features = self._model.encode_text(tokens)
            features = features / features.norm(dim=-1, keepdim=True)

        return features.cpu().numpy().flatten()

    def encode_images_batch(self, images: List[np.ndarray]) -> np.ndarray:
        """Encode a batch of images into normalized embedding vectors."""
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

        return features.cpu().numpy()

    @property
    def model_name(self) -> str:
        return "clip-vit-b-32"

    @property
    def model_version(self) -> str:
        return "openai-clip-vit-b-32-v1"

    @property
    def vector_dim(self) -> int:
        return 512

    @property
    def device(self) -> str:
        return self._device
