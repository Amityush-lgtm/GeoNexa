"""
Test benchmark queries across all Earth Observation categories.
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.retrieval.search import semantic_search

queries = [
    "photovoltaic solar panel arrays in desert",
    "flood damage in Assam",
    "mumbai port container terminal docks",
    "airport runway",
    "dense forest green canopy",
    "urban city buildings",
    "mangrove delta tidal river",
    "Show flood damage in Assam between July and August 2024 with cloud cover < 15%",
]

print("==========================================================================================")
print(" GeoNexa — Real Remote Sensing Query Evaluation Benchmark ")
print("==========================================================================================")

for q in queries:
    res = semantic_search(q, top_k=1)
    if res["results"]:
        top = res["results"][0]
        prompt = res.get("effective_prompt", q)
        print(f"Query:   '{q}'")
        print(f"Prompt:  '{prompt}' | Intent: {res.get('parsed_intent')}")
        print(f"Result:  {top['tile_id']} (Match: {top['match_percentage']}%, Raw: {top['raw_similarity']})")
        print("-" * 90)
    else:
        print(f"Query:   '{q}' -> [NO MATCHES]")
        print("-" * 90)

print("\nAll benchmark tests executed successfully!")
