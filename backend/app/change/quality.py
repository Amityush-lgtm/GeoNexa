"""
Quality checks for change detection.

Identifies confounders (clouds, haze, saturation, low illumination)
and normalizes image pairs for fair comparison.
"""

import logging
from typing import Tuple

import numpy as np

logger = logging.getLogger(__name__)


def quality_check(image: np.ndarray) -> dict:
    """
    Assess image quality for change detection suitability.

    Checks for:
    - Cloud/haze (high-brightness saturation)
    - Low illumination (dark images)
    - Dynamic range
    - Saturation percentage

    Args:
        image: RGB image as numpy array (H, W, 3) in [0, 255].

    Returns:
        dict with quality metrics:
            cloud_fraction, dark_fraction, dynamic_range,
            saturation_fraction, overall_quality (0–1)
    """
    if image is None or image.size == 0:
        return {
            "cloud_fraction": 1.0,
            "dark_fraction": 1.0,
            "dynamic_range": 0.0,
            "saturation_fraction": 1.0,
            "overall_quality": 0.0,
        }

    gray = np.mean(image, axis=2) if image.ndim == 3 else image.astype(np.float32)
    total_pixels = gray.shape[0] * gray.shape[1]

    # Cloud/haze: very bright pixels (>230)
    cloud_pixels = np.sum(gray > 230)
    cloud_fraction = cloud_pixels / total_pixels

    # Dark: very dark pixels (<15)
    dark_pixels = np.sum(gray < 15)
    dark_fraction = dark_pixels / total_pixels

    # Dynamic range
    dynamic_range = float(np.percentile(gray, 98) - np.percentile(gray, 2))

    # Saturation: pixels at max value
    if image.ndim == 3:
        sat_pixels = np.sum(np.any(image >= 250, axis=2))
    else:
        sat_pixels = np.sum(image >= 250)
    saturation_fraction = sat_pixels / total_pixels

    # Overall quality score
    overall = 1.0
    overall -= cloud_fraction * 0.5      # Clouds heavily penalize
    overall -= dark_fraction * 0.3       # Darkness moderately penalizes
    overall -= saturation_fraction * 0.2  # Saturation lightly penalizes
    if dynamic_range < 50:
        overall -= 0.2                    # Low contrast

    overall = max(0.0, min(1.0, overall))

    return {
        "cloud_fraction": round(float(cloud_fraction), 4),
        "dark_fraction": round(float(dark_fraction), 4),
        "dynamic_range": round(float(dynamic_range), 2),
        "saturation_fraction": round(float(saturation_fraction), 4),
        "overall_quality": round(float(overall), 4),
    }


def normalize_pair(
    t1: np.ndarray,
    t2: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Normalize a pair of images for change detection.

    Uses histogram matching to align the radiometric distribution
    of T2 to T1, reducing false positives from illumination/atmosphere.

    Args:
        t1: Earlier observation (H, W, C) in [0, 255].
        t2: Later observation (H, W, C) in [0, 255].

    Returns:
        Tuple of normalized (t1, t2) as float32 arrays.
    """
    t1_float = t1.astype(np.float32)
    t2_float = t2.astype(np.float32)

    # Per-channel histogram matching of T2 to T1
    if t1.ndim == 3 and t2.ndim == 3:
        channels = t1.shape[2]
        t2_matched = np.zeros_like(t2_float)
        for c in range(channels):
            t2_matched[:, :, c] = _histogram_match_channel(
                t2_float[:, :, c], t1_float[:, :, c]
            )
        return t1_float, t2_matched
    else:
        t2_matched = _histogram_match_channel(t2_float, t1_float)
        return t1_float, t2_matched


def _histogram_match_channel(source: np.ndarray, reference: np.ndarray) -> np.ndarray:
    """
    Match the histogram of source to reference (single channel).

    Uses cumulative distribution function matching.
    """
    # Compute histograms
    src_values, src_indices, src_counts = np.unique(
        source.ravel().astype(np.int32).clip(0, 255), return_inverse=True, return_counts=True
    )
    ref_values, ref_counts = np.unique(
        reference.ravel().astype(np.int32).clip(0, 255), return_counts=True
    )

    # CDFs
    src_cdf = np.cumsum(src_counts).astype(np.float64)
    src_cdf /= src_cdf[-1]

    ref_cdf = np.cumsum(ref_counts).astype(np.float64)
    ref_cdf /= ref_cdf[-1]

    # Map source values to reference values
    mapped = np.interp(src_cdf, ref_cdf, ref_values.astype(np.float64))

    # Apply mapping
    result = mapped[src_indices].reshape(source.shape)
    return result.astype(np.float32)
