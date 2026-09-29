"""
Post-retrieval metadata filtering.

Applies date, sensor, and spatial (bbox) filters AFTER vector search.
This narrows the candidate set without replacing semantic retrieval.
"""

from typing import Optional, List


def apply_metadata_filters(
    results: List[dict],
    bbox: Optional[List[float]] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    sensor: Optional[str] = None,
) -> List[dict]:
    """
    Filter search results by metadata constraints.

    Applied after FAISS retrieval to refine the candidate set.

    Args:
        results: List of result dicts (from _join_metadata).
        bbox: [lon_min, lat_min, lon_max, lat_max].
        date_from: Earliest date (inclusive) YYYY-MM-DD.
        date_to: Latest date (inclusive) YYYY-MM-DD.
        sensor: Sensor name to filter by.

    Returns:
        Filtered list of result dicts (order preserved).
    """
    filtered = results

    if bbox:
        filtered = _filter_bbox(filtered, bbox)

    if date_from:
        filtered = [r for r in filtered if r.get("date") and r["date"] >= date_from]

    if date_to:
        filtered = [r for r in filtered if r.get("date") and r["date"] <= date_to]

    if sensor:
        sensor_lower = sensor.lower()
        filtered = [
            r for r in filtered
            if r.get("sensor") and r["sensor"].lower() == sensor_lower
        ]

    return filtered


def _filter_bbox(results: List[dict], bbox: List[float]) -> List[dict]:
    """
    Filter results by bounding box intersection.

    A result matches if its bbox overlaps with the query bbox.
    """
    lon_min, lat_min, lon_max, lat_max = bbox

    filtered = []
    for r in results:
        r_bbox = r.get("bbox", [])
        if len(r_bbox) != 4:
            continue

        r_lon_min, r_lat_min, r_lon_max, r_lat_max = r_bbox

        # Check for overlap (not disjoint)
        if (r_lon_max >= lon_min and r_lon_min <= lon_max and
                r_lat_max >= lat_min and r_lat_min <= lat_max):
            filtered.append(r)

    return filtered
