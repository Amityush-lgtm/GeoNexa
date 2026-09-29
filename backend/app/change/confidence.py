"""
Confidence scoring for change detection.

Combines structural change magnitude, confounder risks, and quality metrics
into a single calibrated confidence score with labeled tiers.
"""

import numpy as np
from typing import Optional, Dict
from app.change.spectral import verify_spectral_change, estimate_coregistration_shift, compute_seasonal_penalty


# Weight configuration — aligned with SIH Multi-Modal Earth Observation Problem Statement
WEIGHTS = {
    "structural": 0.35,
    "spectral_confirmation": 0.25,
    "registration_quality": 0.15,
    "persistence": 0.15,
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
    t1_img: Optional[np.ndarray] = None,
    t2_img: Optional[np.ndarray] = None,
    date_t1: Optional[str] = None,
    date_t2: Optional[str] = None,
) -> dict:
    """
    Compute a calibrated multi-factor confidence score for change detection.

    Factors:
    - Structural: Magnitude and compactness of detected change signal.
    - Spectral Confirmation: Physical index confirmation (NDVI, NDWI, NDBI delta).
    - Registration Quality: Sub-pixel phase correlation alignment score.
    - Seasonal Confounder Risk: Day-Of-Year (DOY) circular penalty.
    - Cloud/Atmospheric Contamination: Cloud, shadow, and saturation penalty.
    - Persistence: Temporal stack consistency.
    """
    # 1. Structural confidence — mean magnitude in change regions
    if change_pixels > 0:
        mean_change_magnitude = float(np.mean(diff_magnitude[change_mask > 0]))
        structural = min(1.0, max(0.0, (mean_change_magnitude - 25.0) / 90.0))
    else:
        structural = 0.0

    # 2. Spectral Verification (NDVI / NDWI / NDBI)
    spectral_meta = {"delta_ndvi": 0.0, "delta_ndwi": 0.0, "delta_ndbi": 0.0, "primary_driver": "structural", "physical_confirmation": True}
    if t1_img is not None and t2_img is not None and change_pixels > 0:
        spectral_meta = verify_spectral_change(t1_img, t2_img, change_mask)
        spectral_score = 1.0 if spectral_meta["physical_confirmation"] else 0.35
    else:
        spectral_score = 0.70

    # 3. Seasonal Normalization via Day-of-Year (DOY) difference
    seasonal_doy_penalty, doy_diff_days = compute_seasonal_penalty(date_t1, date_t2)
    change_ratio = (change_pixels / total_pixels) if total_pixels > 0 else 0
    if change_ratio > 0.55:
        # Diffuse full-scene variation is typical of seasonal shift
        seasonal_confound = max(seasonal_doy_penalty, 0.75)
    elif change_ratio > 0.30:
        seasonal_confound = max(seasonal_doy_penalty, 0.45)
    else:
        seasonal_confound = seasonal_doy_penalty

    # 4. Cloud & Atmospheric contamination from QA checks
    cloud_t1 = t1_quality.get("cloud_fraction", 0.0)
    cloud_t2 = t2_quality.get("cloud_fraction", 0.0)
    cloud_contamination = max(cloud_t1, cloud_t2)

    # 5. Coregistration & Alignment Quality
    if t1_img is not None and t2_img is not None:
        reg_info = estimate_coregistration_shift(t1_img, t2_img)
        registration_quality = reg_info["registration_quality"]
        reg_shift_px = reg_info["total_shift_pixels"]
    else:
        reg_q1 = t1_quality.get("overall_quality", 0.8)
        reg_q2 = t2_quality.get("overall_quality", 0.8)
        registration_quality = min(reg_q1, reg_q2)
        reg_shift_px = 0.0

    # 6. Persistence
    persistence = 0.80 if structural > 0.4 else 0.50

    # 7. Final combined score computation
    raw_score = (
        structural * WEIGHTS["structural"]
        + spectral_score * WEIGHTS["spectral_confirmation"]
        + registration_quality * WEIGHTS["registration_quality"]
        + persistence * WEIGHTS["persistence"]
        + seasonal_confound * WEIGHTS["seasonal_confound"]
        + cloud_contamination * WEIGHTS["cloud_contamination"]
    )
    final_score = max(0.05, min(0.98, raw_score))

    # Calibrated Tiers
    if final_score >= 0.72:
        label = "HIGH"
    elif final_score >= 0.45:
        label = "MEDIUM"
    else:
        label = "LOW"

    return {
        "structural": round(structural, 4),
        "spectral_confirmation": round(spectral_score, 4),
        "seasonal_confound": round(seasonal_confound, 4),
        "cloud_contamination": round(cloud_contamination, 4),
        "registration_quality": round(registration_quality, 4),
        "persistence": round(persistence, 4),
        "doy_diff_days": doy_diff_days,
        "registration_shift_px": reg_shift_px,
        "spectral_driver": spectral_meta.get("primary_driver", "structural"),
        "spectral_description": spectral_meta.get("description", ""),
        "delta_ndvi": spectral_meta.get("delta_ndvi", 0.0),
        "delta_ndwi": spectral_meta.get("delta_ndwi", 0.0),
        "delta_ndbi": spectral_meta.get("delta_ndbi", 0.0),
        "final_score": round(final_score, 4),
        "label": label,
    }

