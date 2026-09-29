"""
Unit tests for Change Detection, Quality Checks, and Confidence Scoring.
"""

import numpy as np
import pytest
from app.change.confidence import compute_confidence
from app.change.quality import quality_check, normalize_pair


def test_confidence_scoring():
    diff_magnitude = np.zeros((100, 100), dtype=np.float32)
    diff_magnitude[20:50, 20:50] = 120.0  # Strong magnitude
    change_mask = (diff_magnitude > 30).astype(np.uint8)

    t1_quality = {"cloud_fraction": 0.05, "overall_quality": 0.9}
    t2_quality = {"cloud_fraction": 0.05, "overall_quality": 0.9}

    res = compute_confidence(
        diff_magnitude=diff_magnitude,
        change_mask=change_mask,
        t1_quality=t1_quality,
        t2_quality=t2_quality,
        change_pixels=int(np.sum(change_mask)),
        total_pixels=10000,
    )

    assert "final_score" in res
    assert "structural" in res
    assert "seasonal_confound" in res
    assert "cloud_contamination" in res
    assert res["final_score"] > 0.0



def test_quality_check_clear_and_cloudy():
    # Clear image
    clear_img = np.zeros((100, 100, 3), dtype=np.uint8) + 100
    q_clear = quality_check(clear_img)
    assert q_clear["cloud_fraction"] == 0.0
    assert q_clear["overall_quality"] > 0.6

    # Cloudy image (saturated bright pixels > 230)
    cloud_img = np.zeros((100, 100, 3), dtype=np.uint8) + 245
    q_cloud = quality_check(cloud_img)
    assert q_cloud["cloud_fraction"] == 1.0
    assert q_cloud["overall_quality"] < q_clear["overall_quality"]


def test_normalize_pair():
    t1 = np.random.randint(50, 200, (64, 64, 3), dtype=np.uint8)
    t2 = np.random.randint(80, 220, (64, 64, 3), dtype=np.uint8)

    t1_norm, t2_norm = normalize_pair(t1, t2)
    assert t1_norm.shape == (64, 64, 3)
    assert t2_norm.shape == (64, 64, 3)
