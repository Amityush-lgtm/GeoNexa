"""
Provenance API routes — retrieve operation traces.
"""

from fastapi import APIRouter, HTTPException

from app.provenance.tracker import get_provenance

router = APIRouter()


@router.get("/{provenance_id}")
async def get_provenance_record(provenance_id: str):
    """Get a provenance record by ID."""
    record = get_provenance(provenance_id)

    if record is None:
        raise HTTPException(status_code=404, detail=f"Provenance record {provenance_id} not found")

    return record
