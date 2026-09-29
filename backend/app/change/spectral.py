"""
Spectral Index and Coregistration Verification for Earth Observation.

Computes physical spectral indices (NDVI, NDWI, NDBI) and sub-pixel phase correlation
to suppress false change alarms caused by registration shift, atmosphere, and seasonal phenology.
"""

import logging
from typing import Dict, Tuple, Optional
import numpy as np
from datetime import datetime

logger = logging.getLogger(__name__)


def compute_spectral_indices(img: np.ndarray) -> Dict[str, np.ndarray]:
    """
    Compute standard remote sensing spectral indices from multi-band / RGB+NIR arrays.
    
    Expected channels:
        4-band: [Red, Green, Blue, NIR] or (H, W, 4)
        3-band: [Red, Green, Blue] -> fallback indices via RGB color ratios
    """
    if img is None or img.size == 0:
        return {}
        
    img_f = img.astype(np.float32)
    h, w = img.shape[:2]
    
    # Check if 4th band (NIR) is present
    has_nir = (img.ndim == 3 and img.shape[2] >= 4)
    
    if has_nir:
        red = img_f[:, :, 0]
        green = img_f[:, :, 1]
        blue = img_f[:, :, 2]
        nir = img_f[:, :, 3]
        
        # NDVI = (NIR - Red) / (NIR + Red + eps)
        ndvi = (nir - red) / (nir + red + 1e-6)
        
        # NDWI (McFeeters) = (Green - NIR) / (Green + NIR + eps)
        ndwi = (green - nir) / (green + nir + 1e-6)
        
        # NDBI approximation = (Red - NIR) / (Red + NIR + 1e-6)
        ndbi = (red - nir) / (red + nir + 1e-6)
    else:
        # 3-band RGB fallback approximations (Visible Vegetation & Water indices)
        red = img_f[:, :, 0] if img.ndim == 3 else img_f
        green = img_f[:, :, 1] if img.ndim == 3 else img_f
        blue = img_f[:, :, 2] if img.ndim == 3 else img_f
        
        # GLI (Green Leaf Index) = (2*G - R - B) / (2*G + R + B + eps)
        ndvi = (2.0 * green - red - blue) / (2.0 * green + red + blue + 1e-6)
        # NDWI-RGB = (G - R) / (G + R + eps) & Blue dominance for water
        ndwi = (blue - red) / (blue + red + 1e-6)
        # Urban index = High red+green bright reflectance vs green
        ndbi = (red - green) / (red + green + 1e-6)

    return {
        "ndvi": np.clip(ndvi, -1.0, 1.0),
        "ndwi": np.clip(ndwi, -1.0, 1.0),
        "ndbi": np.clip(ndbi, -1.0, 1.0),
    }


def verify_spectral_change(
    t1_img: np.ndarray,
    t2_img: np.ndarray,
    change_mask: np.ndarray,
) -> Dict[str, any]:
    """
    Cross-validate detected change regions with physical spectral index deltas.
    
    Returns:
        delta_ndvi, delta_ndwi, delta_ndbi, primary_driver, physical_confirmation (bool)
    """
    if change_mask is None or np.sum(change_mask > 0) == 0:
        return {
            "delta_ndvi": 0.0,
            "delta_ndwi": 0.0,
            "delta_ndbi": 0.0,
            "primary_driver": "none",
            "physical_confirmation": False,
            "description": "No significant change pixels detected.",
        }

    idx1 = compute_spectral_indices(t1_img)
    idx2 = compute_spectral_indices(t2_img)
    
    mask = (change_mask > 0)
    
    delta_ndvi = float(np.mean(idx2["ndvi"][mask] - idx1["ndvi"][mask]))
    delta_ndwi = float(np.mean(idx2["ndwi"][mask] - idx1["ndwi"][mask]))
    delta_ndbi = float(np.mean(idx2["ndbi"][mask] - idx1["ndbi"][mask]))
    
    # Determine primary physical driver
    driver = "unclassified_structural"
    desc = "Structural change detected."
    confirmed = True
    
    if delta_ndwi > 0.18 and delta_ndvi < -0.10:
        driver = "water_inundation_or_flood"
        desc = f"Flood/water inundation verified by strong NDWI increase (+{delta_ndwi:.2f}) and vegetation decline ({delta_ndvi:.2f})."
    elif delta_ndvi < -0.22:
        driver = "vegetation_loss_or_clearing"
        desc = f"Vegetation canopy loss/clearing verified by significant NDVI decline ({delta_ndvi:.2f})."
    elif delta_ndvi > 0.22:
        driver = "vegetation_greening"
        desc = f"Vegetation growth/greening verified by significant NDVI increase (+{delta_ndvi:.2f})."
    elif delta_ndbi > 0.15 and delta_ndvi < -0.05:
        driver = "urban_construction_or_expansion"
        desc = f"Built-up / infrastructure expansion verified by high built-up index (+{delta_ndbi:.2f})."
    elif abs(delta_ndvi) < 0.08 and abs(delta_ndwi) < 0.08 and abs(delta_ndbi) < 0.08:
        # Low physical spectral change -> possible illumination / seasonal artifact
        driver = "illumination_or_texture_shift"
        desc = "Low spectral index shift across changed region; indicates possible illumination or shadow variation."
        confirmed = False

    return {
        "delta_ndvi": round(delta_ndvi, 4),
        "delta_ndwi": round(delta_ndwi, 4),
        "delta_ndbi": round(delta_ndbi, 4),
        "primary_driver": driver,
        "physical_confirmation": confirmed,
        "description": desc,
    }


