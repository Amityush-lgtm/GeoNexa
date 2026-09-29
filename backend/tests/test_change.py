"""
Unit tests for Change Detection & Confidence Scoring.
"""

import numpy as np
import pytest
from app.change.confidence import calculate_confidence_score, ConfidenceComponents
from app.change.quality import detect_cloud_cover, calculate_ndvi


def test_confidence_scoring():
    # Strong structural change, low confounders
    score, details = calculate_confidence_score(
        structural=0.85,
        seasonal_confound=0.10,
        cloud_contamination=0.05,
        registration_quality=0.95,
        persistence=0.80,
    )
    assert score > 0.70
    assert details.structural == 0.85

    # High seasonal confounder (crops) -> attenuated score
    score_seasonal, _ = calculate_confidence_score(
        structural=0.60,
        seasonal_confound=0.80,
        cloud_contamination=0.05,
        registration_quality=0.90,
        persistence=0.50,
    )
    assert score_seasonal < score


def test_ndvi_calculation():
    # NIR > Red -> positive NDVI
    red = np.array([50, 100], dtype=np.uint8)
    nir = np.array([200, 120], dtype=np.uint8)
    ndvi = calculate_ndvi(red, nir)

    assert ndvi[0] > 0.5  # High vegetation
    assert ndvi[1] > 0.05


def test_cloud_detection():
    # Clear tile
    clear_rgb = np.zeros((3, 100, 100), dtype=np.uint8) + 80
    assert detect_cloud_cover(clear_rgb) < 0.05

    # Cloudy tile (bright white)
    cloud_rgb = np.zeros((3, 100, 100), dtype=np.uint8) + 240
    assert detect_cloud_cover(cloud_rgb) > 0.80
