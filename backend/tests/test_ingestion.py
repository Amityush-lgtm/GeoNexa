"""
Unit tests for scene metadata extraction, validation, and georeferenced tiling.
"""

from pathlib import Path
import numpy as np
import pytest
from app.archive.metadata import validate_scene, extract_metadata, generate_scene_id
from app.archive.tiler import tile_scene

try:
    import rasterio
    from rasterio.transform import from_bounds
    HAS_RASTERIO = True
except ImportError:
    HAS_RASTERIO = False


@pytest.fixture
def dummy_geotiff(temp_dir):
    """Create a minimal valid GeoTIFF for testing."""
    if not HAS_RASTERIO:
        pytest.skip("rasterio required for geotiff test")

    file_path = temp_dir / "S2A_MSIL2A_20260115_TEST.tif"
    width, height = 512, 512
    data = np.random.randint(0, 255, (4, height, width), dtype=np.uint8)
    transform = from_bounds(91.65, 26.10, 91.85, 26.25, width, height)

    with rasterio.open(
        str(file_path),
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=4,
        dtype=np.uint8,
        crs="EPSG:4326",
        transform=transform,
    ) as dst:
        for b in range(4):
            dst.write(data[b], b + 1)

    return file_path


def test_validate_and_extract_metadata(dummy_geotiff):
    val = validate_scene(dummy_geotiff)
    assert val["valid"] is True

    meta = extract_metadata(dummy_geotiff)
    assert meta["width"] == 512
    assert meta["height"] == 512
    assert meta["band_count"] == 4
    assert meta["crs"] == "EPSG:4326"


def test_tile_scene_preserves_georeferencing(dummy_geotiff, temp_dir):
    tiles_dir = temp_dir / "tiles"
    tiles = tile_scene(
        scene_path=dummy_geotiff,
        scene_id="TEST_SCENE",
        output_dir=tiles_dir,
        tile_size=256,
        overlap=32,
    )

    assert len(tiles) > 0
    for t in tiles:
        assert t["scene_id"] == "TEST_SCENE"
        assert Path(t["file_path"]).exists()
        assert t["center_lat"] is not None
        assert t["center_lon"] is not None
        assert 26.10 <= t["center_lat"] <= 26.25
        assert 91.65 <= t["center_lon"] <= 91.85
