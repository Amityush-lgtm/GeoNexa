"""
Unit tests for incremental ingestion and content hash manifest tracking.
"""

import hashlib
from pathlib import Path
import pytest
from app.db import init_db, get_connection


def test_incremental_manifest_tracking(temp_dir):
    db_path = temp_dir / "meta.db"
    init_db(db_path)

    # 1. Register 3 tiles in index_manifest
    with get_connection(db_path) as conn:
        for i in range(3):
            conn.execute(
                """
                INSERT INTO index_manifest (tile_id, content_hash, embedding_model, embedding_version, indexed_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (f"tile_{i}", f"hash_{i}", "remoteclip-vit-b-32", "remoteclip-vit-b-32-v1", "2026-01-15T00:00:00Z"),
            )
        conn.commit()

    # 2. Check query
    with get_connection(db_path) as conn:
        rows = conn.execute("SELECT tile_id, content_hash FROM index_manifest").fetchall()
        manifest_map = {r["tile_id"]: r["content_hash"] for r in rows}

    assert len(manifest_map) == 3
    assert manifest_map["tile_0"] == "hash_0"
    assert manifest_map["tile_1"] == "hash_1"
    assert manifest_map["tile_2"] == "hash_2"

    # Test logic for new vs existing
    new_tiles = ["tile_0", "tile_1", "tile_2", "tile_3"]
    to_embed = [t for t in new_tiles if t not in manifest_map]

    assert to_embed == ["tile_3"]
