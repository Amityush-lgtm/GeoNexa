"""
Unit tests for FAISS Vector Store and 1:1 ID mapping invariants.
"""

import numpy as np
import pytest
from app.retrieval.vector_store import VectorStore


def test_vector_store_add_search_and_deduplication(temp_dir):
    index_path = temp_dir / "test.index"
    store = VectorStore(dimension=512, index_path=str(index_path))

    # Generate 5 random normalized vectors
    np.random.seed(42)
    vectors = np.random.randn(5, 512).astype(np.float32)
    vectors = vectors / np.linalg.norm(vectors, axis=1, keepdims=True)
    tile_ids = [f"tile_{i}" for i in range(5)]

    # Add 5 tiles
    assigned_ids = store.add(vectors, tile_ids)
    assert len(assigned_ids) == 5
    assert store.size == 5

    # Test duplicate insertion: adding tile_0 and tile_1 again must NOT increase FAISS size
    dup_vectors = vectors[:2]
    dup_tile_ids = tile_ids[:2]
    dup_assigned_ids = store.add(dup_vectors, dup_tile_ids)
    assert dup_assigned_ids == [0, 1]
    assert store.size == 5  # Must remain 5!

    # Test adding new tiles (tile_5, tile_6)
    new_vectors = np.random.randn(2, 512).astype(np.float32)
    new_vectors = new_vectors / np.linalg.norm(new_vectors, axis=1, keepdims=True)
    new_tile_ids = ["tile_5", "tile_6"]
    new_assigned_ids = store.add(new_vectors, new_tile_ids)
    assert new_assigned_ids == [5, 6]
    assert store.size == 7

    # Save and reload from disk
    store.save()
    assert index_path.exists()

    reloaded = VectorStore(dimension=512, index_path=str(index_path))
    assert reloaded.size == 7

    # Search with tile_0's vector
    matched_ids, scores = reloaded.search(vectors[0], k=3)
    assert len(matched_ids) == 3
    assert matched_ids[0] == "tile_0"
    assert pytest.approx(scores[0], rel=1e-3) == 1.0
