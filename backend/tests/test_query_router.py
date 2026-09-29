"""
Unit tests for Query Router intent classification.
"""

import pytest
from app.query.router import classify_query


def test_classify_change_query():
    text = "what has changed in this area"
    res = classify_query(text)
    assert res["intent"] == "CHANGE_ANALYSIS"
    assert res["confidence"] > 0.5



def test_classify_similarity_query():
    text = "Find locations similar to this site"
    res = classify_query(text, tile_id="tile_123")
    assert res["intent"] == "IMAGE_SIMILARITY"
    assert res["confidence"] > 0.5


def test_classify_provenance_query():
    text = "Where did this data come from and what is the provenance trace"
    res = classify_query(text)
    assert res["intent"] == "PROVENANCE"
    assert res["confidence"] > 0.5


def test_classify_semantic_search():
    text = "Find water bodies, rivers and surrounding dense forest"
    res = classify_query(text)
    assert res["intent"] == "SEMANTIC_SEARCH"
