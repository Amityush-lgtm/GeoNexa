"""
GeoNexa — Semantic Retrieval Quality & Relevance Benchmark.

Loads the development evaluation ground-truth from data/evaluation/retrieval_relevance.csv,
runs queries through semantic_search, computes information retrieval metrics
(Recall@1, Recall@5, Recall@10, Precision@5, MRR), records latency metrics (mean, p50, p95),
and generates a benchmark report.

Usage:
    python scripts/evaluate_retrieval.py
"""

import csv
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any

import numpy as np

# Add backend directory to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.config import get_settings
from app.db import init_db, get_connection, get_db_path
from app.retrieval.search import semantic_search

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("geonexa.eval_retrieval")


def load_relevance_dataset(csv_path: Path) -> Dict[str, Dict[str, Any]]:
    """Load query ground truth labels."""
    queries = {}
    if not csv_path.exists():
        logger.error(f"Relevance dataset not found at {csv_path}")
        return queries

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            qid = row["query_id"]
            if qid not in queries:
                queries[qid] = {
                    "query_id": qid,
                    "query": row["query"],
                    "relevant_tiles": set(),
                    "non_relevant_tiles": set(),
                }
            if row["relevant"] == "1":
                queries[qid]["relevant_tiles"].add(row["tile_id"])
            else:
                queries[qid]["non_relevant_tiles"].add(row["tile_id"])

    return queries


def evaluate_retrieval(model_path: str = None, index_path: str = None):
    settings = get_settings()
    db_path = get_db_path()
    init_db(db_path)

    relevance_file = PROJECT_ROOT / "data" / "evaluation" / "retrieval_relevance.csv"
    gt_queries = load_relevance_dataset(relevance_file)

    if not gt_queries:
        logger.warning("No ground-truth queries found. Please check data/evaluation/retrieval_relevance.csv")
        return

    logger.info(f"Loaded {len(gt_queries)} benchmark queries for evaluation.")

    # Custom model and index if provided
    custom_model = None
    custom_store = None
    if model_path:
        from app.embeddings.clip_model import RemoteCLIPEmbeddingModel
        logger.info(f"Using evaluated model: {model_path}")
        custom_model = RemoteCLIPEmbeddingModel(model_path=model_path, device=settings.device)
    if index_path:
        from app.retrieval.vector_store import VectorStore
        logger.info(f"Using evaluated vector index: {index_path}")
        custom_store = VectorStore(index_path=index_path)

    recall_at_1 = []
    recall_at_5 = []
    recall_at_10 = []
    precision_at_5 = []
    mrr_list = []
    latencies = []
    query_eval_results = []

    for qid, qdata in gt_queries.items():
        query_text = qdata["query"]
        relevant_set = qdata["relevant_tiles"]

        t0 = time.perf_counter()
        res = semantic_search(
            query=query_text,
            top_k=20,
            model=custom_model,
            store=custom_store,
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        latencies.append(elapsed_ms)

        retrieved_tile_ids = [r["tile_id"] for r in res.get("results", [])]

        if not relevant_set:
            continue

        # Recall@K
        r1_hits = set(retrieved_tile_ids[:1]).intersection(relevant_set)
        r5_hits = set(retrieved_tile_ids[:5]).intersection(relevant_set)
        r10_hits = set(retrieved_tile_ids[:10]).intersection(relevant_set)

        r_at_1 = len(r1_hits) / min(1, len(relevant_set)) if relevant_set else 0.0
        r_at_5 = len(r5_hits) / min(5, len(relevant_set)) if relevant_set else 0.0
        r_at_10 = len(r10_hits) / min(10, len(relevant_set)) if relevant_set else 0.0

        p_at_5 = len(r5_hits) / 5.0 if retrieved_tile_ids else 0.0

        # Reciprocal Rank
        first_rank = 0
        for rank_idx, tid in enumerate(retrieved_tile_ids, start=1):
            if tid in relevant_set:
                first_rank = rank_idx
                break
        rr = 1.0 / first_rank if first_rank > 0 else 0.0

        recall_at_1.append(r_at_1)
        recall_at_5.append(r_at_5)
        recall_at_10.append(r_at_10)
        precision_at_5.append(p_at_5)
        mrr_list.append(rr)

        query_eval_results.append({
            "query_id": qid,
            "query": query_text,
            "latency_ms": round(elapsed_ms, 2),
            "total_retrieved": len(retrieved_tile_ids),
            "relevant_count": len(relevant_set),
            "recall@1": round(r_at_1, 4),
            "recall@5": round(r_at_5, 4),
            "recall@10": round(r_at_10, 4),
            "precision@5": round(p_at_5, 4),
            "reciprocal_rank": round(rr, 4),
            "top_3_retrieved": retrieved_tile_ids[:3],
        })

    # Summary Metrics
    mean_lat = float(np.mean(latencies)) if latencies else 0.0
    p50_lat = float(np.percentile(latencies, 50)) if latencies else 0.0
    p95_lat = float(np.percentile(latencies, 95)) if latencies else 0.0

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "evaluation_dataset": "data/evaluation/retrieval_relevance.csv",
        "embedding_model": settings.embedding_model,
        "queries_evaluated": len(gt_queries),
        "metrics": {
            "mean_recall@1": round(float(np.mean(recall_at_1)), 4) if recall_at_1 else 0.0,
            "mean_recall@5": round(float(np.mean(recall_at_5)), 4) if recall_at_5 else 0.0,
            "mean_recall@10": round(float(np.mean(recall_at_10)), 4) if recall_at_10 else 0.0,
            "mean_precision@5": round(float(np.mean(precision_at_5)), 4) if precision_at_5 else 0.0,
            "mrr": round(float(np.mean(mrr_list)), 4) if mrr_list else 0.0,
        },
        "latency_metrics_ms": {
            "mean": round(mean_lat, 2),
            "p50": round(p50_lat, 2),
            "p95": round(p95_lat, 2),
        },
        "per_query_results": query_eval_results,
    }

    reports_dir = PROJECT_ROOT / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_file = reports_dir / f"retrieval_evaluation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    logger.info("================================================================")
    logger.info(f"Retrieval Benchmark Complete!")
    logger.info(f"  Recall@5:     {report['metrics']['mean_recall@5']:.4f}")
    logger.info(f"  Precision@5:  {report['metrics']['mean_precision@5']:.4f}")
    logger.info(f"  MRR:          {report['metrics']['mrr']:.4f}")
    logger.info(f"  Mean Latency: {mean_lat:.2f} ms | P95: {p95_lat:.2f} ms")
    logger.info(f"Report written to: {report_file}")
    logger.info("================================================================")

    return report


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="GeoNexa Retrieval Evaluation Benchmark")
    parser.add_argument("--model-path", type=str, default=None, help="Custom model checkpoint path (.pt)")
    parser.add_argument("--index-path", type=str, default=None, help="Custom FAISS index file path")
    args = parser.parse_args()

    evaluate_retrieval(model_path=args.model_path, index_path=args.index_path)
