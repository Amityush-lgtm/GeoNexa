"""
GeoNexa — Comprehensive All-Domain Query Dataset & Contrastive Training Generator.

Builds an exhaustive corpus of domain-specific Earth Observation queries,
synonyms, multi-spectral conditions, and contrastive training pairs spanning:
- Agriculture & Cropland (Rice, Wheat, Corn, Irrigation Pivots, Orchards, Vineyards, Pasture)
- Urban Infrastructure & Settlements (High-Density Downtown, Residential, Suburbs, Slums)
- Industrial & Logistics (Warehouses, Factories, Chemical Tanks, Distribution Centers)
- Transportation & Aviation (Highways, Runways, Tarmacs, Bridges, Railway Yards)
- Forestry & Vegetation (Tropical Rainforest, Closed Canopies, Woodland Hills, Deforestation)
- Mangroves & Coastal Wetlands (Saline Tidal Creeks, Estuaries, Salt Marshes)
- Hydrology & Freshwater (Braided Rivers, Sediment Plumes, Lakes, Reservoirs, Canals)
- Clean Energy & Arid (Photovoltaic Solar Parks, Wind Turbines, Arid Substrates)
- Maritime & Ports (Deepwater Cargo Docks, Container Terminals, Vessels at Sea)
- Bi-Temporal Change & Hazards (Flooding Inundation, Urban Sprawl, Drought, Burn Scars)
"""

import json
import random
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "training_data"

COMPREHENSIVE_QUERY_TAXONOMY = {
    "agriculture": [
        "agricultural fields with visible crop parcel boundaries",
        "cultivated farmland and green agricultural plots from satellite",
        "geometric crop fields with irrigation channels",
        "overhead view of rice paddy fields and standing water",
        "patchwork of fertile agricultural crops and farm parcels",
        "orchards and vineyard plantation rows viewed from orbit",
        "rural pasture land and livestock grazing fields",
        "terrace farming on hillsides with green vegetation",
        "harvested farmland with bare soil and field boundaries",
        "pivot irrigation agricultural circles in rural landscape",
        "fertile cropland parcels with high chlorophyll reflectance",
        "vegetable crop farming and agricultural greenhouse structures",
        "rural agricultural landscape with farm roads and drainage ditches",
        "monoculture crop fields during peak growing season",
        "agricultural plots transition from vegetative growth to harvest"
    ],
    "urban_residential": [
        "dense urban residential neighborhood with houses and streets",
        "suburban housing development with private rooftops and gardens",
        "high-density residential settlement and narrow alleyways",
        "city residential block with apartment buildings and parking",
        "overhead optical view of urban sprawl and suburban expansion",
        "planned residential community with cul-de-sacs and asphalt roads",
        "residential rooftops with varying color tiles and building clusters",
        "multi-story residential apartments in metropolitan area",
        "satellite view of urban dwelling zones and neighborhood street grid",
        "mixed urban residential and neighborhood commercial shops"
    ],
    "urban_commercial": [
        "city center with high-rise skyscrapers and commercial towers",
        "downtown commercial district with dense concrete buildings",
        "metropolitan skyline and commercial office complexes",
        "urban core with multi-story buildings and street intersections",
        "central business district with high impervious surface coverage",
        "commercial plaza and urban retail buildings from orbit",
        "dense downtown street grid and concrete infrastructure"
    ],
    "industrial_logistics": [
        "industrial manufacturing park with large warehouse buildings",
        "logistics distribution center with loading docks and trucks",
        "factory complex with metal roofs and industrial machinery",
        "chemical storage facility with round oil tanks and pipelines",
        "commercial freight warehouse park near transport corridors",
        "heavy industrial zone with manufacturing plants and smokestacks",
        "storage yards and logistics shipping containers near railway",
        "industrial processing facility with concrete yards and warehouses"
    ],
    "transportation_aviation": [
        "airport runways, taxiways, and airplane tarmac from satellite",
        "asphalt highway interchange and multi-lane transportation corridor",
        "bridge crossing wide river carrying roadway and rail traffic",
        "railway junction and freight train classification yard",
        "paved arterial road cutting through mixed urban landscape",
        "multi-level highway flyover and traffic interchange",
        "commercial aviation airport with terminal buildings and runways",
        "highway toll plaza and multi-lane asphalt expressway"
    ],
    "forestry_canopy": [
        "dense tropical forest canopy with continuous tree cover",
        "natural woodland reserve and deep green temperate forest",
        "coniferous forest on mountainous terrain from space",
        "dense tree foliage and intact ecological forest reserve",
        "continuous woodland canopy on hills with high chlorophyll response",
        "deciduous forest in full summer foliage viewed from orbit",
        "lush tropical rainforest with dense multi-layered tree canopy",
        "protected ecological forest buffer along river valley"
    ],
    "mangroves_wetlands": [
        "coastal mangrove wetland ecosystem with dense tidal creeks",
        "saline tidal marsh and braided mangrove forest channels",
        "estuary wetland with mangrove vegetation and mudflats",
        "coastal swamp forest intersecting with shallow marine waters",
        "tidal delta with mangrove buffer and sediment-rich water",
        "protected mangrove conservation reserve along coastline"
    ],
    "hydrology_rivers": [
        "meandering river channel cutting through valley and floodplain",
        "braided river system with sandbars and sediment flow",
        "freshwater river meeting natural lake with riparian banks",
        "river delta with branching watercourses and sediment plumes",
        "flooded river overflow basin during high water season",
        "deep blue freshwater lake surrounded by natural vegetation",
        "artificial water reservoir behind hydroelectric dam",
        "inland canal watercourse with regulated water flow"
    ],
    "maritime_ports": [
        "deepwater marine port with cargo vessel berthing piers",
        "shipping terminal with container cranes and moored cargo ships",
        "coastal harbor with breakwaters, docks, and maritime traffic",
        "ocean vessel shipping lane approaching coastal port terminal",
        "marine shipyard with dry docks and vessel berths",
        "coastal port facilities with container storage and logistics"
    ],
    "solar_energy": [
        "high-density photovoltaic solar panel arrays in desert",
        "utility-scale solar park with aligned blue photovoltaic panels",
        "solar energy power station over arid ground substrate",
        "grid-aligned solar photovoltaic modules in desert solar park",
        "large-scale renewable solar farm with transformer stations"
    ],
    "change_disaster": [
        "severe river flood inundation over surrounding agricultural plains",
        "urban encroachment and new construction over former cropland",
        "wildfire burn scar on forested hillside and charred ground",
        "deforested land clearing showing bare earth and logging tracks",
        "coastal shoreline erosion and changing beach sediment line",
        "drought-affected reservoir with receding water level and dry bed"
    ]
}


