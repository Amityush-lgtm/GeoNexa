"""
GeoNexa — Automatic Caption Generator for Satellite Tiles.

Generates rich, descriptive captions for satellite image tiles by analyzing
spectral properties (NDVI, NDWI, brightness, texture). These captions are
used as text targets during contrastive fine-tuning of RemoteCLIP.

Approach:
  1. Compute spectral indices (NDVI, NDWI, BSI) from RGB+NIR bands
  2. Classify dominant land cover per tile using index thresholds
  3. Generate multiple caption variants per tile for training diversity
"""

import logging
import random
from pathlib import Path
from typing import List, Dict, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


# ── Land Cover Classification Thresholds ──────────────────────────────────

LAND_COVER_CLASSES = {
    "dense_vegetation": {"ndvi_min": 0.45, "ndvi_max": 1.0},
    "sparse_vegetation": {"ndvi_min": 0.20, "ndvi_max": 0.45},
    "water": {"ndwi_min": 0.10},
    "built_up": {"ndvi_max": 0.15, "brightness_min": 0.35},
    "bare_soil": {"ndvi_max": 0.15, "brightness_max": 0.35},
    "agricultural": {"ndvi_min": 0.25, "ndvi_max": 0.55, "texture_low": True},
}

# ── Caption Templates ────────────────────────────────────────────────────

CAPTION_TEMPLATES = {
    "dense_vegetation": [
        "dense green vegetation and forest canopy covering the landscape",
        "thick tree cover with high vegetation density in a forested area",
        "lush green forest with continuous canopy visible from satellite",
        "dense tropical or subtropical forest with dark green foliage",
        "heavily vegetated terrain showing mature tree growth",
        "satellite view of dense forest cover with high NDVI values",
    ],
    "sparse_vegetation": [
        "sparse vegetation with patches of greenery and exposed ground",
        "scattered trees and shrubs across semi-arid terrain",
        "grassland with moderate vegetation density",
        "open woodland with sparse tree coverage",
        "mixed terrain with scattered vegetation patches",
        "transitional zone between vegetated and barren land",
    ],
    "water": [
        "water body visible as a dark blue region in the satellite image",
        "river flowing through the landscape with surrounding riverbanks",
        "lake or reservoir with calm water surface reflecting low near-infrared",
        "aquatic feature surrounded by riparian vegetation",
        "waterway or canal cutting through the terrain",
        "large water body with distinctive dark spectral signature",
    ],
    "built_up": [
        "urban area with buildings and concrete infrastructure visible",
        "dense urban settlement with closely packed structures",
        "developed area showing roads buildings and impervious surfaces",
        "city or town center with high density of built-up structures",
        "residential neighborhood with rows of houses and street patterns",
        "industrial or commercial zone with large roof surfaces",
        "urban infrastructure including roads and parking areas",
    ],
    "bare_soil": [
        "bare soil or exposed earth with no vegetation cover",
        "dry barren land with exposed ground surface",
        "cleared or fallow land without active vegetation",
        "arid terrain with minimal ground cover",
        "excavated or construction site showing bare earth",
        "desert-like conditions with sandy or rocky surface",
    ],
    "agricultural": [
        "agricultural fields with organized crop patterns",
        "farmland showing regular planting rows visible from above",
        "cultivated area with active crop growth",
        "irrigated agricultural plots with green vegetation",
        "crop fields showing different stages of growth",
        "agricultural landscape with field boundaries and farm roads",
    ],
    "mixed": [
        "mixed land use area combining urban and natural features",
        "transitional landscape with both vegetation and built structures",
        "suburban area with buildings interspersed with green spaces",
        "peri-urban zone showing rural to urban transition",
    ],
    "cloud_or_haze": [
        "satellite image partially obscured by cloud cover",
        "hazy atmospheric conditions affecting image clarity",
        "cloud shadows visible across the terrain below",
    ],
}

# ── Spatial Context Templates ────────────────────────────────────────────

SPATIAL_MODIFIERS = {
    "near_water": [
        "located near a water body",
        "adjacent to a river or stream",
        "situated along the waterfront",
    ],
    "near_urban": [
        "on the outskirts of an urban area",
        "near built-up infrastructure",
        "close to residential development",
    ],
    "near_vegetation": [
        "bordered by dense vegetation",
        "with forested areas nearby",
        "surrounded by green cover",
    ],
}

