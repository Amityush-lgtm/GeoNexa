"""
Archive API routes — scene ingestion, tile retrieval, archive stats.
"""

import io
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.archive.ingestion import ingest_scene, ingest_directory
from app.db import get_connection, execute_query
from app.models.schemas import (
    IngestRequest, BatchIngestRequest, IngestResponse,
    ArchiveStats, TileInfo, SceneInfo,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/ingest", response_model=IngestResponse)
async def ingest(request: IngestRequest):
    """Ingest a single GeoTIFF scene into the archive."""
    result = ingest_scene(
        request.scene_path,
        sensor_override=request.sensor,
        date_override=request.acquisition_date,
    )
    return IngestResponse(
        scene_id=result.get("scene_id", ""),
        tiles_created=result["tiles_created"],
        status=result["status"],
        message=result["message"],
    )


@router.post("/ingest/batch")
async def ingest_batch(request: BatchIngestRequest):
    """Ingest all GeoTIFF files in a directory."""
    results = ingest_directory(
        request.directory,
        sensor_override=request.sensor,
        recursive=request.recursive,
    )
    return {
        "results": results,
        "total": len(results),
        "success": sum(1 for r in results if r["status"] == "success"),
        "tiles_created": sum(r["tiles_created"] for r in results),
    }


@router.get("/stats", response_model=ArchiveStats)
async def get_stats():
    """Get archive statistics."""
    with get_connection() as conn:
        total_scenes = conn.execute("SELECT COUNT(*) FROM scenes").fetchone()[0]
        total_tiles = conn.execute("SELECT COUNT(*) FROM tiles").fetchone()[0]
        total_embeddings = conn.execute("SELECT COUNT(*) FROM embeddings").fetchone()[0]

        sensors = [
            row[0] for row in
            conn.execute("SELECT DISTINCT sensor FROM scenes WHERE sensor IS NOT NULL").fetchall()
        ]

        date_range_row = conn.execute(
            "SELECT MIN(acquisition_date), MAX(acquisition_date) FROM scenes WHERE acquisition_date IS NOT NULL"
        ).fetchone()

    # Get FAISS index size
    try:
        from app.retrieval.vector_store import get_vector_store
        store = get_vector_store()
        index_size = store.size
    except Exception:
        index_size = 0

    date_range = None
    if date_range_row and date_range_row[0]:
        date_range = {"earliest": date_range_row[0], "latest": date_range_row[1]}

    return ArchiveStats(
        total_scenes=total_scenes,
        total_tiles=total_tiles,
        total_embeddings=total_embeddings,
        index_size=index_size,
        sensors=sensors,
        date_range=date_range,
    )


@router.get("/tiles/{tile_id}")
async def get_tile(tile_id: str):
    """Get tile metadata."""
    rows = execute_query(
        """
        SELECT t.*, s.sensor, s.acquisition_date
        FROM tiles t
        JOIN scenes s ON t.scene_id = s.scene_id
        WHERE t.tile_id = ?
        """,
        (tile_id,),
    )

    if not rows:
        raise HTTPException(status_code=404, detail=f"Tile {tile_id} not found")

    row = rows[0]
    return {
        **row,
        "image_url": f"/api/archive/tiles/{tile_id}/image",
    }


@router.get("/tiles/{tile_id}/image")
async def get_tile_image(tile_id: str):
    """Get tile image as PNG."""
    rows = execute_query("SELECT file_path FROM tiles WHERE tile_id = ?", (tile_id,))

    if not rows:
        raise HTTPException(status_code=404, detail=f"Tile {tile_id} not found")

    file_path = rows[0]["file_path"]

    if not Path(file_path).exists():
        raise HTTPException(status_code=404, detail=f"Tile image file not found")

    try:
        import rasterio
        import numpy as np
        from PIL import Image as PILImage

        with rasterio.open(file_path) as ds:
            bands = min(ds.count, 3)
            data = ds.read(list(range(1, bands + 1)))

            if bands == 1:
                data = np.repeat(data, 3, axis=0)
            elif bands == 2:
                data = np.concatenate([data, np.zeros_like(data[:1])], axis=0)

            image = np.transpose(data, (1, 2, 0))

            if image.dtype != np.uint8:
                valid = image[image > 0] if image.any() else image.ravel()
                if len(valid) > 0:
                    vmin, vmax = np.percentile(valid, [2, 98])
                else:
                    vmin, vmax = 0, 1
                if vmax > vmin:
                    image = np.clip((image - vmin) / (vmax - vmin) * 255, 0, 255).astype(np.uint8)
                else:
                    image = np.zeros_like(image, dtype=np.uint8)

        pil_img = PILImage.fromarray(image)
        buf = io.BytesIO()
        pil_img.save(buf, format="PNG")
        buf.seek(0)

        return StreamingResponse(buf, media_type="image/png")

    except Exception as e:
        logger.error(f"Failed to read tile image: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to read tile image: {e}")


@router.get("/scenes")
async def list_scenes():
    """List all ingested scenes."""
    rows = execute_query(
        """
        SELECT s.*, COUNT(t.tile_id) as tile_count
        FROM scenes s
        LEFT JOIN tiles t ON s.scene_id = t.scene_id
        GROUP BY s.scene_id
        ORDER BY s.ingested_at DESC
        """
    )
    return {"scenes": rows, "total": len(rows)}
