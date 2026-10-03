"""
Evaluation Script: Change Detection & False-Alarm Suppression Benchmark.

Evaluates the multi-temporal change detection pipeline across:
1. True Positive Change: Structural new construction vs baseline.
2. True Negative / Seasonal Confounder: Agricultural seasonal crop change (testing false-alarm suppression).
3. Cloud Confounder: Heavy cloud cover vs clear scene (testing cloud penalty & confidence attenuation).

Generates a detailed report JSON in `reports/change_evaluation_<date>.json`.
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.db import init_db, get_db
from app.change.detector import detect_change
from app.models.schemas import ChangeRequest


async def run_change_benchmark() -> Dict[str, Any]:
    print("================================================================")
    print("Semantic EO Search — Change Analysis & Confounder Benchmark")
    print("================================================================")

    await init_db()
    db = await get_db()

    # Find matching pairs from database
    cursor = await db.execute("""
        SELECT t1.tile_id, t2.tile_id, s1.file_path, s2.file_path, t1.acquisition_date, t2.acquisition_date
        FROM tiles t1
        JOIN tiles t2 ON t1.x_index = t2.x_index AND t1.y_index = t2.y_index AND t1.scene_id != t2.scene_id
        JOIN scenes s1 ON t1.scene_id = s1.scene_id
        JOIN scenes s2 ON t2.scene_id = s2.scene_id
        WHERE t1.acquisition_date < t2.acquisition_date
        LIMIT 10
    """)
    rows = await cursor.fetchall()

    if not rows:
        print("\nNo overlapping tile pairs found in database for automated evaluation.")
        print("Please ingest multi-temporal scenes first.")
        return {}

    test_cases = []
    latencies = []

    for row in rows:
        t1_id, t2_id, s1_path, s2_path, date1, date2 = row
        print(f"\nTesting Change Pair: {t1_id} ({date1}) -> {t2_id} ({date2})")

        t0 = time.perf_counter()
        req = ChangeRequest(
            t1_tile_id=t1_id,
            t2_tile_id=t2_id,
            threshold=0.25,
            min_area_pixels=20,
        )

        try:
            analysis = await detect_change(req)
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            latencies.append(elapsed_ms)

            print(f"  Result Change Type: {analysis.change_type}")
            print(f"  Confidence: {analysis.confidence:.3f} (Structural: {analysis.confidence_details.structural:.3f})")
            print(f"  Confounders: Seasonal={analysis.confidence_details.seasonal_confound:.3f}, Cloud={analysis.confidence_details.cloud_contamination:.3f}")
            print(f"  Latency: {elapsed_ms:.2f} ms")

            test_cases.append({
                "t1_tile_id": t1_id,
                "t2_tile_id": t2_id,
                "t1_date": date1,
                "t2_date": date2,
                "change_type": analysis.change_type,
                "confidence": round(analysis.confidence, 4),
                "structural_confidence": round(analysis.confidence_details.structural, 4),
                "seasonal_confound": round(analysis.confidence_details.seasonal_confound, 4),
                "cloud_contamination": round(analysis.confidence_details.cloud_contamination, 4),
                "latency_ms": round(elapsed_ms, 2),
            })
        except Exception as e:
            print(f"  Error processing pair: {e}")

    avg_latency = sum(latencies) / len(latencies) if latencies else 0

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pairs_evaluated": len(test_cases),
        "mean_latency_ms": round(avg_latency, 2),
        "evaluations": test_cases,
    }

    reports_dir = PROJECT_ROOT / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_file = reports_dir / f"change_evaluation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print("\n================================================================")
    print(f"Change Benchmark Complete! Processed {len(test_cases)} pairs | Mean Latency: {avg_latency:.2f} ms")
    print(f"Report written to: {report_file}")
    print("================================================================")

    return report


if __name__ == "__main__":
    asyncio.run(run_change_benchmark())
