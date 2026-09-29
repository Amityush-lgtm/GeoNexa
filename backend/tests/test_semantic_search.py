"""
Unit and integration tests for semantic search and metadata filtering.
"""

import pytest
from app.retrieval.filters import apply_metadata_filters


def test_metadata_filters_date_and_sensor():
    results = [
        {"tile_id": "t1", "date": "2026-01-15", "sensor": "Sentinel-2", "bbox": [91.65, 26.10, 91.70, 26.15]},
        {"tile_id": "t2", "date": "2026-03-20", "sensor": "Sentinel-2", "bbox": [91.70, 26.15, 91.75, 26.20]},
        {"tile_id": "t3", "date": "2026-05-10", "sensor": "Landsat-8", "bbox": [91.75, 26.20, 91.80, 26.25]},
    ]

    # Filter by date range
    filtered = apply_metadata_filters(results, date_from="2026-02-01", date_to="2026-04-01")
    assert len(filtered) == 1
    assert filtered[0]["tile_id"] == "t2"

    # Filter by sensor
    filtered_sensor = apply_metadata_filters(results, sensor="Landsat-8")
    assert len(filtered_sensor) == 1
    assert filtered_sensor[0]["tile_id"] == "t3"


def test_metadata_filters_bbox():
    results = [
        {"tile_id": "t1", "bbox": [91.65, 26.10, 91.70, 26.15]},
        {"tile_id": "t2", "bbox": [92.00, 27.00, 92.10, 27.10]},  # Far outside
    ]

    filtered = apply_metadata_filters(results, bbox=[91.60, 26.00, 91.80, 26.20])
    assert len(filtered) == 1
    assert filtered[0]["tile_id"] == "t1"
