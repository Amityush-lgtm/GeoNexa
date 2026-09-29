"""
Provenance tracker — records every operation for audit and traceability.

Every search, change analysis, similarity result, and VQA answer
generates a provenance record that traces the full processing chain.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from app.db import get_connection

logger = logging.getLogger(__name__)

PROCESSING_VERSION = "0.1.0"


def record_provenance(
    entity_type: str,
    entity_id: Optional[str] = None,
    query_text: Optional[str] = None,
    query_tile_id: Optional[str] = None,
    embedding_model: Optional[str] = None,
    embedding_version: Optional[str] = None,
    parameters: Optional[dict] = None,
    result_summary: Optional[dict] = None,
    confidence: Optional[float] = None,
) -> str:
    """
    Create a provenance record for an operation.

    Args:
        entity_type: Type of operation ('search', 'change', 'similarity', 'vqa').
        entity_id: ID of the result entity (analysis_id, query_id, etc.).
        query_text: Original query text.
        query_tile_id: Query tile ID for similarity/change.
        embedding_model: Model used for embedding.
        embedding_version: Model version.
        parameters: Processing parameters.
        result_summary: Summary of results.
        confidence: Overall confidence score.

    Returns:
        provenance_id
    """
    provenance_id = f"prov-{uuid.uuid4().hex[:8]}"
    now = datetime.now(timezone.utc).isoformat()

    try:
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO provenance_records (
                    provenance_id, entity_type, entity_id,
                    query_text, query_tile_id,
                    embedding_model, embedding_version, processing_version,
                    parameters, result_summary, confidence,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    provenance_id,
                    entity_type,
                    entity_id,
                    query_text,
                    query_tile_id,
                    embedding_model,
                    embedding_version,
                    PROCESSING_VERSION,
                    json.dumps(parameters) if parameters else None,
                    json.dumps(result_summary) if result_summary else None,
                    confidence,
                    now,
                ),
            )
            conn.commit()
    except Exception as e:
        logger.warning(f"Failed to record provenance: {e}")

    return provenance_id


def get_provenance(provenance_id: str) -> Optional[dict]:
    """Retrieve a provenance record by ID."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM provenance_records WHERE provenance_id = ?",
            (provenance_id,),
        ).fetchone()

    if row is None:
        return None

    result = dict(row)

    # Parse JSON fields
    if result.get("parameters"):
        try:
            result["parameters"] = json.loads(result["parameters"])
        except json.JSONDecodeError:
            pass

    if result.get("result_summary"):
        try:
            result["result_summary"] = json.loads(result["result_summary"])
        except json.JSONDecodeError:
            pass

    return result


def get_provenance_by_entity(entity_type: str, entity_id: str) -> list[dict]:
    """Get all provenance records for a given entity."""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM provenance_records
            WHERE entity_type = ? AND entity_id = ?
            ORDER BY created_at DESC
            """,
            (entity_type, entity_id),
        ).fetchall()

    results = []
    for row in rows:
        r = dict(row)
        if r.get("parameters"):
            try:
                r["parameters"] = json.loads(r["parameters"])
            except json.JSONDecodeError:
                pass
        if r.get("result_summary"):
            try:
                r["result_summary"] = json.loads(r["result_summary"])
            except json.JSONDecodeError:
                pass
        results.append(r)

    return results


def get_recent_provenance(limit: int = 50) -> list[dict]:
    """Get the most recent provenance records."""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM provenance_records
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    results = []
    for row in rows:
        r = dict(row)
        if r.get("parameters"):
            try:
                r["parameters"] = json.loads(r["parameters"])
            except json.JSONDecodeError:
                pass
        if r.get("result_summary"):
            try:
                r["result_summary"] = json.loads(r["result_summary"])
            except json.JSONDecodeError:
                pass
        results.append(r)

    return results