# ── Temporal / Seasonal Templates ────────────────────────────────────────

SEASON_DESCRIPTIONS = {
    "winter": "during the dry winter season with lower vegetation activity",
    "pre_monsoon": "in the pre-monsoon season showing early green growth",
    "monsoon": "during the monsoon season with peak vegetation and water levels",
    "post_monsoon": "in the post-monsoon period with receding water and drying crops",
}


def compute_spectral_indices(image: np.ndarray) -> Dict[str, float]:
    """
    Compute spectral indices from a satellite tile image.

    Args:
        image: RGB or RGBN numpy array of shape (H, W, 3) or (H, W, 4).
               Values expected in [0, 255] uint8 range.

    Returns:
        Dictionary of spectral index values (mean over the tile).
    """
    img = image.astype(np.float32) / 255.0

    red = img[:, :, 0]
    green = img[:, :, 1]
    blue = img[:, :, 2]

    # Synthetic NIR estimation from RGB if 4th band not available
    if img.shape[2] >= 4:
        nir = img[:, :, 3]
    else:
        # Approximate NIR from vegetation reflectance model
        nir = np.clip(0.5 * green + 0.3 * red - 0.2 * blue + 0.2, 0, 1)

    # Normalized Difference Vegetation Index
    denom_ndvi = nir + red + 1e-8
    ndvi = (nir - red) / denom_ndvi

    # Normalized Difference Water Index
    denom_ndwi = green + nir + 1e-8
    ndwi = (green - nir) / denom_ndwi

    # Bare Soil Index
    denom_bsi = (blue + nir) - (red + green) + 1e-8
    numer_bsi = (red + blue) - (green + nir)
    bsi = numer_bsi / (np.abs(denom_bsi) + 1e-8)

    # Brightness (mean reflectance)
    brightness = (red + green + blue) / 3.0

    # Texture: standard deviation of brightness in local patches
    from scipy.ndimage import uniform_filter
    try:
        mean_sq = uniform_filter(brightness ** 2, size=16)
        sq_mean = uniform_filter(brightness, size=16) ** 2
        texture = np.sqrt(np.maximum(mean_sq - sq_mean, 0))
    except Exception:
        texture = np.std(brightness) * np.ones_like(brightness)

    # Non-zero mask (ignore pure black pixels from padding)
    valid_mask = brightness > 0.02
    if valid_mask.sum() == 0:
        valid_mask = np.ones_like(brightness, dtype=bool)

    indices = {
        "ndvi_mean": float(np.mean(ndvi[valid_mask])),
        "ndvi_std": float(np.std(ndvi[valid_mask])),
        "ndvi_max": float(np.percentile(ndvi[valid_mask], 95)),
        "ndwi_mean": float(np.mean(ndwi[valid_mask])),
        "bsi_mean": float(np.mean(bsi[valid_mask])),
        "brightness_mean": float(np.mean(brightness[valid_mask])),
        "brightness_std": float(np.std(brightness[valid_mask])),
        "texture_mean": float(np.mean(texture[valid_mask])),
        "red_mean": float(np.mean(red[valid_mask])),
        "green_mean": float(np.mean(green[valid_mask])),
        "blue_mean": float(np.mean(blue[valid_mask])),
        "valid_pixel_ratio": float(valid_mask.sum() / valid_mask.size),
    }
    return indices


def classify_land_cover(indices: Dict[str, float]) -> List[Tuple[str, float]]:
    """
    Classify the dominant land cover type(s) from spectral indices.

    Returns list of (class_name, confidence) tuples, sorted by confidence.
    """
    scores = {}

    ndvi = indices["ndvi_mean"]
    ndwi = indices["ndwi_mean"]
    brightness = indices["brightness_mean"]
    texture = indices["texture_mean"]

    # Dense vegetation
    if ndvi > 0.45:
        scores["dense_vegetation"] = min(1.0, (ndvi - 0.45) / 0.3 + 0.5)
    elif ndvi > 0.20:
        scores["sparse_vegetation"] = min(1.0, (ndvi - 0.20) / 0.25 + 0.3)

    # Water
    if ndwi > 0.10:
        scores["water"] = min(1.0, (ndwi - 0.10) / 0.3 + 0.5)
    elif ndwi > -0.05 and brightness < 0.20:
        scores["water"] = 0.4

    # Built-up
    if ndvi < 0.15 and brightness > 0.35:
        scores["built_up"] = min(1.0, brightness * 1.2)
    elif ndvi < 0.20 and brightness > 0.30 and texture > 0.08:
        scores["built_up"] = 0.5

    # Bare soil
    if ndvi < 0.15 and brightness < 0.35 and brightness > 0.10:
        scores["bare_soil"] = 0.6

    # Agricultural
    if 0.25 < ndvi < 0.55 and texture < 0.10:
        scores["agricultural"] = min(1.0, 0.5 + (0.55 - abs(ndvi - 0.40)) / 0.3)

    # Cloud/haze detection
    if brightness > 0.75 and indices["brightness_std"] < 0.05:
        scores["cloud_or_haze"] = 0.8

    if not scores:
        scores["mixed"] = 0.5

    sorted_scores = sorted(scores.items(), key=lambda x: -x[1])
    return sorted_scores


