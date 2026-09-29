"""
Unit tests for Query Router intent classification.
"""

import pytest
from app.query.router import classify_query
from app.models.schemas import IntentType


def test_classify_change_query():
    text = "Show me changes and new construction between 2026-01-01 and 2026-05-01"
    res = classify_query(text)
    assert res.intent == IntentType.CHANGE_DETECTION
    assert res.suggested_action == "change"


def test_classify_similarity_query():
    text = "Find tiles similar to S2_20260115_001_x02_y04"
    res = classify_query(text)
    assert res.intent == IntentType.SIMILARITY_SEARCH
    assert res.suggested_action == "similar"


def test_classify_provenance_query():
    text = "Explain the provenance for prov-123456"
    res = classify_query(text)
    assert res.intent == IntentType.PROVENANCE_INSPECTION
    assert res.suggested_action == "provenance"


def test_classify_semantic_search():
    text = "Find water bodies, rivers and surrounding dense forest"
    res = classify_query(text)
    assert res.intent == IntentType.SEMANTIC_SEARCH
    assert res.suggested_action == "search"
