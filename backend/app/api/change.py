"""
Change analysis API routes.
"""

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.models.schemas import ChangeRequest, ReviewRequest, ReviewResponse
from app.change.temporal import get_temporal_observations, find_best_pair
from app.change.detector import detect_changes, find_earliest_supported
from app.db import get_connection, execute_query
from app.provenance.tracker import record_provenance
from datetime import datetime, timezone

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/analyze")
async def analyze_change(request: ChangeRequest):
    """
    Run change analysis for a tile.

    Finds temporal observations, selects T1/T2 pair, and runs change detection.
    """
    # Get temporal observations
    observations = get_temporal_observations(request.tile_id)

    if len(observations) < 2:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient temporal observations for tile {request.tile_id}. Need at least 2, found {len(observations)}.",
        )

    # Find best T1/T2 pair
    t1, t2 = find_best_pair(
        request.tile_id,
        t1_tile_id=request.t1_tile_id,
        t2_tile_id=request.t2_tile_id,
    )

    if t1 is None or t2 is None:
        raise HTTPException(status_code=400, detail="Could not find suitable T1/T2 pair")

    # Get file paths
    t1_path = _tile_path(t1["tile_id"])
    t2_path = _tile_path(t2["tile_id"])

    if t1_path is None or t2_path is None:
        raise HTTPException(status_code=404, detail="Tile files not found")

    # Run change detection
    result = detect_changes(
        t1_path=t1_path,
        t2_path=t2_path,
        t1_tile_id=t1["tile_id"],
        t2_tile_id=t2["tile_id"],
        tile_id=request.tile_id,
    )

    # Find earliest supported observation
    earliest = find_earliest_supported(request.tile_id, observations)
    result["earliest_supported"] = earliest

    # Add dates
    result["t1_date"] = t1.get("date")
    result["t2_date"] = t2.get("date")

    # Add temporal observations to result
    result["temporal_observations"] = [
        {
            "tile_id": obs["tile_id"],
            "date": obs.get("date"),
            "sensor": obs.get("sensor"),
            "image_url": obs["image_url"],
        }
        for obs in observations
    ]

    # Record provenance
    try:
        record_provenance(
            entity_type="change",
            entity_id=result["analysis_id"],
            query_tile_id=request.tile_id,
            parameters={
                "t1_tile_id": t1["tile_id"],
                "t2_tile_id": t2["tile_id"],
            },
            result_summary={
                "change_type": result.get("change_type"),
                "change_percentage": result.get("change_percentage"),
                "confidence": result.get("confidence", {}).get("final_score"),
            },
            confidence=result.get("confidence", {}).get("final_score"),
        )
    except Exception as e:
        logger.warning(f"Provenance recording failed: {e}")

    return result


@router.get("/{analysis_id}")
async def get_analysis(analysis_id: str):
    """Get a change analysis result."""
    rows = execute_query(
        "SELECT * FROM change_analyses WHERE analysis_id = ?",
        (analysis_id,),
    )

    if not rows:
        raise HTTPException(status_code=404, detail=f"Analysis {analysis_id} not found")

    return rows[0]


@router.get("/temporal/{tile_id}")
async def get_temporal(tile_id: str):
    """Get temporal observations for a tile location."""
    observations = get_temporal_observations(tile_id)
    return {
        "tile_id": tile_id,
        "observations": observations,
        "total": len(observations),
    }


@router.get("/mask/{analysis_id}")
async def get_change_mask(analysis_id: str):
    """Get the change mask image for an analysis."""
    rows = execute_query(
        "SELECT change_mask_path FROM change_analyses WHERE analysis_id = ?",
        (analysis_id,),
    )

    if not rows or not rows[0].get("change_mask_path"):
        raise HTTPException(status_code=404, detail="Change mask not found")

    mask_path = rows[0]["change_mask_path"]
    if not Path(mask_path).exists():
        raise HTTPException(status_code=404, detail="Change mask file not found")

    return FileResponse(mask_path, media_type="image/png")


@router.post("/review")
async def submit_review(request: ReviewRequest):
    """Submit an analyst review of a change analysis."""
    now = datetime.now(timezone.utc).isoformat()

    with get_connection() as conn:
        # Verify analysis exists
        analysis = conn.execute(
            "SELECT analysis_id FROM change_analyses WHERE analysis_id = ?",
            (request.analysis_id,),
        ).fetchone()

        if not analysis:
            raise HTTPException(status_code=404, detail="Analysis not found")

        cursor = conn.execute(
            """
            INSERT INTO analyst_reviews (analysis_id, decision, notes, analyst, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (request.analysis_id, request.decision, request.notes, request.analyst, now),
        )
        conn.commit()
        review_id = cursor.lastrowid

    return ReviewResponse(
        review_id=review_id,
        status="recorded",
        message=f"Review '{request.decision}' recorded for analysis {request.analysis_id}",
    )


def _tile_path(tile_id: str) -> str | None:
    """Look up the file path for a tile."""
    rows = execute_query("SELECT file_path FROM tiles WHERE tile_id = ?", (tile_id,))
    return rows[0]["file_path"] if rows else None
