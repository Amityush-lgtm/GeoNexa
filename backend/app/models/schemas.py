"""
Pydantic models for API requests and responses.

These schemas define the contract between frontend and backend.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ── Search ──────────────────────────────────────────────────────────

class SearchRequest(BaseModel):
    """Semantic text search request."""
    query: str = Field(..., description="Natural-language search query")
    bbox: Optional[list[float]] = Field(None, description="[lon_min, lat_min, lon_max, lat_max]")
    date_from: Optional[str] = Field(None, description="Start date YYYY-MM-DD")
    date_to: Optional[str] = Field(None, description="End date YYYY-MM-DD")
    sensor: Optional[str] = Field(None, description="Sensor/source filter")
    top_k: int = Field(default=20, ge=1, le=200)


class SimilarityRequest(BaseModel):
    """Image-to-image similarity search request."""
    tile_id: Optional[str] = Field(None, description="Tile ID to find similar tiles for")
    top_k: int = Field(default=20, ge=1, le=200)
    bbox: Optional[list[float]] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    sensor: Optional[str] = None


class SearchResult(BaseModel):
    """A single search result."""
    tile_id: str
    similarity: float
    image_url: str
    location: dict  # {"lat": ..., "lon": ...}
    bbox: list[float]
    date: Optional[str]
    sensor: Optional[str]
    scene_id: str
    provenance_id: Optional[str] = None


class SearchResponse(BaseModel):
    """Search response with ranked results."""
    query_id: str
    results: list[SearchResult]
    total: int
    latency_ms: float


# ── Archive ─────────────────────────────────────────────────────────

class IngestRequest(BaseModel):
    """Ingest a single scene."""
    scene_path: str = Field(..., description="Path to GeoTIFF scene file")
    sensor: Optional[str] = Field(None, description="Sensor name override")
    acquisition_date: Optional[str] = Field(None, description="Acquisition date override YYYY-MM-DD")


class BatchIngestRequest(BaseModel):
    """Ingest multiple scenes."""
    directory: str = Field(..., description="Directory containing GeoTIFF files")
    sensor: Optional[str] = None
    recursive: bool = False


class SceneInfo(BaseModel):
    """Scene metadata."""
    scene_id: str
    file_path: str
    sensor: Optional[str]
    acquisition_date: Optional[str]
    crs: Optional[str]
    bounds: Optional[list[float]]
    width: Optional[int]
    height: Optional[int]
    band_count: Optional[int]
    file_size_bytes: Optional[int]
    ingested_at: str
    tile_count: int = 0


class TileInfo(BaseModel):
    """Tile metadata."""
    tile_id: str
    scene_id: str
    file_path: str
    x_index: int
    y_index: int
    crs: Optional[str]
    bounds: Optional[list[float]]
    center_lat: Optional[float]
    center_lon: Optional[float]
    width: int
    height: int
    band_count: Optional[int]
    created_at: str
    image_url: str = ""


class ArchiveStats(BaseModel):
    """Archive statistics."""
    total_scenes: int
    total_tiles: int
    total_embeddings: int
    index_size: int  # number of vectors in FAISS
    sensors: list[str]
    date_range: Optional[dict] = None  # {"earliest": ..., "latest": ...}
    storage_bytes: int = 0


class IngestResponse(BaseModel):
    """Response from ingestion."""
    scene_id: str
    tiles_created: int
    status: str
    message: str


# ── Change Analysis ─────────────────────────────────────────────────

class ChangeRequest(BaseModel):
    """Request change analysis for a tile."""
    tile_id: str = Field(..., description="Primary tile to analyze")
    t1_tile_id: Optional[str] = Field(None, description="Specific earlier tile (auto-selects if omitted)")
    t2_tile_id: Optional[str] = Field(None, description="Specific later tile (auto-selects if omitted)")


class ChangeConfidence(BaseModel):
    """Confidence breakdown for a change analysis."""
    structural: float = Field(..., ge=0, le=1)
    seasonal_confound: float = Field(..., ge=0, le=1)
    cloud_contamination: float = Field(..., ge=0, le=1)
    registration_quality: float = Field(..., ge=0, le=1)
    persistence: float = Field(default=0.0, ge=0, le=1)
    final_score: float = Field(..., ge=0, le=1)
    label: str  # HIGH, MEDIUM, LOW


class TemporalObservation(BaseModel):
    """A temporal observation of a location."""
    tile_id: str
    date: str
    sensor: Optional[str]
    image_url: str
    similarity_to_target: Optional[float] = None


class ChangeResult(BaseModel):
    """Change analysis result."""
    analysis_id: str
    tile_id: str
    t1_tile_id: str
    t2_tile_id: str
    t1_date: Optional[str]
    t2_date: Optional[str]
    change_type: Optional[str]
    confidence: ChangeConfidence
    earliest_supported: Optional[str]
    change_mask_url: Optional[str]
    change_pixels: int = 0
    total_pixels: int = 0
    change_percentage: float = 0.0
    temporal_observations: list[TemporalObservation] = []
    status: str
    provenance_id: Optional[str] = None


# ── Query Router ────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    """General query to be routed."""
    text: str
    tile_id: Optional[str] = None  # context tile if available


class QueryClassification(BaseModel):
    """Classified query intent."""
    intent: str  # SEMANTIC_SEARCH, IMAGE_SIMILARITY, CHANGE_ANALYSIS, VQA, PROVENANCE
    confidence: float
    original_text: str
    parameters: dict = {}


# ── Provenance ──────────────────────────────────────────────────────

class ProvenanceRecord(BaseModel):
    """Provenance trace for any operation."""
    provenance_id: str
    entity_type: str
    entity_id: Optional[str]
    query_text: Optional[str]
    query_tile_id: Optional[str]
    embedding_model: Optional[str]
    embedding_version: Optional[str]
    processing_version: Optional[str]
    parameters: Optional[dict]
    result_summary: Optional[dict]
    confidence: Optional[float]
    created_at: str


# ── Health ──────────────────────────────────────────────────────────

class HealthCheck(BaseModel):
    """System health and offline readiness."""
    status: str  # "healthy", "degraded", "unhealthy"
    version: str
    offline_mode: bool
    checks: dict[str, bool]
    timestamp: str


# ── Analyst Review ──────────────────────────────────────────────────

class ReviewRequest(BaseModel):
    """Analyst review of a change analysis."""
    analysis_id: str
    decision: str = Field(..., pattern="^(confirmed|rejected|uncertain)$")
    notes: Optional[str] = None
    analyst: Optional[str] = None


class ReviewResponse(BaseModel):
    """Response from submitting a review."""
    review_id: int
    status: str
    message: str
