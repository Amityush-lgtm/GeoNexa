"""
Query router API route — classifies and routes natural-language queries.
"""

from fastapi import APIRouter

from app.models.schemas import QueryRequest, QueryClassification
from app.query.router import classify_query

router = APIRouter()


@router.post("", response_model=QueryClassification)
async def route_query(request: QueryRequest):
    """
    Classify and route a natural-language query.

    Returns the detected intent and parameters so the frontend
    can redirect to the appropriate workflow.
    """
    result = classify_query(request.text, tile_id=request.tile_id)

    return QueryClassification(
        intent=result["intent"],
        confidence=result["confidence"],
        original_text=result["original_text"],
        parameters=result["parameters"],
    )
