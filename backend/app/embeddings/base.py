"""
Abstract embedding model interface.

All embedding models must implement this interface.
The retrieval system depends ONLY on this abstraction — never on a specific model.
"""

from abc import ABC, abstractmethod
from typing import List

import numpy as np


class EmbeddingModel(ABC):
    """
    Abstract base class for image-text embedding models.

    Any model that encodes images and text into a shared vector space
    can implement this interface and be used for semantic retrieval.
    """

    @abstractmethod
    def encode_image(self, image: np.ndarray) -> np.ndarray:
        """
        Encode a single image into a normalized embedding vector.

        Args:
            image: RGB image as numpy array (H, W, 3) with values in [0, 255].

        Returns:
            L2-normalized embedding vector of shape (vector_dim,).
        """
        ...

    @abstractmethod
    def encode_text(self, text: str) -> np.ndarray:
        """
        Encode a text string into a normalized embedding vector.

        Args:
            text: Natural-language text query.

        Returns:
            L2-normalized embedding vector of shape (vector_dim,).
        """
        ...

    @abstractmethod
    def encode_images_batch(self, images: List[np.ndarray]) -> np.ndarray:
        """
        Encode a batch of images into normalized embedding vectors.

        Args:
            images: List of RGB images as numpy arrays (H, W, 3).

        Returns:
            L2-normalized embedding matrix of shape (N, vector_dim).
        """
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Short identifier for the model (e.g., 'clip-vit-b-32')."""
        ...

    @property
    @abstractmethod
    def model_version(self) -> str:
        """Version string for provenance tracking."""
        ...

    @property
    @abstractmethod
    def vector_dim(self) -> int:
        """Dimensionality of the output embedding vectors."""
        ...

    @property
    def device(self) -> str:
        """Device the model runs on (cpu/cuda)."""
        return "cpu"
