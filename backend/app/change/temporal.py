"""
Temporal observation retrieval.

Given a tile/location, find corresponding observations across time
by spatial overlap. This powers the change-analysis timeline.
"""

import logging
from typing import List, Optional

from app.db import get_connection

logger = logging.getLogger(__name__)


# Overlap threshold for considering tiles as co-located (0–1 IoU)
MIN_SPATIAL_OVERLAP = 0.3

# Maximum distance in degrees between tile centers for co-location
MAX_CENTER_DISTANCE_DEG = 0.05  # ~5 km at equator


def get_temporal_observations(tile_id: str) -> List[dict]:
    """
    Find all temporal observations of the same location.

    Strategy:
    1. Get the target tile's bounds and center
    2. Find other tiles whose bounds overlap significantly
    3. Sort by acquisition date
    4. Return ordered list of observations

    Args:
        tile_id: The reference tile ID.

    Returns:
        List of observation dicts sorted by date, each with:
            tile_id, date, sensor, image_url, scene_id, bounds
    """
    with get_connection() as conn:
        # Get reference tile
        ref = conn.execute(
            """
            SELECT t.tile_id, t.center_lat, t.center_lon,
                   t.bounds_minx, t.bounds_miny, t.bounds_maxx, t.bounds_maxy,
                   s.acquisition_date, s.sensor
            FROM tiles t
            JOIN scenes s ON t.scene_id = s.scene_id
            WHERE t.tile_id = ?
            """,
            (tile_id,),
        ).fetchone()

        if ref is None:
            logger.warning(f"Tile {tile_id} not found")
            return []

        ref = dict(ref)

        # Find co-located tiles (nearby center or overlapping bounds)
        if ref["center_lat"] is not None and ref["center_lon"] is not None:
            # Use center distance
            observations = conn.execute(
                """
                SELECT t.tile_id, t.scene_id, t.center_lat, t.center_lon,
                       t.bounds_minx, t.bounds_miny, t.bounds_maxx, t.bounds_maxy,
                       t.file_path,
                       s.acquisition_date, s.sensor
                FROM tiles t
                JOIN scenes s ON t.scene_id = s.scene_id
                WHERE t.tile_id != ?
                  AND t.center_lat IS NOT NULL
                  AND t.center_lon IS NOT NULL
                  AND ABS(t.center_lat - ?) < ?
                  AND ABS(t.center_lon - ?) < ?
                  AND s.acquisition_date IS NOT NULL
                ORDER BY s.acquisition_date ASC
                """,
                (
                    tile_id,
                    ref["center_lat"], MAX_CENTER_DISTANCE_DEG,
                    ref["center_lon"], MAX_CENTER_DISTANCE_DEG,
                ),
            ).fetchall()
        else:
            # Fallback: use bounding box overlap
            observations = conn.execute(
                """
                SELECT t.tile_id, t.scene_id, t.center_lat, t.center_lon,
                       t.bounds_minx, t.bounds_miny, t.bounds_maxx, t.bounds_maxy,
                       t.file_path,
                       s.acquisition_date, s.sensor
                FROM tiles t
                JOIN scenes s ON t.scene_id = s.scene_id
                WHERE t.tile_id != ?
                  AND t.bounds_maxx >= ?
                  AND t.bounds_minx <= ?
                  AND t.bounds_maxy >= ?
                  AND t.bounds_miny <= ?
                  AND s.acquisition_date IS NOT NULL
                ORDER BY s.acquisition_date ASC
                """,
                (
                    tile_id,
                    ref["bounds_minx"], ref["bounds_maxx"],
                    ref["bounds_miny"], ref["bounds_maxy"],
                ),
            ).fetchall()

    # Build result list — include the reference tile in the timeline
    result = [
        {
            "tile_id": ref["tile_id"],
            "date": ref.get("acquisition_date"),
            "sensor": ref.get("sensor"),
            "image_url": f"/api/archive/tiles/{ref['tile_id']}/image",
            "scene_id": None,
            "is_reference": True,
        }
    ]

    for obs in observations:
        obs = dict(obs)
        result.append({
            "tile_id": obs["tile_id"],
            "date": obs.get("acquisition_date"),
            "sensor": obs.get("sensor"),
            "image_url": f"/api/archive/tiles/{obs['tile_id']}/image",
            "scene_id": obs.get("scene_id"),
            "is_reference": False,
        })

    # Sort by date
    result.sort(key=lambda x: x.get("date") or "9999-99-99")

    logger.info(f"Found {len(result)} temporal observations for tile {tile_id}")
    return result


def find_best_pair(tile_id: str, t1_tile_id: Optional[str] = None, t2_tile_id: Optional[str] = None) -> tuple:
    """
    Find the best T1/T2 pair for change analysis.

    If t1/t2 not specified, auto-selects the earliest and latest observations.

    Returns:
        (t1_tile_info, t2_tile_info) dicts with tile metadata
    """
    observations = get_temporal_observations(tile_id)

    if len(observations) < 2:
        return None, None

    # Filter to only non-reference observations + reference
    dated = [o for o in observations if o.get("date")]

    if len(dated) < 2:
        return None, None

    if t1_tile_id and t2_tile_id:
        t1 = next((o for o in dated if o["tile_id"] == t1_tile_id), None)
        t2 = next((o for o in dated if o["tile_id"] == t2_tile_id), None)
        return t1, t2

    # Auto-select: earliest and latest
    t1 = dated[0]
    t2 = dated[-1]

    return t1, t2
