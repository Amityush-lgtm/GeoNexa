"""
Embedding model manager — handles model loading, caching, and lifecycle.
"""

import logging
from typing import Optional

from app.embeddings.base import EmbeddingModel
from app.embeddings.clip_model import CLIPEmbeddingModel
from app.config import get_settings

logger = logging.getLogger(__name__)

# Module-level singleton
_model_instance: Optional[EmbeddingModel] = None


def get_embedding_model() -> EmbeddingModel:
    """
    Get the embedding model instance (lazy-loaded singleton).

    The model is loaded once and cached for the lifetime of the process.
    """
    global _model_instance

    if _model_instance is None:
        settings = get_settings()

        logger.info(f"Loading embedding model: {settings.embedding_model} on {settings.device}")

        if settings.embedding_model == "clip-vit-b-32":
            _model_instance = CLIPEmbeddingModel(
                model_path=settings.model_path,
                device=settings.device,
            )
        else:
            raise ValueError(f"Unknown embedding model: {settings.embedding_model}")

    return _model_instance


def reset_model() -> None:
    """Reset the cached model instance (useful for testing or model swap)."""
    global _model_instance
    _model_instance = None
