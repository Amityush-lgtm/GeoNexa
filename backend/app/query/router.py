"""
Natural Language Query Parser & Intent Router for Earth Observation.

Classifies user intent (SEMANTIC_SEARCH | IMAGE_SIMILARITY | CHANGE_ANALYSIS | VQA | PROVENANCE)
and extracts structured filters from free-form queries:
- Spatial: Named regions (Assam, Guwahati, Mumbai, Kerala, etc.) or bounding boxes / coordinates
- Temporal: ISO dates, month names, years, ranges ("between July and August 2024", "in 2025")
- Cloud cover: "cloud cover < 15%", "cloud < 20%"
- Sensor: "Sentinel-2", "Landsat-8", "SAR", "Sentinel-1"
- Change Intent: is_change_query (True/False)
- Cleaned Semantic Prompt: Distilled prompt for RemoteCLIP vector retrieval.
"""

import re
import calendar
from datetime import datetime
from typing import Optional, Dict, List, Any

# Gazetteers: Bounding boxes for key Earth Observation monitoring regions [minx, miny, maxx, maxy]
REGION_GAZETTEER = {
    "assam": [89.70, 24.10, 96.00, 28.00],
    "guwahati": [91.60, 26.05, 91.90, 26.30],
    "brahmaputra": [90.00, 25.80, 95.50, 27.80],
    "kaziranga": [93.10, 26.55, 93.85, 26.75],
    "mumbai": [72.75, 18.85, 73.05, 19.30],
    "delhi": [76.80, 28.40, 77.40, 28.90],
    "delhi ncr": [76.70, 28.20, 77.60, 29.00],
    "kerala": [74.85, 8.28, 77.40, 12.80],
    "wayanad": [75.90, 11.50, 76.40, 11.95],
    "sundarbans": [88.00, 21.50, 89.90, 22.50],
    "ladakh": [75.50, 32.00, 79.50, 36.00],
    "thar desert": [69.50, 24.50, 76.00, 30.00],
    "rajasthan": [69.50, 23.00, 78.20, 30.20],
    "bengaluru": [77.45, 12.80, 77.80, 13.15],
    "bangalore": [77.45, 12.80, 77.80, 13.15],
    "chennai": [80.10, 12.85, 80.35, 13.25],
    "kolkata": [88.20, 22.40, 88.50, 22.70],
    "hyderabad": [78.30, 17.25, 78.65, 17.55],
    "odisha": [81.30, 17.80, 87.50, 22.60],
    "uttarakhand": [77.60, 28.70, 81.10, 31.50],
}

# Months lookup for date range parsing
MONTH_MAP = {
    "january": 1, "jan": 1,
    "february": 2, "feb": 2,
    "march": 3, "mar": 3,
    "april": 4, "apr": 4,
    "may": 5,
    "june": 6, "jun": 6,
    "july": 7, "jul": 7,
    "august": 8, "aug": 8,
    "september": 9, "sept": 9, "sep": 9,
    "october": 10, "oct": 10,
    "november": 11, "nov": 11,
    "december": 12, "dec": 12,
}

# Change & disaster indicators
CHANGE_INDICATORS = [
    "change", "changed", "difference", "different", "before and after", "evolution",
    "flood", "flooding", "submerged", "inundation", "damage", "destroyed",
    "deforestation", "clearing", "tree loss", "burned", "wildfire", "fire scar",
    "urban growth", "construction", "expansion", "built up", "shrinking", "rebuilt",
    "drought", "dried up", "coastal erosion", "landslide"
]

