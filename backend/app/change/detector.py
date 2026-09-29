"""
Change detection pipeline.

Detects meaningful changes between two temporal observations of the same location.
Uses deterministic pixel-based methods with false-alarm suppression.
"""

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image

from app.change.confidence import compute_confidence
from app.change.quality import quality_check, normalize_pair
from app.db import get_connection
from app.config import get_settings

logger = logging.getLogger(__name__)


def detect_changes(
    t1_path: str,
    t2_path: str,
    t1_tile_id: str,
    t2_tile_id: str,
    tile_id: str,
    output_dir: Optional[str] = None,
) -> dict:
    """
    Detect changes between two temporal observations.

    Pipeline:
        1. Load images
        2. Quality check (cloud, haze, validity)
        3. Normalize radiometry
        4. Compute difference
        5. Threshold + morphological filtering
        6. Connected component analysis
        7. Generate change mask
        8. Compute confidence
        9. Save results

    Args:
        t1_path: Path to earlier observation tile.
        t2_path: Path to later observation tile.
        t1_tile_id: Tile ID for T1.
        t2_tile_id: Tile ID for T2.
        tile_id: Primary tile ID for the analysis.
        output_dir: Directory to save change mask.

    Returns:
        dict with analysis results
    """
    analysis_id = f"chg-{uuid.uuid4().hex[:8]}"
    settings = get_settings()

    if output_dir is None:
        output_dir = Path(settings.data_dir) / "change_results"
    else:
        output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        # 1. Load images
        t1_img = _load_image(t1_path)
        t2_img = _load_image(t2_path)

        if t1_img is None or t2_img is None:
            return _error_result(analysis_id, tile_id, t1_tile_id, t2_tile_id, "Failed to load images")

        # Ensure same dimensions
        if t1_img.shape != t2_img.shape:
            # Resize to match
            min_h = min(t1_img.shape[0], t2_img.shape[0])
            min_w = min(t1_img.shape[1], t2_img.shape[1])
            t1_img = t1_img[:min_h, :min_w]
            t2_img = t2_img[:min_h, :min_w]

        # 2. Quality check
        q1 = quality_check(t1_img)
        q2 = quality_check(t2_img)

        # 3. Normalize
        t1_norm, t2_norm = normalize_pair(t1_img, t2_img)

        # 4. Compute difference (per-channel, then magnitude)
        diff = np.abs(t2_norm.astype(np.float32) - t1_norm.astype(np.float32))
        diff_magnitude = np.mean(diff, axis=2) if diff.ndim == 3 else diff

        # 5. Threshold
        threshold = _compute_adaptive_threshold(diff_magnitude)
        binary_mask = (diff_magnitude > threshold).astype(np.uint8)

        # 6. Morphological filtering (remove noise)
        binary_mask = _morphological_clean(binary_mask)

        # 7. Connected component analysis + size filtering
        binary_mask, num_components = _filter_small_components(binary_mask, min_area=50)

        # 8. Compute statistics
        change_pixels = int(np.sum(binary_mask > 0))
        total_pixels = int(binary_mask.shape[0] * binary_mask.shape[1])
        change_percentage = (change_pixels / total_pixels * 100) if total_pixels > 0 else 0

        # 9. Compute confidence
        confidence = compute_confidence(
            diff_magnitude=diff_magnitude,
            change_mask=binary_mask,
            t1_quality=q1,
            t2_quality=q2,
            change_pixels=change_pixels,
            total_pixels=total_pixels,
        )

        # 10. Save change mask
        mask_path = output_dir / f"{analysis_id}_mask.png"
        _save_change_mask(binary_mask, diff_magnitude, mask_path)

        # 11. Record in database
        now = datetime.now(timezone.utc).isoformat()
        _record_analysis(
            analysis_id, tile_id, t1_tile_id, t2_tile_id,
            confidence, str(mask_path), change_pixels, total_pixels, now,
        )

        return {
            "analysis_id": analysis_id,
            "tile_id": tile_id,
            "t1_tile_id": t1_tile_id,
            "t2_tile_id": t2_tile_id,
            "change_type": _classify_change(change_percentage, confidence),
            "confidence": confidence,
            "change_mask_path": str(mask_path),
            "change_pixels": change_pixels,
            "total_pixels": total_pixels,
            "change_percentage": round(change_percentage, 2),
            "status": "completed",
        }

    except Exception as e:
        logger.error(f"Change detection failed: {e}", exc_info=True)
        return _error_result(analysis_id, tile_id, t1_tile_id, t2_tile_id, str(e))


def find_earliest_supported(tile_id: str, observations: list) -> Optional[str]:
    """
    Find the earliest supported observation of a change.

    Walks backward through temporal observations to find the earliest
    date where the change is still present.

    Args:
        tile_id: Primary tile ID.
        observations: Sorted list of temporal observation dicts.

    Returns:
        Date string of the earliest supported observation, or None.
    """
    if len(observations) < 2:
        return None

    # Use the latest observation as reference (assumed to show the change)
    ref_path = _tile_id_to_path(observations[-1]["tile_id"])
    if ref_path is None:
        return None

    ref_img = _load_image(ref_path)
    if ref_img is None:
        return None

    earliest = observations[-1].get("date")

    # Walk backward
    for obs in reversed(observations[:-1]):
        obs_path = _tile_id_to_path(obs["tile_id"])
        if obs_path is None:
            continue

        obs_img = _load_image(obs_path)
        if obs_img is None:
            continue

        # Quick change check
        result = detect_changes(
            obs_path, ref_path,
            obs["tile_id"], observations[-1]["tile_id"],
            tile_id,
        )

        if result["status"] == "completed" and result["change_percentage"] > 2.0:
            earliest = obs.get("date")
        else:
            break  # No more change detected — stop

    return earliest


