"""
Archive metadata extraction from GeoTIFF/raster files.

Extracts scene-level metadata including CRS, bounds, dimensions,
bands, and acquisition date from raster files using rasterio.
"""

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

import rasterio
from pyproj import Transformer

logger = logging.getLogger(__name__)


def extract_metadata(scene_path: str | Path) -> dict:
    """
    Extract metadata from a GeoTIFF scene file.

    Returns a dict with keys:
        file_path, crs, bounds_minx, bounds_miny, bounds_maxx, bounds_maxy,
        width, height, band_count, file_size_bytes, sensor, acquisition_date
    """
    scene_path = Path(scene_path)

    if not scene_path.exists():
        raise FileNotFoundError(f"Scene file not found: {scene_path}")

    if not scene_path.suffix.lower() in (".tif", ".tiff", ".geotiff"):
        raise ValueError(f"Unsupported file format: {scene_path.suffix}")

    with rasterio.open(str(scene_path)) as ds:
        crs = str(ds.crs) if ds.crs else None
        bounds = ds.bounds

        # Convert bounds to EPSG:4326 (lat/lon) for consistent storage
        bounds_4326 = _transform_bounds(bounds, ds.crs)

        metadata = {
            "file_path": str(scene_path.resolve()),
            "crs": crs,
            "bounds_minx": bounds_4326[0] if bounds_4326 else bounds.left,
            "bounds_miny": bounds_4326[1] if bounds_4326 else bounds.bottom,
            "bounds_maxx": bounds_4326[2] if bounds_4326 else bounds.right,
            "bounds_maxy": bounds_4326[3] if bounds_4326 else bounds.top,
            "width": ds.width,
            "height": ds.height,
            "band_count": ds.count,
            "file_size_bytes": scene_path.stat().st_size,
        }

    # Try to extract sensor and date from filename
    metadata["sensor"] = _extract_sensor(scene_path.name)
    metadata["acquisition_date"] = _extract_date(scene_path.name)

    return metadata


def validate_scene(scene_path: str | Path) -> dict:
    """
    Validate a scene file for ingestion.

    Returns dict with:
        valid: bool
        errors: list[str]
        warnings: list[str]
    """
    scene_path = Path(scene_path)
    errors = []
    warnings = []

    # File exists
    if not scene_path.exists():
        return {"valid": False, "errors": ["File not found"], "warnings": []}

    # File format
    if scene_path.suffix.lower() not in (".tif", ".tiff", ".geotiff"):
        return {"valid": False, "errors": [f"Unsupported format: {scene_path.suffix}"], "warnings": []}

    # Try opening with rasterio
    try:
        with rasterio.open(str(scene_path)) as ds:
            # CRS check
            if ds.crs is None:
                warnings.append("No CRS defined — georeferencing may be lost")

            # Band count
            if ds.count == 0:
                errors.append("No bands found in raster")
            elif ds.count < 3:
                warnings.append(f"Only {ds.count} band(s) — RGB conversion may not be optimal")

            # Dimensions
            if ds.width == 0 or ds.height == 0:
                errors.append("Zero-dimension raster")

            # Readability
            try:
                _ = ds.read(1, window=rasterio.windows.Window(0, 0, min(10, ds.width), min(10, ds.height)))
            except Exception as e:
                errors.append(f"Cannot read raster data: {e}")

    except rasterio.errors.RasterioIOError as e:
        return {"valid": False, "errors": [f"Cannot open raster: {e}"], "warnings": []}

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }


def _transform_bounds(bounds, src_crs) -> Optional[tuple]:
    """Transform bounds to EPSG:4326 if possible."""
    if src_crs is None:
        return None

    try:
        transformer = Transformer.from_crs(src_crs, "EPSG:4326", always_xy=True)
        min_lon, min_lat = transformer.transform(bounds.left, bounds.bottom)
        max_lon, max_lat = transformer.transform(bounds.right, bounds.top)
        return (min_lon, min_lat, max_lon, max_lat)
    except Exception as e:
        logger.warning(f"Could not transform bounds to EPSG:4326: {e}")
        return None


def _extract_sensor(filename: str) -> Optional[str]:
    """Try to extract sensor name from filename using common conventions."""
    filename_upper = filename.upper()

    sensor_patterns = {
        "Sentinel-2": [r"S2[AB]?_", r"SENTINEL.?2", r"^S2_"],
        "Sentinel-1": [r"S1[AB]?_", r"SENTINEL.?1"],
        "Landsat-8": [r"LC08", r"LANDSAT.?8", r"L8_"],
        "Landsat-9": [r"LC09", r"LANDSAT.?9", r"L9_"],
        "MODIS": [r"MOD\d{2}", r"MYD\d{2}"],
        "PlanetScope": [r"PSScene", r"PLANET"],
    }

    for sensor_name, patterns in sensor_patterns.items():
        for pattern in patterns:
            if re.search(pattern, filename_upper):
                return sensor_name

    return None


def _extract_date(filename: str) -> Optional[str]:
    """Try to extract acquisition date from filename."""
    # Try common date patterns

    # YYYYMMDD
    match = re.search(r"(\d{4})(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])", filename)
    if match:
        try:
            date = datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))
            return date.strftime("%Y-%m-%d")
        except ValueError:
            pass

    # YYYY-MM-DD
    match = re.search(r"(\d{4})-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])", filename)
    if match:
        return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"

    # YYYY_MM_DD
    match = re.search(r"(\d{4})_(0[1-9]|1[0-2])_(0[1-9]|[12]\d|3[01])", filename)
    if match:
        return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"

    return None


def generate_scene_id(scene_path: str | Path, sensor: str | None = None, date: str | None = None) -> str:
    """
    Generate a unique scene ID from the file path and metadata.

    Format: {sensor}_{YYYYMMDD}_{stem} or just the filename stem if metadata unavailable.
    """
    stem = Path(scene_path).stem

    # Clean the stem to make it ID-safe
    safe_stem = re.sub(r"[^a-zA-Z0-9_-]", "_", stem)

    parts = []
    if sensor:
        parts.append(sensor.replace("-", "").replace(" ", "")[:4].upper())
    if date:
        parts.append(date.replace("-", ""))
    parts.append(safe_stem)

    return "_".join(parts)