def generate_all_domain_manifests():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    random.seed(42)

    # 1. Inspect local tiles
    tiles_dir = PROJECT_ROOT / "data" / "public" / "tiles"
    tile_files = list(tiles_dir.rglob("*.png")) + list(tiles_dir.rglob("*.jpg")) + list(tiles_dir.rglob("*.tif"))
    logger.info(f"Found {len(tile_files)} local tile images in {tiles_dir}")

    all_pairs = []

    # Map scene keywords to taxonomy categories
    scene_category_map = {
        "AGRICULTURE": ["agriculture"],
        "URBAN": ["urban_residential", "urban_commercial", "transportation_aviation"],
        "INDUSTRIAL": ["industrial_logistics"],
        "FOREST": ["forestry_canopy"],
        "MANGROVE": ["mangroves_wetlands", "forestry_canopy"],
        "BRAHMAPUTRA": ["hydrology_rivers", "change_disaster"],
        "BHADLA": ["solar_energy"],
        "MUMBAI": ["maritime_ports", "transportation_aviation", "urban_commercial"],
        "GUWAHATI": ["urban_residential", "agriculture", "hydrology_rivers"],
        "COASTAL": ["maritime_ports", "mangroves_wetlands", "agriculture"],
        "WATERSHED": ["forestry_canopy", "hydrology_rivers"],
    }

    for tf in tile_files:
        stem = tf.stem
        # Determine matching categories
        matched_cats = []
        for kw, cats in scene_category_map.items():
            if kw in stem:
                matched_cats.extend(cats)

        if not matched_cats:
            matched_cats = ["agriculture", "urban_residential", "hydrology_rivers"]

        matched_cats = list(set(matched_cats))

        # Generate contrastive positive pairs
        for cat in matched_cats:
            query_templates = COMPREHENSIVE_QUERY_TAXONOMY.get(cat, [])
            for q_text in query_templates:
                pair = {
                    "image_path": str(tf.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                    "caption": q_text,
                    "tile_id": stem,
                    "scene_id": stem.split("_tile_")[0] if "_tile_" in stem else stem,
                    "domain_category": cat,
                    "label": 1
                }
                all_pairs.append(pair)

    random.shuffle(all_pairs)
    val_count = max(100, int(len(all_pairs) * 0.15))
    val_pairs = all_pairs[:val_count]
    train_pairs = all_pairs[val_count:]

    logger.info(f"Generated {len(all_pairs)} total domain training pairs across {len(COMPREHENSIVE_QUERY_TAXONOMY)} categories:")
    logger.info(f"  Training pairs:   {len(train_pairs)}")
    logger.info(f"  Validation pairs: {len(val_pairs)}")

    with open(OUTPUT_DIR / "train_pairs.json", "w", encoding="utf-8") as f:
        json.dump({"pairs": train_pairs}, f, indent=2)

    with open(OUTPUT_DIR / "val_pairs.json", "w", encoding="utf-8") as f:
        json.dump({"pairs": val_pairs}, f, indent=2)

    with open(OUTPUT_DIR / "query_taxonomy.json", "w", encoding="utf-8") as f:
        json.dump(COMPREHENSIVE_QUERY_TAXONOMY, f, indent=2)

    logger.info("Saved manifests to training_data/train_pairs.json & val_pairs.json")


if __name__ == "__main__":
    generate_all_domain_manifests()