def generate_captions(
    image: np.ndarray,
    tile_id: str = "",
    season: Optional[str] = None,
    num_captions: int = 5,
    seed: Optional[int] = None,
) -> List[str]:
    """
    Generate diverse text captions for a satellite tile image.

    Args:
        image: RGB(N) image array (H, W, 3 or 4).
        tile_id: Optional tile identifier for provenance.
        season: Optional season hint (winter, pre_monsoon, monsoon, post_monsoon).
        num_captions: Number of caption variants to generate.
        seed: Random seed for reproducibility.

    Returns:
        List of caption strings describing the tile content.
    """
    if seed is not None:
        random.seed(seed)

    # Compute spectral properties
    indices = compute_spectral_indices(image)
    land_covers = classify_land_cover(indices)

    captions = []
    primary_class = land_covers[0][0]
    secondary_class = land_covers[1][0] if len(land_covers) > 1 else None

    # Primary captions from dominant class
    primary_templates = CAPTION_TEMPLATES.get(primary_class, CAPTION_TEMPLATES["mixed"])
    for template in random.sample(primary_templates, min(num_captions, len(primary_templates))):
        caption = f"a satellite image showing {template}"

        # Add seasonal modifier
        if season and season in SEASON_DESCRIPTIONS:
            if random.random() > 0.5:
                caption += f" {SEASON_DESCRIPTIONS[season]}"

        captions.append(caption)

    # Mixed captions combining primary + secondary
    if secondary_class and secondary_class != primary_class:
        sec_templates = CAPTION_TEMPLATES.get(secondary_class, [])
        if sec_templates:
            sec_desc = random.choice(sec_templates)
            mixed_caption = (
                f"a satellite image showing {random.choice(primary_templates)} "
                f"with {sec_desc}"
            )
            captions.append(mixed_caption)

    # Spectral-aware captions
    spectral_desc = _spectral_description(indices)
    if spectral_desc:
        captions.append(f"a satellite image of {spectral_desc}")

    # Trim to requested count
    random.shuffle(captions)
    return captions[:num_captions]


def generate_hard_negative_captions(
    image: np.ndarray,
    num_negatives: int = 3,
) -> List[str]:
    """
    Generate hard negative captions — descriptions that are plausible
    but do NOT match this tile's content.
    """
    indices = compute_spectral_indices(image)
    land_covers = classify_land_cover(indices)
    present_classes = {lc[0] for lc in land_covers}

    absent_classes = set(CAPTION_TEMPLATES.keys()) - present_classes - {"mixed", "cloud_or_haze"}

    negatives = []
    for cls in random.sample(list(absent_classes), min(num_negatives, len(absent_classes))):
        templates = CAPTION_TEMPLATES[cls]
        neg = f"a satellite image showing {random.choice(templates)}"
        negatives.append(neg)

    return negatives[:num_negatives]


def _spectral_description(indices: Dict[str, float]) -> str:
    """Generate a description based on spectral index values."""
    parts = []

    ndvi = indices["ndvi_mean"]
    if ndvi > 0.5:
        parts.append("high vegetation density")
    elif ndvi > 0.3:
        parts.append("moderate vegetation cover")
    elif ndvi > 0.15:
        parts.append("sparse vegetation")
    else:
        parts.append("minimal vegetation")

    ndwi = indices["ndwi_mean"]
    if ndwi > 0.15:
        parts.append("significant water presence")
    elif ndwi > 0.0:
        parts.append("traces of moisture or water")

    brightness = indices["brightness_mean"]
    if brightness > 0.6:
        parts.append("high reflectance from bright surfaces")
    elif brightness < 0.15:
        parts.append("dark surface features")

    return "terrain with " + " and ".join(parts) if parts else ""


