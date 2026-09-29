"""
GeoNexa — Vector Index Builder.

Loads satellite tile chips from SQLite / local tiles directory,
generates L2-normalized image embeddings using local RemoteCLIP ViT-B-32,
populates the FAISS IndexFlatIP vector store, updates SQLite embedding records,
and writes the index manifest.

Usage:
    python scripts/build_index.py --model remoteclip-vit-b-32
"""

import argparse
import hashlib
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

# Add backend directory to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.config import get_settings
from app.db import init_db, get_connection, get_db_path
from app.embeddings.manager import get_embedding_model
from app.retrieval.vector_store import VectorStore
from app.retrieval.search import _load_tile_image

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("geonexa.build_index")


def compute_content_hash(file_path: Path) -> str:
    """Compute SHA-256 hash of the tile image file."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def run_build_index(
    batch_size: int = 32,
    force_rebuild: bool = False,
    model_path: str = None,
    index_path: str = None,
):
    settings = get_settings()
    db_path = get_db_path()
    init_db(db_path)

    # Allow custom model checkpoint and index location
    if model_path:
        from app.embeddings.clip_model import RemoteCLIPEmbeddingModel
        model = RemoteCLIPEmbeddingModel(model_path=model_path, device=settings.device)
    else:
        model = get_embedding_model()

    target_index_path = index_path or settings.faiss_index_path
    if force_rebuild and Path(target_index_path).exists():
        logger.info("Force rebuild requested. Removing existing index...")
        os.remove(target_index_path)
        id_map_path = Path(target_index_path).with_suffix(".idmap.json")
        if id_map_path.exists():
            os.remove(id_map_path)

    vector_store = VectorStore(dimension=512, index_path=target_index_path)

    # 1. Fetch all tiles from SQLite
    with get_connection(db_path) as conn:
        rows = conn.execute("SELECT tile_id, scene_id, file_path FROM tiles ORDER BY tile_id").fetchall()

    if not rows:
        logger.warning("No tiles found in database. Please run scripts/ingest.py first.")
        return

    logger.info(f"Found {len(rows)} total tiles in archive to index.")

    # 2. Check already indexed tiles
    with get_connection(db_path) as conn:
        existing_embeddings = conn.execute(
            "SELECT tile_id FROM embeddings WHERE model_name = ?", (model.model_name,)
        ).fetchall()
        indexed_tile_ids = {r[0] for r in existing_embeddings}

    tiles_to_process = [r for r in rows if r["tile_id"] not in indexed_tile_ids or force_rebuild]
    logger.info(f"Tiles requiring embedding: {len(tiles_to_process)} / {len(rows)}")

    if not tiles_to_process:
        logger.info("All tiles are already indexed in FAISS and SQLite.")
        return

    now = datetime.now(timezone.utc).isoformat()
    total_embedded = 0
    start_time = time.perf_counter()

    # Process in batches
    for i in range(0, len(tiles_to_process), batch_size):
        batch = tiles_to_process[i:i + batch_size]
        batch_images = []
        batch_tile_ids = []
        batch_hashes = []

        for item in batch:
            tile_path = Path(item["file_path"])
            if not tile_path.exists():
                logger.warning(f"Tile file missing: {tile_path}")
                continue

            img = _load_tile_image(str(tile_path))
            if img is not None:
                batch_images.append(img)
                batch_tile_ids.append(item["tile_id"])
                batch_hashes.append(compute_content_hash(tile_path))

        if not batch_images:
            continue

        # Embed batch
        vectors = model.encode_images_batch(batch_images)

        # Add to FAISS VectorStore
        assigned_faiss_ids = vector_store.add(vectors, batch_tile_ids)

        # Register in SQLite embeddings and index_manifest tables
        with get_connection(db_path) as conn:
            for tid, fid, chash in zip(batch_tile_ids, assigned_faiss_ids, batch_hashes):
                conn.execute(
                    """
                    INSERT OR REPLACE INTO embeddings (
                        tile_id, model_name, model_version, vector_dim, faiss_index_id, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (tid, model.model_name, model.model_version, model.vector_dim, fid, now),
                )
                conn.execute(
                    """
                    INSERT OR REPLACE INTO index_manifest (
                        tile_id, content_hash, embedding_model, embedding_version, indexed_at
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (tid, chash, model.model_name, model.model_version, now),
                )
            conn.commit()

        total_embedded += len(batch_tile_ids)
        logger.info(f"Indexed batch: {total_embedded}/{len(tiles_to_process)} tiles.")

    # Save FAISS index
    vector_store.save()
    elapsed = time.perf_counter() - start_time
    logger.info(f"Index build complete. Total vectors in FAISS: {vector_store.size} (Time: {elapsed:.2f}s)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GeoNexa FAISS Vector Index Builder")
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--force-rebuild", action="store_true", help="Rebuild entire FAISS index from scratch")
    parser.add_argument("--model-path", type=str, default=None, help="Path to custom model weights or fine-tuned checkpoint")
    parser.add_argument("--index-path", type=str, default=None, help="Path to output FAISS index file")
    args = parser.parse_args()

    run_build_index(
        batch_size=args.batch_size,
        force_rebuild=args.force_rebuild,
        model_path=args.model_path,
        index_path=args.index_path,
    )
