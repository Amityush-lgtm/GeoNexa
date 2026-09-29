"""
GeoNexa — Scene Ingestion Script.

Ingests raw Sentinel-2 GeoTIFF scenes, validates bands and CRS,
generates 256x256 georeferenced chips with spatial metadata,
and updates the SQLite database and scenes manifest CSV.

Usage:
    python scripts/ingest.py --data-dir data/public/raw/sentinel2
"""

import argparse
import csv
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add backend directory to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.config import get_settings
from app.db import init_db, get_connection, get_db_path
from app.archive.metadata import extract_metadata, validate_scene, generate_scene_id
from app.archive.tiler import tile_scene

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("geonexa.ingest")


def update_scenes_csv(manifest_path: Path, scene_record: dict):
    """Append or update scene entry in data/public/manifests/scenes.csv."""
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "scene_id",
        "product_id",
        "source",
        "sensor",
        "acquisition_datetime",
        "crs",
        "bbox",
        "width",
        "height",
        "band_count",
        "file_path",
        "file_size_bytes",
        "source_reference",
        "license",
        "downloaded_at",
        "processing_version",
    ]

    existing_rows = []
    if manifest_path.exists():
        with open(manifest_path, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            existing_rows = [r for r in reader if r.get("scene_id") != scene_record["scene_id"]]

    existing_rows.append(scene_record)

    with open(manifest_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(existing_rows)


def run_ingest(raw_dir: Path, output_tiles_dir: Path, manifest_path: Path):
    settings = get_settings()
    db_path = get_db_path()
    init_db(db_path)

    if not raw_dir.exists():
        logger.error(f"Source raw directory does not exist: {raw_dir}")
        sys.exit(1)

    tiff_files = sorted(list(raw_dir.glob("*.tif")) + list(raw_dir.glob("*.tiff")))
    if not tiff_files:
        logger.warning(f"No GeoTIFF (.tif/.tiff) files found in {raw_dir}")
        return

    logger.info(f"Found {len(tiff_files)} GeoTIFF scenes to ingest from {raw_dir}")

    total_tiles_created = 0
    now = datetime.now(timezone.utc).isoformat()

    for scene_file in tiff_files:
        logger.info(f"Processing scene: {scene_file.name}")
        val = validate_scene(scene_file)
        if not val["valid"]:
            logger.error(f"Validation failed for {scene_file.name}: {val['errors']}")
            continue

        meta = extract_metadata(scene_file)
        scene_id = generate_scene_id(scene_file, sensor=meta.get("sensor"), date=meta.get("acquisition_date"))

        # Check existing scene
        with get_connection(db_path) as conn:
            existing = conn.execute("SELECT scene_id FROM scenes WHERE scene_id = ?", (scene_id,)).fetchone()
            if existing:
                logger.info(f"Scene {scene_id} already exists in database. Checking tiles...")
                cursor = conn.execute("SELECT COUNT(*) FROM tiles WHERE scene_id = ?", (scene_id,))
                cnt = cursor.fetchone()[0]
                if cnt > 0:
                    logger.info(f"Scene {scene_id} already has {cnt} tiles indexed. Skipping.")
                    continue

        # Tile scene
        scene_tile_dir = output_tiles_dir / scene_id
        tiles = tile_scene(
            scene_path=scene_file,
            scene_id=scene_id,
            output_dir=scene_tile_dir,
            tile_size=settings.tile_size,
            overlap=settings.tile_overlap,
        )

        # Register in SQLite
        with get_connection(db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO scenes (
                    scene_id, file_path, sensor, acquisition_date, crs,
                    bounds_minx, bounds_miny, bounds_maxx, bounds_maxy,
                    width, height, band_count, file_size_bytes,
                    ingested_at, processing_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    scene_id,
                    str(scene_file.resolve()),
                    meta.get("sensor", "Sentinel-2 MSI"),
                    meta.get("acquisition_date", "2026-01-15"),
                    meta.get("crs", "EPSG:4326"),
                    meta.get("bounds_minx"),
                    meta.get("bounds_miny"),
                    meta.get("bounds_maxx"),
                    meta.get("bounds_maxy"),
                    meta.get("width"),
                    meta.get("height"),
                    meta.get("band_count"),
                    meta.get("file_size_bytes"),
                    now,
                    "0.1.0",
                ),
            )

            for t in tiles:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO tiles (
                        tile_id, scene_id, file_path, x_index, y_index,
                        crs, bounds_minx, bounds_miny, bounds_maxx, bounds_maxy,
                        center_lat, center_lon, width, height, band_count,
                        created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        t["tile_id"],
                        t["scene_id"],
                        t["file_path"],
                        t["x_index"],
                        t["y_index"],
                        t.get("crs"),
                        t.get("bounds_minx"),
                        t.get("bounds_miny"),
                        t.get("bounds_maxx"),
                        t.get("bounds_maxy"),
                        t.get("center_lat"),
                        t.get("center_lon"),
                        t["width"],
                        t["height"],
                        t.get("band_count"),
                        now,
                    ),
                )
            conn.commit()

        # Update CSV manifest
        scene_record = {
            "scene_id": scene_id,
            "product_id": f"S2_{scene_id}",
            "source": "Copernicus Data Space Ecosystem",
            "sensor": meta.get("sensor", "Sentinel-2 MSI"),
            "acquisition_datetime": meta.get("acquisition_date", "2026-01-15"),
            "crs": meta.get("crs", "EPSG:4326"),
            "bbox": f"[{meta.get('bounds_minx')},{meta.get('bounds_miny')},{meta.get('bounds_maxx')},{meta.get('bounds_maxy')}]",
            "width": meta.get("width"),
            "height": meta.get("height"),
            "band_count": meta.get("band_count"),
            "file_path": str(scene_file.resolve()),
            "file_size_bytes": meta.get("file_size_bytes"),
            "source_reference": "https://dataspace.copernicus.eu/",
            "license": "CC-BY-4.0 (Copernicus Open Access)",
            "downloaded_at": now,
            "processing_version": "0.1.0",
        }
        update_scenes_csv(manifest_path, scene_record)

        total_tiles_created += len(tiles)
        logger.info(f"Completed scene {scene_id} -> {len(tiles)} chips created.")

    logger.info(f"Ingestion finished. Total tiles created across all scenes: {total_tiles_created}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GeoNexa Satellite Scene Ingestion")
    parser.add_argument("--data-dir", type=Path, default=PROJECT_ROOT / "data" / "public" / "raw" / "sentinel2")
    parser.add_argument("--tiles-dir", type=Path, default=PROJECT_ROOT / "data" / "public" / "tiles")
    parser.add_argument("--manifest", type=Path, default=PROJECT_ROOT / "data" / "public" / "manifests" / "scenes.csv")
    args = parser.parse_args()

    run_ingest(args.data_dir, args.tiles_dir, args.manifest)
