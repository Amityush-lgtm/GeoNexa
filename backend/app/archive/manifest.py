"""
Index manifest for incremental ingestion.

Tracks which tiles have been embedded/indexed and with which model,
allowing the system to skip unchanged tiles and re-embed only when
the content or model changes.
"""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.archive.ingestion import compute_content_hash
from app.db import get_connection, get_db_path

logger = logging.getLogger(__name__)


def should_index_tile(
    tile_id: str,
    tile_path: str | Path,
    embedding_model: str,
    embedding_version: str,
) -> bool:
    """
    Check whether a tile needs (re-)indexing.

    Returns True if:
    - Tile is not in the manifest
    - Tile content has changed (different hash)
    - Embedding model/version has changed

    Returns False if:
    - Same tile + same hash + same model → skip
    """
    content_hash = compute_content_hash(tile_path)

    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT content_hash, embedding_model, embedding_version
            FROM index_manifest
            WHERE tile_id = ? AND embedding_model = ?
            """,
            (tile_id, embedding_model),
        ).fetchone()

    if row is None:
        return True  # Not indexed yet

    if row["content_hash"] != content_hash:
        logger.info(f"Tile {tile_id}: content changed, will re-index")
        return True

    if row["embedding_version"] != embedding_version:
        logger.info(f"Tile {tile_id}: embedding version changed, will re-index")
        return True

    return False  # Already indexed with same content and model


def record_indexed(
    tile_id: str,
    tile_path: str | Path,
    embedding_model: str,
    embedding_version: str,
) -> None:
    """Record that a tile has been successfully indexed."""
    content_hash = compute_content_hash(tile_path)
    now = datetime.now(timezone.utc).isoformat()

    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO index_manifest
                (tile_id, content_hash, embedding_model, embedding_version, indexed_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (tile_id, content_hash, embedding_model, embedding_version, now),
        )
        conn.commit()


def get_manifest_stats() -> dict:
    """Get manifest statistics."""
    with get_connection() as conn:
        total = conn.execute("SELECT COUNT(*) FROM index_manifest").fetchone()[0]
        models = conn.execute(
            "SELECT DISTINCT embedding_model, embedding_version FROM index_manifest"
        ).fetchall()

    return {
        "total_indexed": total,
        "models": [{"model": r[0], "version": r[1]} for r in models],
    }
