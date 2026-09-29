"""
Pytest configuration and shared fixtures for Semantic EO Search.
"""

import os
import tempfile
from pathlib import Path
import numpy as np
import pytest
import pytest_asyncio

# Set test environment
os.environ["OFFLINE_MODE"] = "true"


@pytest.fixture
def temp_dir():
    """Temporary directory for test artifacts."""
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)


@pytest.fixture
def sample_tile_array():
    """Create a 4-band sample tile array (4, 256, 256)."""
    np.random.seed(42)
    return np.random.randint(0, 255, (4, 256, 256), dtype=np.uint8)


@pytest.fixture
def mock_embedding():
    """Create a 512-dim unit vector embedding."""
    vec = np.random.randn(512).astype(np.float32)
    return vec / np.linalg.norm(vec)
