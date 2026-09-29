"""
FAISS vector store wrapper.

Wraps FAISS index operations (add, search, save, load) and manages
the mapping between FAISS internal IDs and tile IDs via SQLite.
"""

import json
import logging
from pathlib import Path
from typing import Optional, Tuple, List

import faiss
import numpy as np

from app.config import get_settings

logger = logging.getLogger(__name__)


class VectorStore:
    """
    FAISS-based vector store for tile embeddings.

    Uses IndexFlatIP (inner product on L2-normalized vectors = cosine similarity).
    FAISS IDs map to tile_ids via the embeddings table in SQLite.
    """

    def __init__(self, dimension: int = 512, index_path: str | None = None):
        """
        Initialize the vector store.

        Args:
            dimension: Embedding vector dimensionality.
            index_path: Path to load/save the FAISS index file.
        """
        self.dimension = dimension
        self.index_path = index_path or get_settings().faiss_index_path
        self._id_map_path = str(Path(self.index_path).with_suffix(".idmap.json"))

        # ID mapping: FAISS sequential ID -> tile_id
        self._id_to_tile: dict[int, str] = {}
        self._tile_to_id: dict[str, int] = {}
        self._next_id: int = 0

        # Create or load index
        if Path(self.index_path).exists():
            self.load()
        else:
            self.index = faiss.IndexFlatIP(dimension)
            logger.info(f"Created new FAISS IndexFlatIP (dim={dimension})")

    def add(self, vectors: np.ndarray, tile_ids: List[str]) -> List[int]:
        """
        Add vectors to the index.

        Args:
            vectors: L2-normalized vectors of shape (N, dimension).
            tile_ids: Corresponding tile IDs.

        Returns:
            List of assigned FAISS index IDs.
        """
        if len(vectors) != len(tile_ids):
            raise ValueError(f"Vector count ({len(vectors)}) != tile ID count ({len(tile_ids)})")

        vectors = np.ascontiguousarray(vectors, dtype=np.float32)

        new_vectors_list = []
        assigned_ids = []

        for vec, tile_id in zip(vectors, tile_ids):
            if tile_id in self._tile_to_id:
                # Already indexed — return existing mapping ID without duplicating in FAISS
                assigned_ids.append(self._tile_to_id[tile_id])
                continue

            fid = self._next_id
            self._id_to_tile[fid] = tile_id
            self._tile_to_id[tile_id] = fid
            assigned_ids.append(fid)
            new_vectors_list.append(vec)
            self._next_id += 1

        if new_vectors_list:
            new_vectors = np.ascontiguousarray(np.stack(new_vectors_list), dtype=np.float32)
            self.index.add(new_vectors)
            logger.info(f"Added {len(new_vectors)} new vectors to index (total: {self.size})")
        else:
            logger.info(f"No new vectors to add (all {len(tile_ids)} tiles were already indexed)")

        return assigned_ids


    def search(self, query_vector: np.ndarray, k: int = 20) -> Tuple[List[str], np.ndarray]:
        """
        Search for the k nearest neighbors.

        Args:
            query_vector: L2-normalized query vector of shape (dimension,) or (1, dimension).
            k: Number of results to return.

        Returns:
            Tuple of (tile_ids, similarity_scores).
        """
        if self.size == 0:
            return [], np.array([])

        query = query_vector.reshape(1, -1).astype(np.float32)
        k = min(k, self.size)

        scores, indices = self.index.search(query, k)

        tile_ids = []
        valid_scores = []
        for idx, score in zip(indices[0], scores[0]):
            if idx >= 0 and idx in self._id_to_tile:
                tile_ids.append(self._id_to_tile[idx])
                valid_scores.append(float(score))

        return tile_ids, np.array(valid_scores)

    def get_vector(self, tile_id: str) -> Optional[np.ndarray]:
        """Get the stored vector for a tile ID."""
        if tile_id not in self._tile_to_id:
            return None

        fid = self._tile_to_id[tile_id]
        if fid < self.index.ntotal:
            return faiss.rev_swig_ptr(
                self.index.get_xb() + fid * self.dimension, self.dimension
            ).copy()

        return None

    def save(self, path: str | None = None) -> None:
        """Save the FAISS index and ID mapping to disk."""
        path = path or self.index_path
        Path(path).parent.mkdir(parents=True, exist_ok=True)

        faiss.write_index(self.index, str(path))

        # Save ID mapping
        id_map_path = str(Path(path).with_suffix(".idmap.json"))
        with open(id_map_path, "w") as f:
            json.dump({
                "id_to_tile": {str(k): v for k, v in self._id_to_tile.items()},
                "next_id": self._next_id,
            }, f)

        logger.info(f"Saved FAISS index ({self.size} vectors) to {path}")

    def load(self, path: str | None = None) -> None:
        """Load the FAISS index and ID mapping from disk."""
        path = path or self.index_path

        if not Path(path).exists():
            raise FileNotFoundError(f"FAISS index not found: {path}")

        self.index = faiss.read_index(str(path))

        # Load ID mapping
        id_map_path = str(Path(path).with_suffix(".idmap.json"))
        if Path(id_map_path).exists():
            with open(id_map_path, "r") as f:
                data = json.load(f)
                self._id_to_tile = {int(k): v for k, v in data["id_to_tile"].items()}
                self._tile_to_id = {v: int(k) for k, v in data["id_to_tile"].items()}
                self._next_id = data.get("next_id", len(self._id_to_tile))

        logger.info(f"Loaded FAISS index ({self.size} vectors) from {path}")

    @property
    def size(self) -> int:
        """Number of vectors in the index."""
        return self.index.ntotal


# Module-level singleton
_store_instance: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """Get the vector store instance (lazy-loaded singleton)."""
    global _store_instance

    if _store_instance is None:
        settings = get_settings()
        _store_instance = VectorStore(
            dimension=512,  # CLIP ViT-B/32
            index_path=settings.faiss_index_path,
        )

    return _store_instance


def reset_vector_store() -> None:
    """Reset the cached vector store instance."""
    global _store_instance
    _store_instance = None