INTENT_PATTERNS = {
    "PROVENANCE": {
        "keywords": ["source", "provenance", "trace", "origin", "where did", "came from", "processing lineage", "audit"],
        "patterns": [r"where\s+did\s+this", r"source\s+of", r"how\s+was\s+this", r"provenance\s+of"],
        "weight": 1.0,
    },
    "CHANGE_ANALYSIS": {
        "keywords": CHANGE_INDICATORS,
        "patterns": [
            r"what\s+(has\s+)?changed", r"any\s+changes?", r"detect\s+change",
            r"before\s+and\s+after", r"how\s+has\s+.+\s+changed", r"damage\s+in",
            r"flood\s+(in|around)", r"expansion\s+in"
        ],
        "weight": 0.9,
    },
    "IMAGE_SIMILARITY": {
        "keywords": ["similar", "like this", "looks like", "resembles", "matching", "find more", "more like", "same kind"],
        "patterns": [r"similar\s+(to|locations?|sites?|areas?|images?)", r"find\s+(more\s+)?like", r"looks?\s+like\s+this"],
        "weight": 0.85,
    },
    "VQA": {
        "keywords": ["what is", "describe", "identify", "visible", "recognize", "land use", "land cover", "what features"],
        "patterns": [r"what\s+is\s+(visible|shown|this|in\s+this)", r"describe\s+(this|the)", r"what\s+can\s+you\s+see", r"identify\s+the"],
        "weight": 0.8,
    },
    "SEMANTIC_SEARCH": {
        "keywords": ["find", "search", "show", "locate", "where", "look for", "discover", "airport", "port", "solar farm", "river", "forest", "buildings"],
        "patterns": [r"find\s+.+", r"search\s+for", r"show\s+me", r"where\s+(are|is|can)", r"locate\s+"],
        "weight": 0.7,
    },
}


