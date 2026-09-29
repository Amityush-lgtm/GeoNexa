"""
GeoNexa — Incremental Ingestion Script.

Performs hash-aware incremental indexing:
1. Calculates SHA-256 content hashes of all tiles in the archive.
2. Checks against SQLite index_manifest table.
3. Skips tiles whose content and embedding model have not changed.
4. Generates embeddings only for NEW or MODIFIED tiles.
5. Appends new vectors to FAISS and updates SQLite.

Usage:
    python scripts/incremental_ingest.py
"""

import argparse
import hashlib
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Add backend directory to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.config import get_settings
from app.db import init_db, get_connection, get_db_path
from app.embeddings.manager import get_embedding_model
from app.retrieval.vector_store import get_vector_store
from app.retrieval.search import _load_tile_image

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("geonexa.incremental")


def compute_content_hash(file_path: Path) -> str:
    """Compute SHA-256 hash of a file's content."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def run_incremental_ingest(batch_size: int = 32):
    settings = get_settings()
    db_path = get_db_path()
    init_db(db_path)

    # 1. Fetch current tile records from DB
    with get_connection(db_path) as conn:
        all_tiles = conn.execute("SELECT tile_id, scene_id, file_path FROM tiles").fetchall()
        manifest_rows = conn.execute(
            "SELECT tile_id, content_hash, embedding_model, embedding_version FROM index_manifest"
        ).fetchall()

    manifest_map = {r["tile_id"]: dict(r) for r in manifest_rows}
    model = get_embedding_model()
    vector_store = get_vector_store()

    logger.info(f"Checking {len(all_tiles)} tiles against incremental manifest ({len(manifest_map)} indexed entries)...")

    new_tiles = []
    modified_tiles = []
    skipped_count = 0

    for tile in all_tiles:
        tid = tile["tile_id"]
        tile_path = Path(tile["file_path"])
        if not tile_path.exists():
            continue

        chash = compute_content_hash(tile_path)
        existing = manifest_map.get(tid)

        if existing is None:
            new_tiles.append((tile, chash))
        elif existing["content_hash"] != chash or existing["embedding_model"] != model.model_name:
            modified_tiles.append((tile, chash))
        else:
            skipped_count += 1

    logger.info(
        f"Incremental Ingestion Summary:\n"
        f"  - Unchanged (Skipped): {skipped_count}\n"
        f"  - New Tiles: {len(new_tiles)}\n"
        f"  - Modified Tiles: {len(modified_tiles)}"
    )

    tiles_to_process = new_tiles + modified_tiles
    if not tiles_to_process:
        logger.info("Archive is fully synchronized. No new embeddings required.")
        return

    now = datetime.now(timezone.utc).isoformat()
    processed_count = 0

    for i in range(0, len(tiles_to_process), batch_size):
        batch = tiles_to_process[i:i + batch_size]
        batch_images = []
        batch_tile_ids = []
        batch_hashes = []

        for tile, chash in batch:
            tile_path = Path(tile["file_path"])
            img = _load_tile_image(str(tile_path))
            if img is not None:
                batch_images.append(img)
                batch_tile_ids.append(tile["tile_id"])
                batch_hashes.append(chash)

        if not batch_images:
            continue

        vectors = model.encode_images_batch(batch_images)
        assigned_fids = vector_store.add(vectors, batch_tile_ids)

        with get_connection(db_path) as conn:
            for tid, fid, chash in zip(batch_tile_ids, assigned_fids, batch_hashes):
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

        processed_count += len(batch_tile_ids)
        logger.info(f"Incrementally indexed {processed_count}/{len(tiles_to_process)} tiles.")

    vector_store.save()
    logger.info(f"Incremental ingestion complete. Total FAISS vector count: {vector_store.size}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GeoNexa Incremental Ingestion")
    parser.add_argument("--batch-size", type=int, default=32)
    args = parser.parse_args()

    run_incremental_ingest(batch_size=args.batch_size)
