"""
FastAPI application — main entry point for the backend.

Registers all routes, CORS middleware, and startup events.
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.db import init_db

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    settings = get_settings()

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    )

    # Initialize database
    init_db()
    logger.info("Database initialized")

    # Ensure data directories exist
    Path(settings.data_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.data_dir, "scenes").mkdir(parents=True, exist_ok=True)
    Path(settings.data_dir, "tiles").mkdir(parents=True, exist_ok=True)
    Path(settings.faiss_index_path).parent.mkdir(parents=True, exist_ok=True)

    logger.info(f"Semantic EO Search backend starting (offline_mode={settings.offline_mode})")

    yield

    logger.info("Semantic EO Search backend shutting down")


# Create the FastAPI application
app = FastAPI(
    title="Semantic EO Search",
    description="Semantic Retrieval and Multi-Temporal Change Analysis of Satellite Imagery",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and register routes
from app.api.archive import router as archive_router
from app.api.search import router as search_router
from app.api.change import router as change_router
from app.api.query import router as query_router
from app.api.provenance import router as provenance_router
from app.api.health import router as health_router

app.include_router(archive_router, prefix="/api/archive", tags=["Archive"])
app.include_router(search_router, prefix="/api/search", tags=["Search"])
app.include_router(change_router, prefix="/api/change", tags=["Change Analysis"])
app.include_router(query_router, prefix="/api/query", tags=["Query Router"])
app.include_router(provenance_router, prefix="/api/provenance", tags=["Provenance"])
app.include_router(health_router, prefix="/api", tags=["System"])


@app.get("/")
async def root():
    return {
        "name": "Semantic EO Search",
        "version": "0.1.0",
        "description": "Earth Observation Search Engine",
        "docs": "/docs",
    }