def _load_image(path: str) -> Optional[np.ndarray]:
    """Load a raster tile as RGB numpy array."""
    try:
        import rasterio
        with rasterio.open(path) as ds:
            bands = min(ds.count, 3)
            data = ds.read(list(range(1, bands + 1)))

            if bands == 1:
                data = np.repeat(data, 3, axis=0)
            elif bands == 2:
                data = np.concatenate([data, np.zeros_like(data[:1])], axis=0)

            image = np.transpose(data, (1, 2, 0))  # CHW → HWC

            if image.dtype != np.uint8:
                vmin, vmax = np.percentile(image[image > 0], [2, 98]) if image.any() else (0, 1)
                if vmax > vmin:
                    image = np.clip((image - vmin) / (vmax - vmin) * 255, 0, 255).astype(np.uint8)
                else:
                    image = np.zeros_like(image, dtype=np.uint8)

            return image
    except Exception as e:
        logger.error(f"Failed to load image {path}: {e}")
        return None


def _compute_adaptive_threshold(diff_magnitude: np.ndarray) -> float:
    """Compute an adaptive threshold based on the difference distribution."""
    mean_diff = np.mean(diff_magnitude)
    std_diff = np.std(diff_magnitude)
    # Threshold at mean + 2*std, with minimum of 30
    return max(mean_diff + 2.0 * std_diff, 30.0)


def _morphological_clean(mask: np.ndarray) -> np.ndarray:
    """Apply morphological operations to remove noise."""
    try:
        from skimage.morphology import binary_opening, binary_closing, disk
        selem = disk(2)
        mask = binary_opening(mask.astype(bool), selem).astype(np.uint8)
        mask = binary_closing(mask.astype(bool), selem).astype(np.uint8)
    except ImportError:
        # Fallback: no morphological filtering
        pass
    return mask


def _filter_small_components(mask: np.ndarray, min_area: int = 50) -> tuple:
    """Remove connected components smaller than min_area pixels."""
    try:
        from skimage.measure import label
        labeled = label(mask, connectivity=2)
        num_components = labeled.max()

        filtered = np.zeros_like(mask)
        for i in range(1, num_components + 1):
            component = (labeled == i)
            if np.sum(component) >= min_area:
                filtered[component] = 1

        return filtered, int(filtered.max())
    except ImportError:
        return mask, 1


def _save_change_mask(mask: np.ndarray, diff_magnitude: np.ndarray, path: Path) -> None:
    """Save change mask as a color-coded PNG."""
    # Create color mask: red for change, green for no-change
    h, w = mask.shape
    color_mask = np.zeros((h, w, 3), dtype=np.uint8)

    # Normalize diff for visualization
    if diff_magnitude.max() > 0:
        intensity = (diff_magnitude / diff_magnitude.max() * 255).astype(np.uint8)
    else:
        intensity = np.zeros_like(diff_magnitude, dtype=np.uint8)

    # Change pixels in red, with intensity
    color_mask[mask > 0, 0] = intensity[mask > 0]  # Red channel
    color_mask[mask == 0, 1] = 50  # Faint green for no-change

    Image.fromarray(color_mask).save(str(path))


def _classify_change(change_percentage: float, confidence: dict) -> Optional[str]:
    """Rough change type classification based on magnitude."""
    if change_percentage < 1.0:
        return None  # No significant change
    if confidence.get("final_score", 0) < 0.3:
        return None  # Low confidence

    # For MVP, we report "detected change" rather than fabricating specific types
    if change_percentage > 15:
        return "major_change"
    elif change_percentage > 5:
        return "moderate_change"
    else:
        return "minor_change"


def _tile_id_to_path(tile_id: str) -> Optional[str]:
    """Look up the file path for a tile ID."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT file_path FROM tiles WHERE tile_id = ?", (tile_id,)
        ).fetchone()
    return row["file_path"] if row else None


def _error_result(analysis_id: str, tile_id: str, t1: str, t2: str, message: str) -> dict:
    """Build an error result."""
    return {
        "analysis_id": analysis_id,
        "tile_id": tile_id,
        "t1_tile_id": t1,
        "t2_tile_id": t2,
        "change_type": None,
        "confidence": {"structural": 0, "seasonal_confound": 0, "cloud_contamination": 0,
                       "registration_quality": 0, "persistence": 0, "final_score": 0, "label": "ERROR"},
        "change_mask_path": None,
        "change_pixels": 0,
        "total_pixels": 0,
        "change_percentage": 0,
        "status": "error",
        "error": message,
    }


def _record_analysis(
    analysis_id: str, tile_id: str, t1_tile_id: str, t2_tile_id: str,
    confidence: dict, mask_path: str, change_pixels: int, total_pixels: int, now: str,
) -> None:
    """Record change analysis in the database."""
    try:
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO change_analyses (
                    analysis_id, tile_id, t1_tile_id, t2_tile_id,
                    confidence, structural_confidence, seasonal_confound,
                    cloud_contamination, registration_quality, persistence_score,
                    change_mask_path, change_pixels, total_pixels,
                    status, created_at, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    analysis_id, tile_id, t1_tile_id, t2_tile_id,
                    confidence.get("final_score"),
                    confidence.get("structural"),
                    confidence.get("seasonal_confound"),
                    confidence.get("cloud_contamination"),
                    confidence.get("registration_quality"),
                    confidence.get("persistence"),
                    mask_path, change_pixels, total_pixels,
                    "completed", now, now,
                ),
            )
            conn.commit()
    except Exception as e:
        logger.warning(f"Failed to record analysis: {e}")
