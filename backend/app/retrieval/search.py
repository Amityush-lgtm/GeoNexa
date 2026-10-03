"""
Semantic search pipeline.

Orchestrates: text embedding → FAISS search → metadata join → filtering → ranking.
"""

import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Optional, List

import numpy as np

from app.db import get_connection
from app.embeddings.manager import get_embedding_model
from app.retrieval.vector_store import get_vector_store
from app.retrieval.filters import apply_metadata_filters

from app.query.router import parse_and_route_query


def calibrate_text_similarity(raw_score: float) -> float:
    """Calibrate raw text-to-image cosine similarity into standard 0.0-1.0 confidence."""
    # RemoteCLIP cosine similarities typically range between 0.16 and 0.34
    val = (float(raw_score) - 0.15) / 0.18
    val = max(0.0, min(1.0, val))
    return round(float(np.clip(0.50 + 0.48 * (val ** 0.85), 0.10, 0.99)), 4)


def calibrate_image_similarity(raw_score: float) -> float:
    """Calibrate image-to-image cosine similarity into standard 0.0-1.0 confidence."""
    val = (float(raw_score) - 0.45) / 0.50
    val = max(0.0, min(1.0, val))
    return round(float(np.clip(0.50 + 0.48 * val, 0.10, 0.99)), 4)


def semantic_search(
    query: str,
    top_k: int = 20,
    bbox: Optional[List[float]] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    sensor: Optional[str] = None,
    model=None,
    store=None,
) -> dict:
    """
    Perform semantic text-to-image search with natural language parsing.
    """
    start = time.time()
    query_id = f"q-{uuid.uuid4().hex[:8]}"

    # Parse natural language query for filters and distilled prompt
    parsed = parse_and_route_query(query)
    effective_prompt = parsed.get("cleaned_prompt") or query
    
    # Auto-populate filters if not explicitly provided
    if bbox is None and parsed.get("bbox"):
        bbox = parsed["bbox"]
    if date_from is None and parsed.get("date_from"):
        date_from = parsed["date_from"]
    if date_to is None and parsed.get("date_to"):
        date_to = parsed["date_to"]
    if sensor is None and parsed.get("sensor"):
        sensor = parsed["sensor"]

    # 1. Encode distilled text
    if model is None:
        model = get_embedding_model()
    query_vector = model.encode_text(effective_prompt)

    # 2. Search FAISS index across candidate pool for Stage-2 reasoning
    if store is None:
        store = get_vector_store()
    total_vectors = len(store._id_to_tile)
    fetch_k = max(1, total_vectors) if total_vectors > 0 else max(1, top_k)
    tile_ids, scores = store.search(query_vector, k=fetch_k)

    if not tile_ids:
        return {
            "query_id": query_id,
            "query": query,
            "effective_prompt": effective_prompt,
            "parsed_intent": parsed.get("intent", "SEMANTIC_SEARCH"),
            "is_change_query": parsed.get("is_change_query", False),
            "results": [],
            "total": 0,
            "latency_ms": (time.time() - start) * 1000,
        }

    # 3. Join with metadata and calibrate scores
    results = _join_metadata(tile_ids, scores, search_type="text")

    # 4. Apply metadata filters
    results = apply_metadata_filters(
        results, bbox=bbox, date_from=date_from, date_to=date_to, sensor=sensor
    )

    # 5. Stage 2: Apply Local VLM Precision Verification & Visual Reasoning
    from app.retrieval.vlm_reasoner import rerank_search_results
    results = rerank_search_results(
        query=effective_prompt or query,
        candidates=results,
        top_k=top_k
    )

    # 6. Log query
    latency_ms = (time.time() - start) * 1000
    _log_query(query_id, parsed.get("intent", "SEMANTIC_SEARCH"), query, None, {
        "bbox": bbox, "date_from": date_from, "date_to": date_to, "sensor": sensor,
    }, len(results), latency_ms)

    return {
        "query_id": query_id,
        "query": query,
        "effective_prompt": effective_prompt,
        "parsed_intent": parsed.get("intent", "SEMANTIC_SEARCH"),
        "is_change_query": parsed.get("is_change_query", False),
        "extracted_filters": {
            "location": parsed.get("location"),
            "bbox": bbox,
            "date_from": date_from,
            "date_to": date_to,
            "sensor": sensor,
        },
        "results": results,
        "total": len(results),
        "latency_ms": latency_ms,
    }


