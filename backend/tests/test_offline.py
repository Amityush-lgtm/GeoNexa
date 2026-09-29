"""
Unit tests for offline mode enforcement and air-gap compliance.
"""

import pytest
from app.config import get_settings


def test_offline_mode_configuration():
    settings = get_settings()
    assert settings.offline_mode is True


def test_local_model_path_configured():
    settings = get_settings()
    assert "remoteclip" in settings.model_path.lower() or "clip" in settings.model_path.lower()
    assert "main.index" in settings.faiss_index_path
    assert "metadata.db" in settings.database_path
