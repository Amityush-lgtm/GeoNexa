"""
Evaluation Script: Retrieval Quality and Latency Benchmark.

Runs a suite of standardized test queries against the semantic search engine,
measures latency metrics (mean, p50, p95), result rankings, and outputs
a detailed evaluation report JSON to `reports/retrieval_evaluation_<date>.json`.
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any

# Ensure backend app is importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.db import init_db, get_db
from app.retrieval.search import search as run_search
from app.models.schemas import SearchRequest


BENCHMARK_QUERIES = [
    {
        "query": "river with water body and surrounding green vegetation",
        "expected_features": ["river", "water", "vegetation"],
        "description": "Semantic query targeting natural water features",
    },
    {
        "query": "new industrial construction and newly built structures",
        "expected_features": ["buildings", "structures", "construction"],
        "description": "Semantic query targeting infrastructure expansion",
    },
    {
        "query": "dense forest canopy and dark green trees",
        "expected_features": ["forest", "trees", "vegetation"],
        "description": "Semantic query targeting forest cover",
    },
    {
        "query": "agricultural farm fields and crops",
        "expected_features": ["crops", "agriculture", "fields"],
        "description": "Semantic query targeting agricultural patterns",
    },
    {
        "query": "asphalt road crossing through rural landscape",
        "expected_features": ["road", "transportation"],
        "description": "Semantic query targeting linear infrastructure",
    },
    {
        "query": "port docks and coastal area",
        "expected_features": ["port", "coast", "water"],
        "description": "Semantic query targeting port / coastal infrastructure",
    },
]


async def run_retrieval_benchmark() -> Dict[str, Any]:
    print("================================================================")
    print("Semantic EO Search — Retrieval Evaluation & Benchmark")
    print("================================================================")

    await init_db()

    # Check total indexed tiles in DB
    db = await get_db()
    cursor = await db.execute("SELECT COUNT(*) FROM tiles")
    row = await cursor.fetchone()
    total_tiles = row[0] if row else 0

    cursor = await db.execute("SELECT COUNT(*) FROM embeddings")
    row = await cursor.fetchone()
    total_embeddings = row[0] if row else 0

    print(f"Archive status: {total_tiles} tiles, {total_embeddings} vector embeddings.")

    if total_embeddings == 0:
        print("\nWARNING: No embeddings found in database. Ingest scenes first with:")
        print("python -m app.archive.ingestion or via /api/archive/ingest")

    results = []
    latencies = []

    for item in BENCHMARK_QUERIES:
        query_text = item["query"]
        print(f"\nQuery: '{query_text}'")

        req = SearchRequest(
            query=query_text,
            top_k=10,
        )

        t0 = time.perf_counter()
        search_res = await run_search(req)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        latencies.append(elapsed_ms)

        top_results = []
        for r in search_res.results[:3]:
            top_results.append({
                "tile_id": r.tile_id,
                "similarity": round(r.similarity, 4),
                "location": {"lat": r.location.lat, "lon": r.location.lon},
                "acquisition_date": r.date,
            })
            print(f"  -> Match: {r.tile_id} (Score: {r.similarity:.4f}, Date: {r.date})")

        results.append({
            "query": query_text,
            "description": item["description"],
            "latency_ms": round(elapsed_ms, 2),
            "total_matches": search_res.total,
            "top_3": top_results,
        })

    # Summary statistics
    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    p50_latency = sorted(latencies)[len(latencies) // 2] if latencies else 0
    p95_latency = sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_indexed_tiles": total_tiles,
        "total_embeddings": total_embeddings,
        "queries_tested": len(BENCHMARK_QUERIES),
        "latency_metrics_ms": {
            "mean": round(avg_latency, 2),
            "p50": round(p50_latency, 2),
            "p95": round(p95_latency, 2),
            "min": round(min(latencies), 2) if latencies else 0,
            "max": round(max(latencies), 2) if latencies else 0,
        },
        "query_results": results,
    }

    # Save report
    reports_dir = PROJECT_ROOT / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_file = reports_dir / f"retrieval_evaluation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print("\n================================================================")
    print(f"Evaluation Complete! Mean Latency: {avg_latency:.2f} ms | P95: {p95_latency:.2f} ms")
    print(f"Report written to: {report_file}")
    print("================================================================")

    return report


if __name__ == "__main__":
    asyncio.run(run_retrieval_benchmark())
