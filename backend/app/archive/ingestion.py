"""
Scene ingestion pipeline — validates, extracts metadata, tiles, and registers in DB.

This is the main entry point for adding new satellite imagery to the archive.
"""

import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.archive.metadata import extract_metadata, validate_scene, generate_scene_id
from app.archive.tiler import tile_scene
from app.db import get_connection, get_db_path, init_db

logger = logging.getLogger(__name__)


def ingest_scene(
    scene_path: str | Path,
    sensor_override: str | None = None,
    date_override: str | None = None,
) -> dict:
    """
    Ingest a single GeoTIFF scene into the archive.

    Pipeline:
        1. Validate scene
        2. Extract metadata
        3. Generate scene ID
        4. Tile scene
        5. Register scene + tiles in SQLite
        6. Return ingestion result

    Args:
        scene_path: Path to the GeoTIFF file.
        sensor_override: Override auto-detected sensor name.
        date_override: Override auto-detected acquisition date.

    Returns:
        dict with scene_id, tiles_created, status, message
    """
    scene_path = Path(scene_path)
    now = datetime.now(timezone.utc).isoformat()

    # 1. Validate
    validation = validate_scene(scene_path)
    if not validation["valid"]:
        return {
            "scene_id": None,
            "tiles_created": 0,
            "status": "error",
            "message": f"Validation failed: {'; '.join(validation['errors'])}",
        }

    if validation["warnings"]:
        for w in validation["warnings"]:
            logger.warning(f"Scene {scene_path.name}: {w}")

    # 2. Extract metadata
    try:
        metadata = extract_metadata(scene_path)
    except Exception as e:
        return {
            "scene_id": None,
            "tiles_created": 0,
            "status": "error",
            "message": f"Metadata extraction failed: {e}",
        }

    # Apply overrides
    if sensor_override:
        metadata["sensor"] = sensor_override
    if date_override:
        metadata["acquisition_date"] = date_override

    # 3. Generate scene ID
    scene_id = generate_scene_id(
        scene_path,
        sensor=metadata.get("sensor"),
        date=metadata.get("acquisition_date"),
    )

    # Check for duplicate scene
    db_path = get_db_path()
    init_db(db_path)

    with get_connection(db_path) as conn:
        existing = conn.execute(
            "SELECT scene_id FROM scenes WHERE scene_id = ?", (scene_id,)
        ).fetchone()
        if existing:
            return {
                "scene_id": scene_id,
                "tiles_created": 0,
                "status": "skipped",
                "message": f"Scene {scene_id} already exists in the archive",
            }

    # 4. Tile scene
    try:
        tiles = tile_scene(scene_path, scene_id)
    except Exception as e:
        return {
            "scene_id": scene_id,
            "tiles_created": 0,
            "status": "error",
            "message": f"Tiling failed: {e}",
        }

    # 5. Register in database
    try:
        _register_scene(scene_id, metadata, tiles, now, db_path)
    except Exception as e:
        return {
            "scene_id": scene_id,
            "tiles_created": 0,
            "status": "error",
            "message": f"Database registration failed: {e}",
        }

    logger.info(f"Ingested scene {scene_id}: {len(tiles)} tiles created")
    return {
        "scene_id": scene_id,
        "tiles_created": len(tiles),
        "status": "success",
        "message": f"Successfully ingested {scene_path.name} → {len(tiles)} tiles",
    }


def ingest_directory(
    directory: str | Path,
    sensor_override: str | None = None,
    recursive: bool = False,
) -> list[dict]:
    """Ingest all GeoTIFF files in a directory."""
    directory = Path(directory)
    if not directory.is_dir():
        return [{"scene_id": None, "tiles_created": 0, "status": "error",
                 "message": f"Not a directory: {directory}"}]

    pattern = "**/*.tif" if recursive else "*.tif"
    tiff_files = sorted(directory.glob(pattern))

    # Also include .tiff extension
    tiff_files += sorted(directory.glob(pattern + "f"))

    results = []
    for scene_path in tiff_files:
        result = ingest_scene(scene_path, sensor_override=sensor_override)
        results.append(result)

    total_tiles = sum(r["tiles_created"] for r in results)
    success = sum(1 for r in results if r["status"] == "success")
    logger.info(f"Batch ingestion: {success}/{len(results)} scenes, {total_tiles} tiles total")

    return results


def compute_content_hash(file_path: str | Path) -> str:
    """Compute SHA-256 hash of a file's content for incremental indexing."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def _register_scene(scene_id: str, metadata: dict, tiles: list[dict], now: str, db_path) -> None:
    """Register a scene and its tiles in the database."""
    with get_connection(db_path) as conn:
        # Insert scene
        conn.execute(
            """
            INSERT INTO scenes (
                scene_id, file_path, sensor, acquisition_date, crs,
                bounds_minx, bounds_miny, bounds_maxx, bounds_maxy,
                width, height, band_count, file_size_bytes,
                ingested_at, processing_version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                scene_id,
                metadata["file_path"],
                metadata.get("sensor"),
                metadata.get("acquisition_date"),
                metadata.get("crs"),
                metadata.get("bounds_minx"),
                metadata.get("bounds_miny"),
                metadata.get("bounds_maxx"),
                metadata.get("bounds_maxy"),
                metadata.get("width"),
                metadata.get("height"),
                metadata.get("band_count"),
                metadata.get("file_size_bytes"),
                now,
                "0.1.0",
            ),
        )

        # Insert tiles
        for tile in tiles:
            conn.execute(
                """
                INSERT INTO tiles (
                    tile_id, scene_id, file_path, x_index, y_index,
                    crs, bounds_minx, bounds_miny, bounds_maxx, bounds_maxy,
                    center_lat, center_lon, width, height, band_count,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    tile["tile_id"],
                    tile["scene_id"],
                    tile["file_path"],
                    tile["x_index"],
                    tile["y_index"],
                    tile.get("crs"),
                    tile.get("bounds_minx"),
                    tile.get("bounds_miny"),
                    tile.get("bounds_maxx"),
                    tile.get("bounds_maxy"),
                    tile.get("center_lat"),
                    tile.get("center_lon"),
                    tile["width"],
                    tile["height"],
                    tile.get("band_count"),
                    now,
                ),
            )

        conn.commit()
