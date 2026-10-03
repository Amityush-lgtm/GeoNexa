"""
GeoNexa — System Performance Benchmark.

Measures and logs actual runtime environment metrics:
- Hardware, CPU, RAM, GPU availability, Python version
- Dataset statistics (scene count, tile count, storage footprint)
- Model load time, embedding dimensions
- FAISS index size, build time
- Latency percentiles (mean, p50, p95)

Outputs:
    reports/system_benchmark.json
"""

import json
import logging
import os
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

# Add backend directory to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.config import get_settings
from app.db import init_db, get_connection, get_db_path
from app.embeddings.manager import get_embedding_model
from app.retrieval.vector_store import get_vector_store
from app.retrieval.search import semantic_search

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("geonexa.benchmark")


def run_system_benchmark():
    settings = get_settings()
    db_path = get_db_path()
    init_db(db_path)

    logger.info("Running GeoNexa System Benchmark...")

    # 1. Environment & Hardware
    hardware = {
        "platform": platform.platform(),
        "processor": platform.processor() or platform.machine(),
        "python_version": platform.python_version(),
        "cpu_count": os.cpu_count(),
    }

    try:
        import torch
        hardware["torch_version"] = torch.__version__
        hardware["cuda_available"] = torch.cuda.is_available()
        hardware["device"] = "cuda" if torch.cuda.is_available() else "cpu"
        if torch.cuda.is_available():
            hardware["gpu_name"] = torch.cuda.get_device_name(0)
    except ImportError:
        hardware["torch_version"] = "Not Installed"
        hardware["cuda_available"] = False
        hardware["device"] = "cpu"

    # 2. Dataset Metrics
    with get_connection(db_path) as conn:
        sc_cursor = conn.execute("SELECT COUNT(*) FROM scenes")
        scene_count = sc_cursor.fetchone()[0]
        tc_cursor = conn.execute("SELECT COUNT(*) FROM tiles")
        tile_count = tc_cursor.fetchone()[0]

    tiles_dir = Path(settings.tiles_dir)
    total_tile_bytes = sum(f.stat().st_size for f in tiles_dir.glob("**/*") if f.is_file()) if tiles_dir.exists() else 0

    dataset_metrics = {
        "scene_count": scene_count,
        "tile_count": tile_count,
        "tiles_storage_mb": round(total_tile_bytes / (1024 * 1024), 2),
    }

    # 3. Model Benchmark
    t0 = time.perf_counter()
    model = get_embedding_model()
    model_load_ms = (time.perf_counter() - t0) * 1000.0

    model_metrics = {
        "model_name": model.model_name,
        "model_version": model.model_version,
        "embedding_dimension": model.vector_dim,
        "device": model.device,
        "load_time_ms": round(model_load_ms, 2),
    }

    # 4. Vector Store Benchmark
    vector_store = get_vector_store()
    index_file = Path(settings.faiss_index_path)
    index_size_kb = round(index_file.stat().st_size / 1024, 2) if index_file.exists() else 0.0

    index_metrics = {
        "faiss_total_vectors": vector_store.size,
        "vector_dimension": vector_store.dimension,
        "index_file_size_kb": index_size_kb,
    }

    # 5. Search Latency Benchmark
    test_queries = [
        "urban buildings near water",
        "river and surrounding vegetation",
        "agricultural fields",
        "roads through urban areas",
        "dense forest canopy on hills",
    ]

    latencies = []
    for q in test_queries:
        t_start = time.perf_counter()
        _ = semantic_search(query=q, top_k=10)
        lat = (time.perf_counter() - t_start) * 1000.0
        latencies.append(lat)

    search_metrics = {
        "test_queries_count": len(test_queries),
        "mean_latency_ms": round(float(np.mean(latencies)), 2) if latencies else 0.0,
        "p50_latency_ms": round(float(np.percentile(latencies, 50)), 2) if latencies else 0.0,
        "p95_latency_ms": round(float(np.percentile(latencies, 95)), 2) if latencies else 0.0,
    }

    benchmark_report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "hardware": hardware,
        "dataset": dataset_metrics,
        "model": model_metrics,
        "index": index_metrics,
        "search_performance": search_metrics,
    }

    reports_dir = PROJECT_ROOT / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_file = reports_dir / "system_benchmark.json"

    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(benchmark_report, f, indent=2)

    logger.info(f"System benchmark complete! Output saved to: {report_file}")
    return benchmark_report


if __name__ == "__main__":
    run_system_benchmark()
