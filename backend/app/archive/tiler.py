"""
Scene tiling — split a GeoTIFF into georeferenced tile chips.

Each tile preserves its geospatial reference (CRS, bounds) and is traceable
back to its parent scene. Tiles are saved as individual GeoTIFF files.
"""

import logging
from pathlib import Path
from typing import Optional

import numpy as np
import rasterio
from rasterio.windows import Window
from pyproj import Transformer

from app.config import get_settings

logger = logging.getLogger(__name__)


def tile_scene(
    scene_path: str | Path,
    scene_id: str,
    output_dir: str | Path | None = None,
    tile_size: int | None = None,
    overlap: int | None = None,
) -> list[dict]:
    """
    Tile a GeoTIFF scene into fixed-size chips with optional overlap.

    Args:
        scene_path: Path to the source GeoTIFF.
        scene_id: Parent scene ID (for tile ID generation).
        output_dir: Directory to save tiles. Defaults to settings.tiles_dir / scene_id.
        tile_size: Tile dimension in pixels. Defaults to settings.tile_size.
        overlap: Overlap in pixels between adjacent tiles. Defaults to settings.tile_overlap.

    Returns:
        List of tile metadata dicts with keys:
            tile_id, scene_id, file_path, x_index, y_index,
            crs, bounds_minx, bounds_miny, bounds_maxx, bounds_maxy,
            center_lat, center_lon, width, height, band_count
    """
    settings = get_settings()
    tile_size = tile_size or settings.tile_size
    overlap = overlap or settings.tile_overlap
    scene_path = Path(scene_path)

    if output_dir is None:
        output_dir = Path(settings.data_dir) / "tiles" / scene_id
    else:
        output_dir = Path(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    tiles = []
    step = tile_size - overlap

    with rasterio.open(str(scene_path)) as ds:
        src_crs = ds.crs
        src_transform = ds.transform
        band_count = min(ds.count, 3)  # Use at most 3 bands for tiles

        # Calculate number of tiles in each dimension
        n_cols = max(1, (ds.width - overlap) // step)
        n_rows = max(1, (ds.height - overlap) // step)

        # Set up CRS transformer for center lat/lon computation
        transformer = None
        if src_crs:
            try:
                transformer = Transformer.from_crs(src_crs, "EPSG:4326", always_xy=True)
            except Exception:
                pass

        for yi in range(n_rows):
            for xi in range(n_cols):
                col_off = xi * step
                row_off = yi * step

                # Clamp window to raster extent
                win_width = min(tile_size, ds.width - col_off)
                win_height = min(tile_size, ds.height - row_off)

                # Skip very small edge tiles
                if win_width < tile_size // 2 or win_height < tile_size // 2:
                    continue

                window = Window(col_off, row_off, win_width, win_height)

                # Read data (up to 3 bands)
                bands_to_read = list(range(1, band_count + 1))
                data = ds.read(bands_to_read, window=window)

                # Pad if smaller than tile_size
                if win_width < tile_size or win_height < tile_size:
                    padded = np.zeros((band_count, tile_size, tile_size), dtype=data.dtype)
                    padded[:, :win_height, :win_width] = data
                    data = padded

                # Compute tile transform and bounds
                tile_transform = rasterio.windows.transform(window, src_transform)
                tile_bounds = rasterio.windows.bounds(window, src_transform)

                # Compute center in EPSG:4326
                center_lat, center_lon = None, None
                bounds_4326 = None
                if transformer:
                    try:
                        cx = (tile_bounds[0] + tile_bounds[2]) / 2
                        cy = (tile_bounds[1] + tile_bounds[3]) / 2
                        center_lon, center_lat = transformer.transform(cx, cy)
                        min_lon, min_lat = transformer.transform(tile_bounds[0], tile_bounds[1])
                        max_lon, max_lat = transformer.transform(tile_bounds[2], tile_bounds[3])
                        bounds_4326 = (min_lon, min_lat, max_lon, max_lat)
                    except Exception:
                        pass

                # Generate tile ID
                tile_id = f"{scene_id}_x{xi:02d}_y{yi:02d}"
                tile_path = output_dir / f"{tile_id}.tif"

                # Write tile as GeoTIFF
                profile = ds.profile.copy()
                profile.update(
                    width=tile_size,
                    height=tile_size,
                    count=band_count,
                    transform=tile_transform,
                    driver="GTiff",
                    compress="lzw",
                )

                with rasterio.open(str(tile_path), "w", **profile) as tile_ds:
                    tile_ds.write(data)

                # Build tile metadata
                tile_meta = {
                    "tile_id": tile_id,
                    "scene_id": scene_id,
                    "file_path": str(tile_path.resolve()),
                    "x_index": xi,
                    "y_index": yi,
                    "crs": str(src_crs) if src_crs else None,
                    "bounds_minx": bounds_4326[0] if bounds_4326 else tile_bounds[0],
                    "bounds_miny": bounds_4326[1] if bounds_4326 else tile_bounds[1],
                    "bounds_maxx": bounds_4326[2] if bounds_4326 else tile_bounds[2],
                    "bounds_maxy": bounds_4326[3] if bounds_4326 else tile_bounds[3],
                    "center_lat": center_lat,
                    "center_lon": center_lon,
                    "width": tile_size,
                    "height": tile_size,
                    "band_count": band_count,
                }

                tiles.append(tile_meta)

    logger.info(f"Tiled scene {scene_id}: {len(tiles)} tiles ({n_cols}x{n_rows} grid, {tile_size}px, {overlap}px overlap)")
    return tiles