def similarity_search(
    tile_id: str,
    top_k: int = 20,
    bbox: Optional[List[float]] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    sensor: Optional[str] = None,
) -> dict:
    """
    Perform image-to-image similarity search.
    """
    start = time.time()
    query_id = f"q-{uuid.uuid4().hex[:8]}"

    store = get_vector_store()
    query_vector = store.get_vector(tile_id)

    if query_vector is None:
        tile_meta = _get_tile_metadata(tile_id)
        if tile_meta is None:
            return {
                "query_id": query_id,
                "results": [],
                "total": 0,
                "latency_ms": (time.time() - start) * 1000,
                "error": f"Tile {tile_id} not found",
            }

        model = get_embedding_model()
        image = _load_tile_image(tile_meta["file_path"])
        if image is not None:
            query_vector = model.encode_image(image)
        else:
            return {
                "query_id": query_id,
                "results": [],
                "total": 0,
                "latency_ms": (time.time() - start) * 1000,
                "error": f"Could not load image for tile {tile_id}",
            }

    fetch_k = top_k + 5
    tile_ids, scores = store.search(query_vector, k=fetch_k)

    filtered = [(tid, s) for tid, s in zip(tile_ids, scores) if tid != tile_id]
    tile_ids = [t[0] for t in filtered]
    scores = np.array([t[1] for t in filtered])

    results = _join_metadata(tile_ids, scores, search_type="image")
    results = apply_metadata_filters(
        results, bbox=bbox, date_from=date_from, date_to=date_to, sensor=sensor
    )
    results = results[:top_k]

    latency_ms = (time.time() - start) * 1000
    _log_query(query_id, "IMAGE_SIMILARITY", None, tile_id, {
        "bbox": bbox, "date_from": date_from, "date_to": date_to, "sensor": sensor,
    }, len(results), latency_ms)

    return {
        "query_id": query_id,
        "query_tile_id": tile_id,
        "results": results,
        "total": len(results),
        "latency_ms": latency_ms,
    }


def _join_metadata(tile_ids: List[str], scores: np.ndarray, search_type: str = "text") -> List[dict]:
    """Join vector search results with SQLite tile metadata and calibrated confidence."""
    if not tile_ids:
        return []

    placeholders = ",".join(["?"] * len(tile_ids))
    with get_connection() as conn:
        rows = conn.execute(
            f"""
            SELECT t.tile_id, t.scene_id, t.file_path, t.center_lat, t.center_lon,
                   t.bounds_minx, t.bounds_miny, t.bounds_maxx, t.bounds_maxy,
                   t.band_count,
                   s.sensor, s.acquisition_date
            FROM tiles t
            JOIN scenes s ON t.scene_id = s.scene_id
            WHERE t.tile_id IN ({placeholders})
            """,
            tile_ids,
        ).fetchall()

    meta_lookup = {row["tile_id"]: dict(row) for row in rows}

    results = []
    for tid, score in zip(tile_ids, scores):
        meta = meta_lookup.get(tid)
        if meta is None:
            continue

        raw_score = float(score)
        if search_type == "image":
            calibrated_conf = calibrate_image_similarity(raw_score)
        else:
            calibrated_conf = calibrate_text_similarity(raw_score)

        results.append({
            "tile_id": tid,
            "similarity": calibrated_conf,  # Calibrated for friendly UI displays
            "raw_similarity": round(raw_score, 4),  # Preserved for STAC provenance
            "confidence": calibrated_conf,
            "match_percentage": round(calibrated_conf * 100, 1),
            "image_url": f"/api/archive/tiles/{tid}/image",
            "location": {
                "lat": meta.get("center_lat"),
                "lon": meta.get("center_lon"),
            },
            "bbox": [
                meta.get("bounds_minx", 0),
                meta.get("bounds_miny", 0),
                meta.get("bounds_maxx", 0),
                meta.get("bounds_maxy", 0),
            ],
            "date": meta.get("acquisition_date"),
            "sensor": meta.get("sensor"),
            "scene_id": meta.get("scene_id"),
        })

    return results


def _get_tile_metadata(tile_id: str) -> Optional[dict]:
    """Get tile metadata from SQLite."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM tiles WHERE tile_id = ?", (tile_id,)
        ).fetchone()
    return dict(row) if row else None


def _load_tile_image(file_path: str) -> Optional[np.ndarray]:
    """Load a tile image as RGB numpy array."""
    try:
        import rasterio
        with rasterio.open(file_path) as ds:
            bands = min(ds.count, 3)
            data = ds.read(list(range(1, bands + 1)))

            if bands == 1:
                # Grayscale → repeat to 3 channels
                data = np.repeat(data, 3, axis=0)
            elif bands == 2:
                # 2 bands → pad with zeros
                data = np.concatenate([data, np.zeros_like(data[:1])], axis=0)

            # CHW → HWC
            image = np.transpose(data, (1, 2, 0))

            # Normalize to 0-255
            if image.dtype != np.uint8:
                vmin, vmax = np.percentile(image[image > 0], [2, 98]) if image.any() else (0, 1)
                if vmax > vmin:
                    image = np.clip((image - vmin) / (vmax - vmin) * 255, 0, 255).astype(np.uint8)
                else:
                    image = np.zeros_like(image, dtype=np.uint8)

            return image
    except Exception as e:
        logger.error(f"Failed to load tile image {file_path}: {e}")
        return None


def _log_query(
    query_id: str, query_type: str, query_text: Optional[str],
    query_tile_id: Optional[str], filters: dict,
    result_count: int, latency_ms: float,
) -> None:
    """Log a query to the audit table."""
    import json
    now = datetime.now(timezone.utc).isoformat()
    try:
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO query_log
                    (query_id, query_type, query_text, query_tile_id, filters, result_count, latency_ms, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (query_id, query_type, query_text, query_tile_id,
                 json.dumps(filters), result_count, latency_ms, now),
            )
            conn.commit()
    except Exception as e:
        logger.warning(f"Failed to log query: {e}")
