"""
Query router — classifies user intent using rule-based matching.

Routes queries to the appropriate service:
    SEMANTIC_SEARCH | IMAGE_SIMILARITY | CHANGE_ANALYSIS | VQA | PROVENANCE

Uses keyword/pattern matching — no LLM dependency for routing.
"""

import re
from typing import Optional


# Intent patterns — ordered by priority (first match wins)
INTENT_PATTERNS = {
    "PROVENANCE": {
        "keywords": ["source", "provenance", "trace", "origin", "where did", "came from", "processing"],
        "patterns": [r"where\s+did\s+this", r"source\s+of", r"how\s+was\s+this"],
        "weight": 1.0,
    },
    "CHANGE_ANALYSIS": {
        "keywords": ["changed", "change", "different", "before and after", "difference",
                      "evolution", "transformed", "developed", "constructed", "demolished",
                      "cleared", "built", "grown", "expanded", "shrunk"],
        "patterns": [r"what\s+(has\s+)?changed", r"any\s+changes?", r"detect\s+change",
                     r"before\s+and\s+after", r"how\s+has\s+.+\s+changed"],
        "weight": 0.9,
    },
    "IMAGE_SIMILARITY": {
        "keywords": ["similar", "like this", "looks like", "resembles", "matching",
                      "find more", "more like", "same kind"],
        "patterns": [r"similar\s+(to|locations?|sites?|areas?|images?)",
                     r"find\s+(more\s+)?like", r"looks?\s+like\s+this"],
        "weight": 0.85,
    },
    "VQA": {
        "keywords": ["what is", "describe", "identify", "visible", "see",
                      "recognize", "land use", "land cover", "features"],
        "patterns": [r"what\s+is\s+(visible|shown|this|in\s+this)",
                     r"describe\s+(this|the)", r"what\s+can\s+you\s+see",
                     r"identify\s+the"],
        "weight": 0.8,
    },
    "SEMANTIC_SEARCH": {
        "keywords": ["find", "search", "show", "locate", "where", "look for",
                      "discover", "structures", "buildings", "water", "river",
                      "road", "vegetation", "urban", "rural", "forest", "field",
                      "airport", "port", "dam", "bridge"],
        "patterns": [r"find\s+.+", r"search\s+for", r"show\s+me",
                     r"where\s+(are|is|can)", r"locate\s+"],
        "weight": 0.7,
    },
}


def classify_query(text: str, tile_id: Optional[str] = None) -> dict:
    """
    Classify a query into an intent.

    Uses keyword matching and regex patterns with priority weighting.
    Context (e.g., whether a tile is selected) influences classification.

    Args:
        text: User's natural-language input.
        tile_id: Currently selected tile ID (provides context).

    Returns:
        dict with: intent, confidence, original_text, parameters
    """
    text_lower = text.lower().strip()
    scores = {}

    for intent, config in INTENT_PATTERNS.items():
        score = 0.0

        # Keyword matching
        for keyword in config["keywords"]:
            if keyword in text_lower:
                score += config["weight"] * 0.5

        # Pattern matching
        for pattern in config["patterns"]:
            if re.search(pattern, text_lower):
                score += config["weight"] * 0.7
                break  # One pattern match is enough

        scores[intent] = score

    # Context boost: if a tile is selected, boost change/similarity/VQA
    if tile_id:
        for intent in ["CHANGE_ANALYSIS", "IMAGE_SIMILARITY", "VQA"]:
            scores[intent] *= 1.3

    # Default to semantic search if no strong match
    best_intent = max(scores, key=scores.get)
    best_score = scores[best_intent]

    if best_score < 0.1:
        best_intent = "SEMANTIC_SEARCH"
        best_score = 0.5

    # Normalize confidence
    total = sum(scores.values()) if sum(scores.values()) > 0 else 1
    confidence = best_score / total

    return {
        "intent": best_intent,
        "confidence": round(min(1.0, confidence), 3),
        "original_text": text,
        "parameters": _extract_parameters(text, best_intent),
    }


def _extract_parameters(text: str, intent: str) -> dict:
    """Extract intent-specific parameters from the query text."""
    params = {}

    # Try to extract date references
    date_match = re.search(r"(\d{4}[-/]\d{2}[-/]\d{2})", text)
    if date_match:
        params["date_reference"] = date_match.group(1)

    # Try to extract location references
    coord_match = re.search(r"(\d+\.?\d*)[°,]\s*(\d+\.?\d*)", text)
    if coord_match:
        params["location_reference"] = {
            "lat": float(coord_match.group(1)),
            "lon": float(coord_match.group(2)),
        }

    return params
