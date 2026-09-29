"""
Provenance API routes — retrieve operation traces.
"""

from typing import List
from fastapi import APIRouter, HTTPException

from app.provenance.tracker import get_provenance, get_recent_provenance

router = APIRouter()


@router.get("", response_model=List[dict])
@router.get("/recent", response_model=List[dict])
async def list_recent_provenance(limit: int = 50):
    """List recent provenance records."""
    return get_recent_provenance(limit=limit)


@router.get("/{provenance_id}")
async def get_provenance_record(provenance_id: str):
    """Get a provenance record by ID."""
    record = get_provenance(provenance_id)

    if record is None:
        raise HTTPException(status_code=404, detail=f"Provenance record {provenance_id} not found")

    return record