def generate_training_pairs_from_tiles(
    tiles_dir: Path,
    output_json: Path,
    captions_per_tile: int = 5,
    season_map: Optional[Dict[str, str]] = None,
) -> int:
    """
    Scan a tiles directory, generate captions, and write image-text pairs to JSON.

    Args:
        tiles_dir: Path to directory containing tile subdirectories.
        output_json: Path to write the output JSON file.
        captions_per_tile: Number of captions per tile.
        season_map: Optional mapping of scene_id -> season.

    Returns:
        Number of training pairs generated.
    """
    import json

    pairs = []
    tile_files = sorted(tiles_dir.rglob("*.tif"))

    if not tile_files:
        logger.warning(f"No .tif files found in {tiles_dir}")
        return 0

    logger.info(f"Generating captions for {len(tile_files)} tiles...")

    for i, tile_path in enumerate(tile_files):
        try:
            image = _load_tile_for_captioning(tile_path)
            if image is None:
                continue

            tile_id = tile_path.stem
            scene_id = tile_path.parent.name
            season = season_map.get(scene_id) if season_map else None

            # Generate positive captions
            captions = generate_captions(
                image, tile_id=tile_id, season=season,
                num_captions=captions_per_tile, seed=i,
            )

            # Generate hard negatives
            neg_captions = generate_hard_negative_captions(image, num_negatives=3)

            # Compute indices for metadata
            indices = compute_spectral_indices(image)
            land_covers = classify_land_cover(indices)

            for caption in captions:
                pairs.append({
                    "image_path": str(tile_path),
                    "caption": caption,
                    "tile_id": tile_id,
                    "scene_id": scene_id,
                    "label": 1,  # positive pair
                    "land_cover": land_covers[0][0],
                    "ndvi": round(indices["ndvi_mean"], 3),
                })

            for neg in neg_captions:
                pairs.append({
                    "image_path": str(tile_path),
                    "caption": neg,
                    "tile_id": tile_id,
                    "scene_id": scene_id,
                    "label": 0,  # negative pair
                    "land_cover": land_covers[0][0],
                    "ndvi": round(indices["ndvi_mean"], 3),
                })

            if (i + 1) % 10 == 0:
                logger.info(f"  Processed {i+1}/{len(tile_files)} tiles...")

        except Exception as e:
            logger.warning(f"Failed to process {tile_path}: {e}")
            continue

    # Write to JSON
    output_json.parent.mkdir(parents=True, exist_ok=True)
    with open(output_json, "w") as f:
        json.dump({
            "metadata": {
                "total_pairs": len(pairs),
                "positive_pairs": sum(1 for p in pairs if p["label"] == 1),
                "negative_pairs": sum(1 for p in pairs if p["label"] == 0),
                "tiles_processed": len(tile_files),
                "captions_per_tile": captions_per_tile,
            },
            "pairs": pairs,
        }, f, indent=2)

    logger.info(f"Generated {len(pairs)} training pairs → {output_json}")
    return len(pairs)


def _load_tile_for_captioning(tile_path: Path) -> Optional[np.ndarray]:
    """Load a GeoTIFF tile as an RGB numpy array for captioning."""
    try:
        import rasterio
        with rasterio.open(str(tile_path)) as ds:
            bands = min(ds.count, 3)
            data = ds.read(list(range(1, bands + 1)))

            if bands == 1:
                data = np.repeat(data, 3, axis=0)
            elif bands == 2:
                data = np.concatenate([data, np.zeros_like(data[:1])], axis=0)

            image = np.transpose(data, (1, 2, 0))  # CHW → HWC

            if image.dtype != np.uint8:
                valid = image[image > 0]
                if len(valid) > 0:
                    vmin = np.percentile(valid, 2)
                    vmax = np.percentile(valid, 98)
                else:
                    vmin, vmax = 0, 1
                if vmax > vmin:
                    image = np.clip((image - vmin) / (vmax - vmin) * 255, 0, 255).astype(np.uint8)
                else:
                    image = np.zeros_like(image, dtype=np.uint8)

            return image
    except Exception as e:
        logger.warning(f"Could not load {tile_path}: {e}")
        return None
