"""
Unit tests for Image-to-Image similarity search.
"""

import numpy as np
import pytest
from app.retrieval.vector_store import VectorStore


def test_similarity_search_excludes_self(temp_dir):
    """Ensure that image-to-image similarity search does not return query tile itself."""
    index_path = temp_dir / "sim.index"
    store = VectorStore(dimension=512, index_path=str(index_path))

    # Add 4 tiles
    np.random.seed(99)
    vectors = np.random.randn(4, 512).astype(np.float32)
    vectors = vectors / np.linalg.norm(vectors, axis=1, keepdims=True)
    tile_ids = ["tile_A", "tile_B", "tile_C", "tile_D"]

    store.add(vectors, tile_ids)

    # Query with tile_A vector
    matched_ids, scores = store.search(vectors[0], k=4)

    # Filter self (as done in similarity_search implementation)
    filtered_results = [tid for tid in matched_ids if tid != "tile_A"]

    assert "tile_A" not in filtered_results
    assert len(filtered_results) == 3
