"""
Application configuration loaded from environment variables and .env file.
"""

import os
from pathlib import Path
try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseModel as BaseSettings
from pydantic import Field


# Project root is two levels up from this file: backend/app/config.py -> semantic-eo-search/
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """Application settings — loaded from .env or environment variables."""

    # Core paths
    data_dir: str = Field(default=str(PROJECT_ROOT / "data" / "public"))
    model_path: str = Field(default=str(PROJECT_ROOT / "models" / "remoteclip-vit-b-32"))
    faiss_index_path: str = Field(default=str(PROJECT_ROOT / "indexes" / "main.index"))
    database_path: str = Field(default=str(PROJECT_ROOT / "data" / "public" / "metadata" / "metadata.db"))

    def model_post_init(self, __context) -> None:
        """Resolve relative paths against PROJECT_ROOT."""
        for field in ("data_dir", "model_path", "faiss_index_path", "database_path"):
            value = getattr(self, field)
            if not Path(value).is_absolute():
                object.__setattr__(self, field, str(PROJECT_ROOT / value))

    # Offline mode
    offline_mode: bool = Field(default=True)

    # Tiling
    tile_size: int = Field(default=256)
    tile_overlap: int = Field(default=32)

    # Search
    default_top_k: int = Field(default=20)

    # Embedding
    embedding_model: str = Field(default="remoteclip-vit-b-32")
    device: str = Field(default="cpu")

    # Server
    backend_host: str = Field(default="0.0.0.0")
    backend_port: int = Field(default=8000)
    frontend_url: str = Field(default="http://localhost:5173")

    # Logging
    log_level: str = Field(default="INFO")

    model_config = {
        "env_file": str(PROJECT_ROOT / ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    @property
    def raw_scenes_dir(self) -> Path:
        return Path(self.data_dir) / "raw" / "sentinel2"

    @property
    def processed_scenes_dir(self) -> Path:
        return Path(self.data_dir) / "processed" / "sentinel2"

    @property
    def tiles_dir(self) -> Path:
        return Path(self.data_dir) / "tiles"

    @property
    def metadata_dir(self) -> Path:
        return Path(self.data_dir) / "metadata"

    @property
    def manifests_dir(self) -> Path:
        return Path(self.data_dir) / "manifests"

    @property
    def indexes_dir(self) -> Path:
        return Path(self.faiss_index_path).parent


def get_settings() -> Settings:
    """Get application settings (singleton-ish via module-level caching)."""
    return Settings()

