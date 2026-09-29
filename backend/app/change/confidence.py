"""
Confidence scoring for change detection.

Combines structural change magnitude, confounder risks, and quality metrics
into a single calibrated confidence score with labeled tiers.
"""

import numpy as np


# Weight configuration — documented for reproducibility
WEIGHTS = {
    "structural": 0.40,
    "persistence": 0.25,
    "registration_quality": 0.15,
    "seasonal_confound": -0.10,
    "cloud_contamination": -0.10,
}


def compute_confidence(
    diff_magnitude: np.ndarray,
    change_mask: np.ndarray,
    t1_quality: dict,
    t2_quality: dict,
    change_pixels: int,
    total_pixels: int,
) -> dict:
    """
    Compute a multi-factor confidence score for a change detection result.

    Factors:
    - Structural: How strong is the detected change signal?
    - Seasonal confound: Risk of seasonal false alarm.
    - Cloud contamination: Cloud/haze presence in either observation.
    - Registration quality: Estimated alignment quality.
    - Persistence: Placeholder for multi-date confirmation (future).

    Args:
        diff_magnitude: Difference magnitude array.
        change_mask: Binary change mask.
        t1_quality: Quality metrics for T1.
        t2_quality: Quality metrics for T2.
        change_pixels: Number of change pixels.
        total_pixels: Total pixels.

    Returns:
        dict with individual scores and final combined score.
    """
    # Structural confidence — based on mean magnitude in change regions
    if change_pixels > 0:
        mean_change_magnitude = float(np.mean(diff_magnitude[change_mask > 0]))
        # Normalize: magnitude of 100+ is very strong, 30 is threshold
        structural = min(1.0, max(0.0, (mean_change_magnitude - 30) / 100))
    else:
        structural = 0.0

    # Seasonal confound risk
    # Higher if changes are diffuse (scattered small changes = likely seasonal)
    change_ratio = change_pixels / total_pixels if total_pixels > 0 else 0
    if change_ratio > 0.5:
        # More than 50% changed = suspicious (seasonal/atmospheric)
        seasonal_confound = 0.8
    elif change_ratio > 0.3:
        seasonal_confound = 0.5
    elif change_ratio > 0.15:
        seasonal_confound = 0.3
    else:
        seasonal_confound = 0.1

    # Cloud contamination — from quality checks
    cloud_t1 = t1_quality.get("cloud_fraction", 0)
    cloud_t2 = t2_quality.get("cloud_fraction", 0)
    cloud_contamination = max(cloud_t1, cloud_t2)

    # Registration quality — estimated from image quality consistency
    # Better quality in both images → better registration assumed
    reg_q1 = t1_quality.get("overall_quality", 0.5)
    reg_q2 = t2_quality.get("overall_quality", 0.5)
    registration_quality = min(reg_q1, reg_q2)

    # Persistence — placeholder for multi-date confirmation
    # Requires temporal stack analysis (future implementation)
    persistence = 0.5  # Neutral default

    # Compute final score
    final_score = (
        structural * WEIGHTS["structural"]
        + persistence * WEIGHTS["persistence"]
        + registration_quality * WEIGHTS["registration_quality"]
        + seasonal_confound * WEIGHTS["seasonal_confound"]
        + cloud_contamination * WEIGHTS["cloud_contamination"]
    )
    final_score = max(0.0, min(1.0, final_score))

    # Label
    if final_score >= 0.7:
        label = "HIGH"
    elif final_score >= 0.4:
        label = "MEDIUM"
    else:
        label = "LOW"

    return {
        "structural": round(structural, 4),
        "seasonal_confound": round(seasonal_confound, 4),
        "cloud_contamination": round(cloud_contamination, 4),
        "registration_quality": round(registration_quality, 4),
        "persistence": round(persistence, 4),
        "final_score": round(final_score, 4),
        "label": label,
    }
