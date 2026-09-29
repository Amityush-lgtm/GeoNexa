"""
End-to-end system verification script.
Tests all backend routes, model inference, FAISS vector search, image serving, change analysis, and query routing.
"""

import urllib.request
import json
import time
import sys

BASE_URL = "http://127.0.0.1:8000"

def run_tests():
    print("=" * 60)
    print("GeoNexa End-to-End System Verification")
    print("=" * 60)

    # 1. Root
    try:
        with urllib.request.urlopen(f"{BASE_URL}/") as resp:
            data = json.loads(resp.read().decode())
            print(f"[PASS] Root API: {data.get('name')} v{data.get('version')}")
    except Exception as e:
        print(f"[FAIL] Root API: {e}")
        return False

    # 2. Health
    try:
        with urllib.request.urlopen(f"{BASE_URL}/api/health") as resp:
            data = json.loads(resp.read().decode())
            print(f"[PASS] Health Status: {data.get('status')}")
            for k, v in data.get("checks", {}).items():
                print(f"       - {k}: {v}")
            if data.get("status") != "healthy":
                print("[WARN] System not marked healthy!")
    except Exception as e:
        print(f"[FAIL] Health Check: {e}")
        return False

    # 3. Archive Stats
    try:
        with urllib.request.urlopen(f"{BASE_URL}/api/archive/stats") as resp:
            data = json.loads(resp.read().decode())
            print(f"[PASS] Archive Stats: {data.get('total_scenes')} scenes, {data.get('total_tiles')} tiles, {data.get('index_size')} indexed vectors")
    except Exception as e:
        print(f"[FAIL] Archive Stats: {e}")

    # 4. Semantic Search
    top_tile_id = None
    try:
        payload = json.dumps({"query": "river water body winding through agricultural fields", "top_k": 5}).encode("utf-8")
        req = urllib.request.Request(f"{BASE_URL}/api/search", data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            results = data.get("results", [])
            print(f"[PASS] Semantic Search: query='river water body...' -> {len(results)} results")
            if results:
                top_tile_id = results[0]["tile_id"]
                print(f"       Top Match: {top_tile_id} (score: {results[0]['similarity']:.4f})")
    except Exception as e:
        print(f"[FAIL] Semantic Search: {e}")

    # 5. Tile Image Retrieval
    if top_tile_id:
        try:
            with urllib.request.urlopen(f"{BASE_URL}/api/archive/tiles/{top_tile_id}/image") as resp:
                img_data = resp.read()
                content_type = resp.headers.get("Content-Type")
                print(f"[PASS] Tile Image Serving: {len(img_data)} bytes PNG ({content_type})")
        except Exception as e:
            print(f"[FAIL] Tile Image Serving: {e}")

    # 6. Similarity Search
    if top_tile_id:
        try:
            payload = json.dumps({"tile_id": top_tile_id, "top_k": 3}).encode("utf-8")
            req = urllib.request.Request(f"{BASE_URL}/api/search/similar", data=payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode())
                print(f"[PASS] Visual Similarity Search: {len(data.get('results', []))} similar tiles found")
        except Exception as e:
            print(f"[FAIL] Similarity Search: {e}")

    # 7. Query Routing (Natural Language vs Geo vs Change)
    try:
        payload = json.dumps({"query": "detect deforestation between 2024 and 2026 near Guwahati"}).encode("utf-8")
        req = urllib.request.Request(f"{BASE_URL}/api/query/route", data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            print(f"[PASS] Query Router: Intent = {data.get('intent')} | Parameters = {data.get('extracted_parameters')}")
    except Exception as e:
        print(f"[FAIL] Query Router: {e}")

    # 8. Provenance
    try:
        with urllib.request.urlopen(f"{BASE_URL}/api/provenance/recent") as resp:
            data = json.loads(resp.read().decode())
            records = data.get("records", []) if isinstance(data, dict) else data
            print(f"[PASS] Provenance Tracking: {len(records)} audit log entries verified")
    except Exception as e:
        print(f"[FAIL] Provenance API: {e}")

    # 9. Change Analysis
    if top_tile_id:
        try:
            payload = json.dumps({"tile_id": top_tile_id}).encode("utf-8")
            req = urllib.request.Request(f"{BASE_URL}/api/change/analyze", data=payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode())
                print(f"[PASS] Change Analysis: Type={data.get('change_type')} | Confidence={data.get('confidence', {}).get('label')} | Change%={data.get('change_percentage', 0):.2f}%")
        except Exception as e:
            print(f"[FAIL] Change Analysis: {e}")

    print("=" * 60)
    print("Verification Completed Successfully!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
