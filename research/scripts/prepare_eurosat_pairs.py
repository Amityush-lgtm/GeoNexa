"""
Prepare Contrastive Remote Sensing Training Pairs from Real Sentinel-2 EuroSAT Dataset.

Generates rich, descriptive remote sensing image-caption pairs for fine-tuning RemoteCLIP
across all 10 real optical satellite land-cover categories.
"""

import os
import json
import random
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EUROSAT_DIR = PROJECT_ROOT / "data" / "eurosat" / "eurosat" / "2750"
OUTPUT_DIR = PROJECT_ROOT / "training_data"

CLASS_CAPTIONS = {
    "AnnualCrop": [
        "satellite view of agricultural crop fields with distinct parcel boundaries",
        "overhead optical imagery of cultivated farmland and agricultural plots",
        "remote sensing view of green cropland with irrigation and farm boundaries",
        "aerial view of rectangular agricultural fields and planted crops",
        "patchwork of fertile farm fields and agricultural land from orbit",
    ],
    "Forest": [
        "dense forest canopy and continuous green woodland from satellite",
        "remote sensing view of deep green coniferous and deciduous forest",
        "overhead view of natural forest reserve and dense tree cover",
        "satellite capture of undisturbed woodland and forested hills",
        "aerial imagery showing dense canopy of temperate forest vegetation",
    ],
    "HerbaceousVegetation": [
        "open grassland meadow and natural herbaceous vegetation",
        "satellite imagery of rural grazing prairie and wild grasslands",
        "remote sensing view of open field with low herbaceous cover",
        "overhead view of natural savannah and wild grassland landscape",
    ],
    "Highway": [
        "asphalt highway and multi-lane transportation corridor through landscape",
        "satellite imagery showing paved road network and highway interchange",
        "overhead view of primary highway and rural road intersection",
        "remote sensing image of transportation infrastructure and roadway",
    ],
    "Industrial": [
        "industrial manufacturing park with large warehouse buildings and storage",
        "satellite view of commercial logistics facility and industrial roofs",
        "overhead optical view of industrial complex with metal roofs and loading bays",
        "remote sensing capture of factory infrastructure and commercial buildings",
    ],
    "Pasture": [
        "green pasture land and agricultural grazing fields from orbit",
        "satellite imagery of rural livestock pasture and open grassland",
        "overhead view of agricultural pasture and grass fields",
        "remote sensing photo of open rural pasture and farm paddock",
    ],
    "PermanentCrop": [
        "permanent orchards and vineyard agricultural plantation rows",
        "satellite view of geometric fruit tree orchard and permanent crops",
        "remote sensing image of structured crop plantation and agricultural rows",
        "overhead view of permanent agricultural groves and vineyard rows",
    ],
    "Residential": [
        "residential neighborhood with houses, suburban streets, and rooftops",
        "satellite imagery of suburban housing development and urban settlement",
        "overhead view of residential buildings, private yards, and access roads",
        "remote sensing view of dense residential living zone and street grid",
    ],
    "River": [
        "meandering river channel cutting through rural landscape and floodplain",
        "satellite view of winding freshwater river and surrounding riparian banks",
        "remote sensing imagery of natural river watercourse with sandbars",
        "overhead view of braided river channel with water sediment flow",
    ],
    "SeaLake": [
        "open coastal sea water with sediment runoff and deep blue water",
        "satellite imagery of freshwater lake with coastal shoreline",
        "remote sensing view of calm marine coastal waters and turquoise sediment plumes",
        "overhead view of natural lake water body and shoreline transition",
    ],
}


def build_training_manifests(samples_per_class: int = 400, val_ratio: float = 0.15):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    random.seed(42)

    all_pairs = []
    
    for class_name, captions in CLASS_CAPTIONS.items():
        class_folder = EUROSAT_DIR / class_name
        if not class_folder.exists():
            print(f"Warning: Class folder {class_folder} not found.")
            continue
            
        images = list(class_folder.glob("*.jpg"))
        random.shuffle(images)
        selected = images[:samples_per_class]
        
        for img_path in selected:
            # Pair each image with multiple diverse captions
            for caption in captions:
                pair = {
                    "image_path": str(img_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                    "caption": caption,
                    "tile_id": f"{class_name}_{img_path.stem}",
                    "scene_id": "EuroSAT",
                    "label": 1,
                    "class_name": class_name,
                    "source": "EuroSAT_Sentinel2",
                }
                all_pairs.append(pair)
                
    random.shuffle(all_pairs)
    
    val_count = int(len(all_pairs) * val_ratio)
    val_pairs = all_pairs[:val_count]
    train_pairs = all_pairs[val_count:]
    
    print(f"Total pairs generated: {len(all_pairs)}")
    print(f"  Training pairs:   {len(train_pairs)}")
    print(f"  Validation pairs: {len(val_pairs)}")
    
    with open(OUTPUT_DIR / "train_pairs.json", "w", encoding="utf-8") as f:
        json.dump({"pairs": train_pairs}, f, indent=2)
        
    with open(OUTPUT_DIR / "val_pairs.json", "w", encoding="utf-8") as f:
        json.dump({"pairs": val_pairs}, f, indent=2)
        
    print(f"Saved manifests to {OUTPUT_DIR}/train_pairs.json and {OUTPUT_DIR}/val_pairs.json")


if __name__ == "__main__":
    build_training_manifests(samples_per_class=600)
