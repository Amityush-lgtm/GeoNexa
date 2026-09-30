"""
GeoNexa — Prepare Training Data.

Generates image-text training pairs from the existing tile archive
by analyzing spectral properties and creating diverse captions.

Usage:
    python scripts/prepare_training_data.py
    python scripts/prepare_training_data.py --tiles-dir data/public/tiles --output training_data/
"""

import argparse
import json
import logging
import random
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from training.caption_generator import (
    generate_training_pairs_from_tiles,
    compute_spectral_indices,
    classify_land_cover,
    generate_captions,
    generate_hard_negative_captions,
    _load_tile_for_captioning,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


# ── Extended caption templates for richer training data ────────────────────

REMOTE_SENSING_QUERIES = [
    # Urban / Built-up
    "urban area with dense buildings",
    "city center with high-rise structures",
    "residential neighborhood from satellite view",
    "industrial zone with warehouses and factories",
    "roads and highways cutting through urban landscape",
    "construction site with bare earth and equipment",
    "airport runway visible from space",

    # Vegetation
    "dense tropical forest canopy",
    "agricultural cropland with irrigation",
    "rice paddy fields with water",
    "tea plantation on hillside",
    "mangrove forest along coastline",
    "deciduous forest in winter",
    "deforested area showing land clearing",

    # Water
    "river flowing through a valley",
    "lake surrounded by vegetation",
    "coastal waters meeting the shoreline",
    "reservoir behind a dam",
    "wetland with marshy vegetation",
    "flooded area during monsoon season",
    "river delta with sediment deposits",

    # Terrain
    "mountainous terrain with snow",
    "desert landscape with sand dunes",
    "rocky terrain with sparse vegetation",
    "coastal beach with sand and waves",
    "hilly terrain with terraced farming",
    "plateau with grasslands",

    # Change Detection
    "area showing new construction compared to before",
    "urban expansion into agricultural land",
    "flood damage visible from satellite",
    "wildfire burn scar on forested land",
    "seasonal vegetation change between dry and wet season",
    "coastal erosion along the shoreline",
]


def prepare_training_data(
    tiles_dir: Path,
    output_dir: Path,
    captions_per_tile: int = 8,
    val_split: float = 0.15,
    seed: int = 42,
):
    """
    Generate complete training and validation datasets.

    Steps:
      1. Scan all tiles in the archive
      2. Generate spectral-based captions (positive pairs)
      3. Generate hard negatives per tile
      4. Add curated remote sensing query templates
      5. Split into train/val
      6. Save as JSON manifests
    """
    random.seed(seed)
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("═══════════════════════════════════════════════")
    logger.info("  GeoNexa — Training Data Preparation")
    logger.info(f"  Tiles directory: {tiles_dir}")
    logger.info(f"  Output directory: {output_dir}")
    logger.info(f"  Captions per tile: {captions_per_tile}")
    logger.info(f"  Validation split: {val_split:.0%}")
    logger.info("═══════════════════════════════════════════════")

    # ── Phase 1: Auto-generate caption pairs from tiles ──
    logger.info("\n[Phase 1] Generating auto-captions from spectral analysis...")

    # Season mapping for Guwahati scenes
    season_map = {
        "SENT_20260115_S2A_MSIL2A_20260115_GUWAHATI_T1": "winter",
        "SENT_20260306_S2B_MSIL2A_20260306_GUWAHATI_T2": "pre_monsoon",
        "SENT_20260425_S2A_MSIL2A_20260425_GUWAHATI_T3": "pre_monsoon",
    }

    all_pairs_path = output_dir / "all_pairs.json"
    n_auto = generate_training_pairs_from_tiles(
        tiles_dir=tiles_dir,
        output_json=all_pairs_path,
        captions_per_tile=captions_per_tile,
        season_map=season_map,
    )

    if n_auto == 0:
        logger.warning("No local GeoTIFF tiles found! Automatically preparing EuroSAT Sentinel-2 pairs...")
        from scripts.prepare_eurosat_pairs import build_training_manifests
        import torchvision.datasets
        euro_dir = PROJECT_ROOT / "data" / "eurosat"
        if not (euro_dir / "eurosat" / "2750").exists():
            logger.info("Downloading EuroSAT Sentinel-2 dataset...")
            torchvision.datasets.EuroSAT(root=str(euro_dir), download=True)
        build_training_manifests(samples_per_class=600)
        return

    with open(all_pairs_path, "r") as f:
        data = json.load(f)
    pairs = data["pairs"]

    # For each tile, assign the most relevant curated queries
    tile_files = sorted(tiles_dir.rglob("*.tif"))
    curated_pairs = []

    for tile_path in tile_files:
        image = _load_tile_for_captioning(tile_path)
        if image is None:
            continue

        indices = compute_spectral_indices(image)
        land_covers = classify_land_cover(indices)
        primary_class = land_covers[0][0]

        # Select relevant curated queries based on land cover
        relevant_queries = _get_relevant_queries(primary_class)

        for query in relevant_queries[:3]:  # Top 3 relevant queries per tile
            curated_pairs.append({
                "image_path": str(tile_path),
                "caption": f"a satellite image showing {query}",
                "tile_id": tile_path.stem,
                "scene_id": tile_path.parent.name,
                "label": 1,
                "land_cover": primary_class,
                "ndvi": round(indices["ndvi_mean"], 3),
                "source": "curated",
            })

    pairs.extend(curated_pairs)
    logger.info(f"  Added {len(curated_pairs)} curated query pairs")

    # ── Phase 3: Train/Val Split ──
    logger.info("\n[Phase 3] Splitting into train/val...")

    # Split by tile_id to avoid data leakage
    tile_ids = list(set(p["tile_id"] for p in pairs))
    random.shuffle(tile_ids)
    n_val = max(1, int(len(tile_ids) * val_split))
    val_tile_ids = set(tile_ids[:n_val])
    train_tile_ids = set(tile_ids[n_val:])

    train_pairs = [p for p in pairs if p["tile_id"] in train_tile_ids]
    val_pairs = [p for p in pairs if p["tile_id"] in val_tile_ids]

    # Save train set
    train_path = output_dir / "train_pairs.json"
    with open(train_path, "w") as f:
        json.dump({
            "metadata": {
                "total_pairs": len(train_pairs),
                "positive_pairs": sum(1 for p in train_pairs if p["label"] == 1),
                "negative_pairs": sum(1 for p in train_pairs if p["label"] == 0),
                "unique_tiles": len(train_tile_ids),
                "split": "train",
            },
            "pairs": train_pairs,
        }, f, indent=2)

    # Save val set
    val_path = output_dir / "val_pairs.json"
    with open(val_path, "w") as f:
        json.dump({
            "metadata": {
                "total_pairs": len(val_pairs),
                "positive_pairs": sum(1 for p in val_pairs if p["label"] == 1),
                "negative_pairs": sum(1 for p in val_pairs if p["label"] == 0),
                "unique_tiles": len(val_tile_ids),
                "split": "val",
            },
            "pairs": val_pairs,
        }, f, indent=2)

    # ── Phase 4: Generate data quality report ──
    logger.info("\n[Phase 4] Generating data quality report...")
    report = _generate_data_report(train_pairs, val_pairs, output_dir)

    logger.info("═══════════════════════════════════════════════")
    logger.info("  Training Data Preparation Complete!")
    logger.info(f"  Train pairs: {len(train_pairs)} ({len(train_tile_ids)} tiles)")
    logger.info(f"  Val pairs:   {len(val_pairs)} ({len(val_tile_ids)} tiles)")
    logger.info(f"  Train JSON:  {train_path}")
    logger.info(f"  Val JSON:    {val_path}")
    logger.info("═══════════════════════════════════════════════")


def _get_relevant_queries(land_cover: str) -> list:
    """Map land cover class to relevant curated queries."""
    mapping = {
        "dense_vegetation": [
            "dense tropical forest canopy",
            "mangrove forest along coastline",
            "deciduous forest in winter",
        ],
        "sparse_vegetation": [
            "grasslands with sparse tree cover",
            "scattered shrubs across semi-arid terrain",
            "savanna with dispersed vegetation",
        ],
        "water": [
            "river flowing through a valley",
            "lake surrounded by vegetation",
            "wetland with marshy vegetation",
        ],
        "built_up": [
            "urban area with dense buildings",
            "residential neighborhood from satellite view",
            "roads and highways cutting through urban landscape",
        ],
        "bare_soil": [
            "construction site with bare earth and equipment",
            "desert landscape with sand dunes",
            "rocky terrain with sparse vegetation",
        ],
        "agricultural": [
            "agricultural cropland with irrigation",
            "rice paddy fields with water",
            "hilly terrain with terraced farming",
        ],
    }
    return mapping.get(land_cover, REMOTE_SENSING_QUERIES[:3])


def _generate_data_report(train_pairs, val_pairs, output_dir):
    """Generate a data quality report."""
    report = {
        "train": {
            "total": len(train_pairs),
            "class_distribution": {},
            "caption_length_stats": {},
        },
        "val": {
            "total": len(val_pairs),
            "class_distribution": {},
        },
    }

    for split_name, split_pairs in [("train", train_pairs), ("val", val_pairs)]:
        class_dist = {}
        caption_lengths = []
        for p in split_pairs:
            lc = p.get("land_cover", "unknown")
            class_dist[lc] = class_dist.get(lc, 0) + 1
            caption_lengths.append(len(p["caption"].split()))

        report[split_name]["class_distribution"] = class_dist
        if caption_lengths:
            report[split_name]["caption_length_stats"] = {
                "mean": round(sum(caption_lengths) / len(caption_lengths), 1),
                "min": min(caption_lengths),
                "max": max(caption_lengths),
            }

    report_path = output_dir / "data_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    # Print class distribution
    logger.info("  Class distribution (train):")
    for cls, count in sorted(report["train"]["class_distribution"].items()):
        logger.info(f"    {cls}: {count}")

    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prepare GeoNexa training data")
    parser.add_argument(
        "--tiles-dir",
        default=str(PROJECT_ROOT / "data" / "public" / "tiles"),
        help="Path to tiles directory",
    )
    parser.add_argument(
        "--output",
        default=str(PROJECT_ROOT / "training_data"),
        help="Output directory for training pairs",
    )
    parser.add_argument("--captions-per-tile", type=int, default=8)
    parser.add_argument("--val-split", type=float, default=0.15)
    parser.add_argument("--seed", type=int, default=42)

    args = parser.parse_args()

    prepare_training_data(
        tiles_dir=Path(args.tiles_dir),
        output_dir=Path(args.output),
        captions_per_tile=args.captions_per_tile,
        val_split=args.val_split,
        seed=args.seed,
    )
