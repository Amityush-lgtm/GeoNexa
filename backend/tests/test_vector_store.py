"""
Unit tests for FAISS Vector Store.
"""

import numpy as np
import pytest
from app.retrieval.vector_store import VectorStore


def test_vector_store_add_and_search(temp_dir):
    """Test creating index, adding embeddings, and performing cosine search."""
    index_path = temp_dir / "test.index"
    store = VectorStore(index_path=str(index_path), dim=512)

    # Generate 10 random vectors
    np.random.seed(123)
    vectors = np.random.randn(10, 512).astype(np.float32)
    vectors = vectors / np.linalg.norm(vectors, axis=1, keepdims=True)

    # Add to store
    store.add(vectors)
    assert store.total_vectors == 10

    # Save and reload
    store.save()
    assert index_path.exists()

    reloaded_store = VectorStore(index_path=str(index_path), dim=512)
    assert reloaded_store.total_vectors == 10

    # Search with first vector (should match index 0 with score ~1.0)
    query = vectors[0]
    scores, indices = reloaded_store.search(query, top_k=3)

    assert len(scores) == 3
    assert len(indices) == 3
    assert indices[0] == 0
    assert pytest.approx(scores[0], 0.001) == 1.0
