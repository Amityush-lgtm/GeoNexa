"""
Search API routes — semantic search and image-to-image similarity.
"""

import logging

from fastapi import APIRouter

from app.models.schemas import SearchRequest, SimilarityRequest, SearchResponse
from app.retrieval.search import semantic_search, similarity_search
from app.provenance.tracker import record_provenance
from app.embeddings.manager import get_embedding_model

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("", response_model=SearchResponse)
async def search(request: SearchRequest):
    """
    Semantic text-to-image search.

    Encodes the text query, searches the FAISS index, filters by metadata,
    and returns ranked satellite tile results.
    """
    result = semantic_search(
        query=request.query,
        top_k=request.top_k,
        bbox=request.bbox,
        date_from=request.date_from,
        date_to=request.date_to,
        sensor=request.sensor,
    )

    # Record provenance
    try:
        model = get_embedding_model()
        prov_id = record_provenance(
            entity_type="search",
            entity_id=result["query_id"],
            query_text=request.query,
            embedding_model=model.model_name,
            embedding_version=model.model_version,
            parameters={
                "top_k": request.top_k,
                "bbox": request.bbox,
                "date_from": request.date_from,
                "date_to": request.date_to,
                "sensor": request.sensor,
            },
            result_summary={
                "total_results": result["total"],
                "top_similarity": result["results"][0]["similarity"] if result["results"] else 0,
            },
        )

        # Attach provenance to results
        for r in result["results"]:
            r["provenance_id"] = prov_id
    except Exception as e:
        logger.warning(f"Provenance recording failed: {e}")

    return SearchResponse(**result)


@router.post("/similar")
async def search_similar(request: SimilarityRequest):
    """
    Image-to-image similarity search.

    Uses the embedding of an existing tile to find visually similar locations.
    """
    if not request.tile_id:
        return {"error": "tile_id is required", "results": [], "total": 0}

    result = similarity_search(
        tile_id=request.tile_id,
        top_k=request.top_k,
        bbox=request.bbox,
        date_from=request.date_from,
        date_to=request.date_to,
        sensor=request.sensor,
    )

    # Record provenance
    try:
        model = get_embedding_model()
        record_provenance(
            entity_type="similarity",
            entity_id=result["query_id"],
            query_tile_id=request.tile_id,
            embedding_model=model.model_name,
            embedding_version=model.model_version,
            parameters={"top_k": request.top_k},
            result_summary={"total_results": result["total"]},
        )
    except Exception as e:
        logger.warning(f"Provenance recording failed: {e}")

    return result
