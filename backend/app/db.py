"""
SQLite database connection and schema management.

All metadata, provenance, and audit records are stored in SQLite.
Vector data lives in FAISS; SQLite provides the relational context.
"""

import sqlite3
import logging
from pathlib import Path
from contextlib import contextmanager
from typing import Generator

from app.config import get_settings

logger = logging.getLogger(__name__)


# ── Schema ──────────────────────────────────────────────────────────

SCHEMA_SQL = """
-- Source scenes (original GeoTIFF files)
CREATE TABLE IF NOT EXISTS scenes (
    scene_id            TEXT PRIMARY KEY,
    file_path           TEXT NOT NULL,
    sensor              TEXT,
    acquisition_date    TEXT,
    crs                 TEXT,
    bounds_minx         REAL,
    bounds_miny         REAL,
    bounds_maxx         REAL,
    bounds_maxy         REAL,
    width               INTEGER,
    height              INTEGER,
    band_count          INTEGER,
    file_size_bytes     INTEGER,
    ingested_at         TEXT NOT NULL,
    processing_version  TEXT
);

-- Tiles / chips generated from scenes
CREATE TABLE IF NOT EXISTS tiles (
    tile_id             TEXT PRIMARY KEY,
    scene_id            TEXT NOT NULL REFERENCES scenes(scene_id),
    file_path           TEXT NOT NULL,
    x_index             INTEGER,
    y_index             INTEGER,
    crs                 TEXT,
    bounds_minx         REAL,
    bounds_miny         REAL,
    bounds_maxx         REAL,
    bounds_maxy         REAL,
    center_lat          REAL,
    center_lon          REAL,
    width               INTEGER,
    height              INTEGER,
    band_count          INTEGER,
    created_at          TEXT NOT NULL
);

-- Embedding records (link tiles to FAISS vectors)
CREATE TABLE IF NOT EXISTS embeddings (
    embedding_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    tile_id             TEXT NOT NULL REFERENCES tiles(tile_id),
    model_name          TEXT NOT NULL,
    model_version       TEXT NOT NULL,
    vector_dim          INTEGER NOT NULL,
    faiss_index_id      INTEGER NOT NULL,
    created_at          TEXT NOT NULL
);

-- Index manifest for incremental ingestion
CREATE TABLE IF NOT EXISTS index_manifest (
    tile_id             TEXT NOT NULL,
    content_hash        TEXT NOT NULL,
    embedding_model     TEXT NOT NULL,
    embedding_version   TEXT NOT NULL,
    indexed_at          TEXT NOT NULL,
    PRIMARY KEY (tile_id, embedding_model)
);

-- Change analysis records
CREATE TABLE IF NOT EXISTS change_analyses (
    analysis_id             TEXT PRIMARY KEY,
    tile_id                 TEXT NOT NULL,
    t1_tile_id              TEXT,
    t2_tile_id              TEXT,
    change_type             TEXT,
    confidence              REAL,
    structural_confidence   REAL,
    seasonal_confound       REAL,
    cloud_contamination     REAL,
    registration_quality    REAL,
    persistence_score       REAL,
    earliest_supported      TEXT,
    change_mask_path        TEXT,
    change_pixels           INTEGER,
    total_pixels            INTEGER,
    status                  TEXT DEFAULT 'pending',
    created_at              TEXT NOT NULL,
    completed_at            TEXT
);

-- Analyst review decisions
CREATE TABLE IF NOT EXISTS analyst_reviews (
    review_id           INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_id         TEXT REFERENCES change_analyses(analysis_id),
    tile_id             TEXT,
    decision            TEXT CHECK(decision IN ('confirmed', 'rejected', 'uncertain')),
    notes               TEXT,
    analyst             TEXT,
    created_at          TEXT NOT NULL
);

-- Provenance records — trace every operation
CREATE TABLE IF NOT EXISTS provenance_records (
    provenance_id       TEXT PRIMARY KEY,
    entity_type         TEXT NOT NULL,
    entity_id           TEXT,
    query_text          TEXT,
    query_tile_id       TEXT,
    embedding_model     TEXT,
    embedding_version   TEXT,
    processing_version  TEXT,
    parameters          TEXT,
    result_summary      TEXT,
    confidence          REAL,
    created_at          TEXT NOT NULL
);

-- Query / audit log
CREATE TABLE IF NOT EXISTS query_log (
    query_id            TEXT PRIMARY KEY,
    query_type          TEXT NOT NULL,
    query_text          TEXT,
    query_tile_id       TEXT,
    filters             TEXT,
    result_count        INTEGER,
    latency_ms          REAL,
    created_at          TEXT NOT NULL
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_tiles_scene ON tiles(scene_id);
CREATE INDEX IF NOT EXISTS idx_tiles_date ON tiles(created_at);
CREATE INDEX IF NOT EXISTS idx_tiles_location ON tiles(center_lat, center_lon);
CREATE INDEX IF NOT EXISTS idx_tiles_bounds ON tiles(bounds_minx, bounds_miny, bounds_maxx, bounds_maxy);
CREATE INDEX IF NOT EXISTS idx_embeddings_tile ON embeddings(tile_id);
CREATE INDEX IF NOT EXISTS idx_embeddings_faiss ON embeddings(faiss_index_id);
CREATE INDEX IF NOT EXISTS idx_manifest_tile ON index_manifest(tile_id);
CREATE INDEX IF NOT EXISTS idx_change_tile ON change_analyses(tile_id);
CREATE INDEX IF NOT EXISTS idx_provenance_entity ON provenance_records(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_query_log_type ON query_log(query_type);
"""


def get_db_path() -> Path:
    """Get the database file path from settings."""
    settings = get_settings()
    return Path(settings.database_path)


def init_db(db_path: Path | None = None) -> None:
    """Initialize the database schema. Creates the file and tables if they don't exist."""
    if db_path is None:
        db_path = get_db_path()

    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    try:
        conn.executescript(SCHEMA_SQL)
        conn.commit()
        logger.info(f"Database initialized at {db_path}")
    finally:
        conn.close()


@contextmanager
def get_connection(db_path: Path | None = None) -> Generator[sqlite3.Connection, None, None]:
    """Get a database connection as a context manager."""
    if db_path is None:
        db_path = get_db_path()

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
    finally:
        conn.close()


def execute_query(sql: str, params: tuple = (), db_path: Path | None = None) -> list[dict]:
    """Execute a SELECT query and return results as list of dicts."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(sql, params)
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


def execute_insert(sql: str, params: tuple = (), db_path: Path | None = None) -> int:
    """Execute an INSERT and return the last row ID."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(sql, params)
        conn.commit()
        return cursor.lastrowid


def execute_many(sql: str, params_list: list[tuple], db_path: Path | None = None) -> None:
    """Execute a parameterized statement for multiple rows."""
    with get_connection(db_path) as conn:
        conn.executemany(sql, params_list)
        conn.commit()