def estimate_coregistration_shift(t1_img: np.ndarray, t2_img: np.ndarray) -> Dict[str, float]:
    """
    Estimate sub-pixel coregistration translation between T1 and T2 using phase correlation.
    
    Returns:
        shift_x, shift_y, registration_quality (0.0 to 1.0), edge_artifact_risk (0.0 to 1.0)
    """
    if t1_img is None or t2_img is None:
        return {"shift_x": 0.0, "shift_y": 0.0, "registration_quality": 0.5, "edge_artifact_risk": 0.0}
        
    g1 = np.mean(t1_img[:, :, :3], axis=2) if t1_img.ndim == 3 else t1_img.astype(np.float32)
    g2 = np.mean(t2_img[:, :, :3], axis=2) if t2_img.ndim == 3 else t2_img.astype(np.float32)
    
    # Compute 2D Fourier transforms
    f1 = np.fft.fft2(g1)
    f2 = np.fft.fft2(g2)
    
    # Cross-power spectrum
    eps = 1e-12
    cross_power = (f1 * np.conj(f2)) / (np.abs(f1 * np.conj(f2)) + eps)
    correlation = np.fft.ifft2(cross_power)
    correlation = np.abs(np.fft.fftshift(correlation))
    
    # Peak location
    h, w = g1.shape
    cy, cx = h // 2, w // 2
    max_idx = np.unravel_index(np.argmax(correlation), correlation.shape)
    shift_y = float(max_idx[0] - cy)
    shift_x = float(max_idx[1] - cx)
    
    total_shift = np.sqrt(shift_x**2 + shift_y**2)
    
    # Registration quality score (1.0 = perfectly aligned, drops if shift > 1.5 px)
    reg_quality = float(max(0.0, min(1.0, 1.0 - (total_shift / 5.0))))
    edge_risk = float(min(1.0, total_shift / 3.0)) if total_shift > 0.8 else 0.0
    
    return {
        "shift_x": round(shift_x, 2),
        "shift_y": round(shift_y, 2),
        "total_shift_pixels": round(float(total_shift), 2),
        "registration_quality": round(reg_quality, 4),
        "edge_artifact_risk": round(edge_risk, 4),
    }


def compute_seasonal_penalty(date_t1: Optional[str], date_t2: Optional[str]) -> Tuple[float, int]:
    """
    Calculate Day-Of-Year (DOY) difference and seasonal false-alarm penalty.
    
    Returns:
        seasonal_penalty (0.0 to 1.0), doy_difference_days
    """
    if not date_t1 or not date_t2:
        return 0.15, 0  # Neutral default
        
    try:
        d1 = datetime.strptime(date_t1[:10], "%Y-%m-%d")
        d2 = datetime.strptime(date_t2[:10], "%Y-%m-%d")
        
        doy1 = d1.timetuple().tm_yday
        doy2 = d2.timetuple().tm_yday
        
        # Circular DOY distance (accounting for year wraparound)
        raw_diff = abs(doy1 - doy2)
        circular_doy_diff = min(raw_diff, 365 - raw_diff)
        
        # Penalty scales up when DOY diff is between 60 and 180 days (opposite seasons)
        if circular_doy_diff < 30:
            penalty = 0.05  # Near same season: very low risk of false seasonal alarm
        elif circular_doy_diff < 75:
            penalty = 0.20
        elif circular_doy_diff < 140:
            penalty = 0.45
        else:
            penalty = 0.70  # Opposite season (e.g. wet monsoon vs dry winter)
            
        return round(penalty, 4), circular_doy_diff
    except Exception as e:
        logger.debug(f"Could not parse dates for DOY calculation: {e}")
        return 0.15, 0
