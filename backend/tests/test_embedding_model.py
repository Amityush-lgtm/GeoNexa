"""
Unit tests for RemoteCLIP Embedding Model.
"""

import numpy as np
import pytest
from app.embeddings.clip_model import RemoteCLIPEmbeddingModel


class MockRemoteCLIP(RemoteCLIPEmbeddingModel):
    """Subclass that bypasses loading for unit testing shape & normalization."""

    def __init__(self):
        self._device = "cpu"
        self._model_path = None

    def _load_model(self):
        pass

    def encode_image(self, image: np.ndarray) -> np.ndarray:
        np.random.seed(int(image.mean()) % 1000)
        vec = np.random.randn(512).astype(np.float32)
        return vec / np.linalg.norm(vec)

    def encode_text(self, text: str) -> np.ndarray:
        np.random.seed(abs(hash(text)) % 10000)
        vec = np.random.randn(512).astype(np.float32)
        return vec / np.linalg.norm(vec)

    def encode_images_batch(self, images):
        return np.stack([self.encode_image(img) for img in images])


def test_embedding_model_properties():
    model = MockRemoteCLIP()
    assert model.model_name == "remoteclip-vit-b-32"
    assert model.model_version == "remoteclip-vit-b-32-v1"
    assert model.vector_dim == 512
    assert model.device == "cpu"


def test_embedding_normalization_and_dimension(sample_tile_array):
    model = MockRemoteCLIP()
    # Image embedding
    rgb_img = np.transpose(sample_tile_array[:3], (1, 2, 0))
    vec = model.encode_image(rgb_img)

    assert vec.shape == (512,)
    assert pytest.approx(np.linalg.norm(vec), rel=1e-3) == 1.0

    # Text embedding
    txt_vec = model.encode_text("urban buildings near water")
    assert txt_vec.shape == (512,)
    assert pytest.approx(np.linalg.norm(txt_vec), rel=1e-3) == 1.0


def test_missing_checkpoint_raises_file_not_found(temp_dir):
    missing_path = temp_dir / "non_existent_model.pt"
    with pytest.raises(FileNotFoundError):
        RemoteCLIPEmbeddingModel(model_path=missing_path)