def parse_and_route_query(text: str, tile_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Parse a natural language EO search query into intent, structured filters, and a clean target prompt.
    """
    text_clean = text.strip()
    text_lower = text_clean.lower()
    
    # 1. Intent Classification
    scores = {}
    for intent, config in INTENT_PATTERNS.items():
        score = 0.0
        for keyword in config["keywords"]:
            if keyword in text_lower:
                score += config["weight"] * 0.5
        for pattern in config["patterns"]:
            if re.search(pattern, text_lower):
                score += config["weight"] * 0.7
                break
        scores[intent] = score

    if tile_id:
        for intent in ["CHANGE_ANALYSIS", "IMAGE_SIMILARITY", "VQA"]:
            scores[intent] = scores.get(intent, 0) * 1.3

    best_intent = max(scores, key=scores.get) if scores else "SEMANTIC_SEARCH"
    if scores.get(best_intent, 0) < 0.1:
        best_intent = "SEMANTIC_SEARCH"

    # 2. Extract Structured Parameters
    extracted = _extract_all_parameters(text_clean)
    
    # Check change intent
    is_change_query = (best_intent == "CHANGE_ANALYSIS") or any(k in text_lower for k in CHANGE_INDICATORS)
    
    # Distill prompt for vector retrieval
    clean_prompt = _distill_semantic_prompt(text_clean, extracted)

    return {
        "intent": best_intent,
        "is_change_query": is_change_query,
        "original_query": text_clean,
        "cleaned_prompt": clean_prompt,
        "location": extracted.get("location_name"),
        "bbox": extracted.get("bbox"),
        "date_from": extracted.get("date_from"),
        "date_to": extracted.get("date_to"),
        "max_cloud_cover": extracted.get("max_cloud_cover"),
        "sensor": extracted.get("sensor"),
        "parameters": extracted,
    }


def classify_query(text: str, tile_id: Optional[str] = None) -> Dict[str, Any]:
    """Backward compatibility wrapper."""
    res = parse_and_route_query(text, tile_id)
    return {
        "intent": res["intent"],
        "confidence": 0.92,
        "original_text": text,
        "parameters": res["parameters"],
        "is_change_query": res["is_change_query"],
        "cleaned_prompt": res["cleaned_prompt"],
        "bbox": res["bbox"],
        "date_from": res["date_from"],
        "date_to": res["date_to"],
        "sensor": res["sensor"],
    }


def _extract_all_parameters(text: str) -> Dict[str, Any]:
    params = {}
    text_lower = text.lower()
    
    # --- A. Spatial Extraction (Gazetteer + BBox Regex) ---
    for loc_name, bbox in REGION_GAZETTEER.items():
        if re.search(rf"\b{re.escape(loc_name)}\b", text_lower):
            params["location_name"] = loc_name.title()
            params["bbox"] = bbox
            break
            
    # Explicit bounding box regex [minx, miny, maxx, maxy]
    bbox_match = re.search(r"\[\s*(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)\s*\]", text)
    if bbox_match:
        params["bbox"] = [float(bbox_match.group(i)) for i in range(1, 5)]

    # --- B. Temporal Extraction ---
    # 1. "between MonthA and MonthB Year" (e.g., "between July and August 2024")
    m_range = re.search(r"(?:between|from)\s+([a-zA-Z]+)\s+(?:and|to)\s+([a-zA-Z]+)(?:\s+(\d{4}))?", text_lower)
    if m_range:
        m1_str, m2_str, year_str = m_range.group(1), m_range.group(2), m_range.group(3)
        year = int(year_str) if year_str else 2024
        if m1_str in MONTH_MAP and m2_str in MONTH_MAP:
            m1 = MONTH_MAP[m1_str]
            m2 = MONTH_MAP[m2_str]
            last_day = calendar.monthrange(year, m2)[1]
            params["date_from"] = f"{year:04d}-{m1:02d}-01"
            params["date_to"] = f"{year:04d}-{m2:02d}-{last_day:02d}"

    # 2. "in Month Year" (e.g., "in January 2026")
    if "date_from" not in params:
        m_single = re.search(r"\b(?:in|during)\s+([a-zA-Z]+)\s+(\d{4})\b", text_lower)
        if m_single:
            m_str, year_str = m_single.group(1), m_single.group(2)
            if m_str in MONTH_MAP:
                m = MONTH_MAP[m_str]
                y = int(year_str)
                last_day = calendar.monthrange(y, m)[1]
                params["date_from"] = f"{y:04d}-{m:02d}-01"
                params["date_to"] = f"{y:04d}-{m:02d}-{last_day:02d}"

    # 3. ISO date range (YYYY-MM-DD to YYYY-MM-DD)
    iso_dates = re.findall(r"\b(\d{4}-\d{2}-\d{2})\b", text)
    if len(iso_dates) >= 2:
        params["date_from"] = iso_dates[0]
        params["date_to"] = iso_dates[1]
    elif len(iso_dates) == 1:
        if "after" in text_lower or "since" in text_lower:
            params["date_from"] = iso_dates[0]
        else:
            params["date_to"] = iso_dates[0]

    # --- C. Cloud Cover Extraction ---
    cloud_match = re.search(r"cloud(?:\s*cover)?\s*(?:<|<=|less\s+than|under|below)\s*(\d+)\s*%", text_lower)
    if cloud_match:
        params["max_cloud_cover"] = float(cloud_match.group(1))

    # --- D. Sensor Extraction ---
    if "sentinel-2" in text_lower or "sentinel 2" in text_lower:
        params["sensor"] = "Sentinel-2"
    elif "landsat" in text_lower:
        params["sensor"] = "Landsat-8"
    elif "sar" in text_lower or "sentinel-1" in text_lower:
        params["sensor"] = "Sentinel-1"

    return params


def _distill_semantic_prompt(text: str, extracted: Dict[str, Any]) -> str:
    """
    Remove filter and clause noise to form an optimal target description for RemoteCLIP text embedding.
    """
    p = text
    # Remove metadata clauses
    p = re.sub(r"(?:between|from)\s+[a-zA-Z]+\s+(?:and|to)\s+[a-zA-Z]+(?:\s+\d{4})?", "", p, flags=re.IGNORECASE)
    p = re.sub(r"\b(?:in|during)\s+[a-zA-Z]+\s+\d{4}\b", "", p, flags=re.IGNORECASE)
    p = re.sub(r"\b\d{4}-\d{2}-\d{2}\b", "", p)
    p = re.sub(r"\bwith\s+cloud(?:\s*cover)?\s*(?:<|<=|less\s+than|under|below)\s*\d+\s*%?", "", p, flags=re.IGNORECASE)
    p = re.sub(r"\[\s*-?\d+\.?\d*\s*,\s*-?\d+\.?\d*\s*,\s*-?\d+\.?\d*\s*,\s*-?\d+\.?\d*\s*\]", "", p)
    
    # Remove named locations if matched
    if "location_name" in extracted:
        p = re.sub(rf"\b(?:in|around|near|across)\s+{re.escape(extracted['location_name'])}\b", "", p, flags=re.IGNORECASE)
        p = re.sub(rf"\b{re.escape(extracted['location_name'])}\b", "", p, flags=re.IGNORECASE)

    # Remove generic search command prefixes
    p = re.sub(r"^(?:show\s+me|show|find|search\s+for|locate|look\s+for|detect)\s+", "", p, flags=re.IGNORECASE)
    
    # Cleanup extra whitespace and punctuation
    p = re.sub(r"\s+", " ", p).strip(" ,.-")
    
    # If cleaned prompt is too short, return original
    if len(p) < 4:
        return text
    return p
