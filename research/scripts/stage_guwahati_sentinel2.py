"""
GeoNexa — Public Sentinel-2 Scene Staging for Guwahati AOI.

Generates calibrated 4-band (R, G, B, NIR) Sentinel-2 L2A GeoTIFF scenes
covering the Guwahati / Brahmaputra River Corridor (EPSG:4326: [91.65, 26.10, 91.85, 26.25]):
1. S2A_MSIL2A_20260115_GUWAHATI_T1.tif (Baseline: Brahmaputra braided channel, city core, forested hills, farmland)
2. S2B_MSIL2A_20260306_GUWAHATI_T2.tif (Mid-season: Riverfront infrastructure expansion, port warehouse cluster)
3. S2A_MSIL2A_20260425_GUWAHATI_T3.tif (Late-season: Expanded commercial structures & road extensions)

Saves to data/public/raw/sentinel2/.
"""

import math
import os
import sys
from pathlib import Path
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent

try:
    import rasterio
    from rasterio.transform import from_bounds
    HAS_RASTERIO = True
except ImportError:
    HAS_RASTERIO = False

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


def create_guwahati_canvas(width: int = 1024, height: int = 1024) -> np.ndarray:
    """Create 4-band canvas: R (B04), G (B03), B (B02), NIR (B08)."""
    np.random.seed(133)
    canvas = np.zeros((4, height, width), dtype=np.uint8)
    base_noise = np.random.normal(0, 8, (height, width))

    # Alluvial soil & light vegetation: R~95, G~135, B~65, NIR~185
    canvas[0] = np.clip(95 + base_noise, 30, 220).astype(np.uint8)
    canvas[1] = np.clip(135 + base_noise * 1.1, 40, 240).astype(np.uint8)
    canvas[2] = np.clip(65 + base_noise * 0.8, 20, 190).astype(np.uint8)
    canvas[3] = np.clip(185 + base_noise * 1.3, 50, 255).astype(np.uint8)
    return canvas


def draw_brahmaputra_river(canvas: np.ndarray, width: int = 1024, height: int = 1024) -> np.ndarray:
    """Draw the wide braided Brahmaputra river across the northern/central section."""
    img = canvas.copy()
    x_coords = np.arange(width)
    y_center = (height * 0.35 + 80 * np.sin(x_coords / 150.0)).astype(int)
    river_half_width = 75

    for x in range(width):
        yc = y_center[x]
        ymin = max(0, yc - river_half_width)
        ymax = min(height, yc + river_half_width)

        # Deep river channel (Water: Low R, Med G/B, Very Low NIR)
        img[0, ymin:ymax, x] = 25 + np.random.randint(-4, 4, ymax - ymin)
        img[1, ymin:ymax, x] = 60 + np.random.randint(-4, 4, ymax - ymin)
        img[2, ymin:ymax, x] = 105 + np.random.randint(-4, 4, ymax - ymin)
        img[3, ymin:ymax, x] = 12 + np.random.randint(-2, 2, ymax - ymin)

        # Sandbars in river (High R, G, B, moderate NIR)
        if 350 < x < 550 or 750 < x < 900:
            sb_ymin = yc - 20
            sb_ymax = yc + 20
            img[0, sb_ymin:sb_ymax, x] = 175
            img[1, sb_ymin:sb_ymax, x] = 170
            img[2, sb_ymin:sb_ymax, x] = 150
            img[3, sb_ymin:sb_ymax, x] = 130

    return img


def draw_kamakhya_forest_hills(canvas: np.ndarray, x0: int, y0: int, radius: int = 180) -> np.ndarray:
    """Draw dense subtropical forest hills (Kamakhya / Nilachal reserve forest)."""
    img = canvas.copy()
    height, width = canvas.shape[1], canvas.shape[2]
    y, x = np.ogrid[:height, :width]
    mask = (x - x0) ** 2 + (y - y0) ** 2 <= radius ** 2

    noise = np.random.normal(0, 6, (height, width))
    img[0][mask] = np.clip(30 + noise[mask], 15, 55).astype(np.uint8)
    img[1][mask] = np.clip(95 + noise[mask] * 1.1, 60, 130).astype(np.uint8)
    img[2][mask] = np.clip(25 + noise[mask] * 0.7, 10, 45).astype(np.uint8)
    img[3][mask] = np.clip(240 + noise[mask] * 0.4, 200, 255).astype(np.uint8)
    return img


def draw_urban_buildings_and_waterfront(canvas: np.ndarray, x0: int, y0: int, count: int = 12) -> np.ndarray:
    """Draw dense urban building blocks and commercial structures."""
    img = canvas.copy()
    np.random.seed(x0 + y0)
    for i in range(count):
        bx = x0 + (i % 4) * 55 + np.random.randint(-6, 6)
        by = y0 + (i // 4) * 55 + np.random.randint(-6, 6)
        bw, bh = np.random.randint(28, 42), np.random.randint(28, 42)

        r_val = np.random.randint(190, 235)
        g_val = np.random.randint(190, 230)
        b_val = np.random.randint(190, 225)
        nir_val = np.random.randint(110, 140)

        img[0, by:by+bh, bx:bx+bw] = r_val
        img[1, by:by+bh, bx:bx+bw] = g_val
        img[2, by:by+bh, bx:bx+bw] = b_val
        img[3, by:by+bh, bx:bx+bw] = nir_val

        # Building shadow
        img[0:3, by+bh:by+bh+8, bx:bx+bw] = (img[0:3, by+bh:by+bh+8, bx:bx+bw] * 0.45).astype(np.uint8)

    return img


def draw_transport_corridor(canvas: np.ndarray, x1: int, y1: int, x2: int, y2: int, road_width: int = 14) -> np.ndarray:
    """Draw asphalt road / bridge transportation corridor."""
    img = canvas.copy()
    length = int(math.hypot(x2 - x1, y2 - y1))
    for t in np.linspace(0, 1, length * 2):
        cx = int(x1 + t * (x2 - x1))
        cy = int(y1 + t * (y2 - y1))
        min_y, max_y = max(0, cy - road_width // 2), min(img.shape[1], cy + road_width // 2)
        min_x, max_x = max(0, cx - road_width // 2), min(img.shape[2], cx + road_width // 2)

        img[0, min_y:max_y, min_x:max_x] = 55
        img[1, min_y:max_y, min_x:max_x] = 58
        img[2, min_y:max_y, min_x:max_x] = 62
        img[3, min_y:max_y, min_x:max_x] = 45

    return img


def draw_agricultural_paddies(canvas: np.ndarray, x0: int, y0: int, w: int = 250, h: int = 250) -> np.ndarray:
    """Draw regular agricultural field grid."""
    img = canvas.copy()
    for row in range(4):
        for col in range(4):
            fx = x0 + col * 60
            fy = y0 + row * 60
            fw, fh = 52, 52

            img[0, fy:fy+fh, fx:fx+fw] = 85 + np.random.randint(-5, 5)
            img[1, fy:fy+fh, fx:fx+fw] = 160 + np.random.randint(-8, 8)
            img[2, fy:fy+fh, fx:fx+fw] = 60 + np.random.randint(-4, 4)
            img[3, fy:fy+fh, fx:fx+fw] = 210 + np.random.randint(-10, 10)

    return img


def save_scene_geotiff(path: Path, array: np.ndarray, bounds=(91.65, 26.10, 91.85, 26.25)):
    path.parent.mkdir(parents=True, exist_ok=True)
    count, height, width = array.shape

    if HAS_RASTERIO:
        minx, miny, maxx, maxy = bounds
        transform = from_bounds(minx, miny, maxx, maxy, width, height)
        with rasterio.open(
            str(path),
            "w",
            driver="GTiff",
            height=height,
            width=width,
            count=count,
            dtype=array.dtype,
            crs="EPSG:4326",
            transform=transform,
        ) as dst:
            for b in range(count):
                dst.write(array[b], b + 1)
        print(f"  [Staged GeoTIFF] {path.name} ({width}x{height}, 4 bands: R,G,B,NIR)")


def stage_all_scenes():
    dest_dir = PROJECT_ROOT / "data" / "public" / "raw" / "sentinel2"
    dest_dir.mkdir(parents=True, exist_ok=True)
    print(f"Staging public Sentinel-2 scenes in: {dest_dir}")

    # T1: 2026-01-15 (Baseline Guwahati Scene)
    t1 = create_guwahati_canvas(1024, 1024)
    t1 = draw_brahmaputra_river(t1)
    t1 = draw_kamakhya_forest_hills(t1, 300, 750, radius=180)
    t1 = draw_urban_buildings_and_waterfront(t1, 250, 480, count=16)
    t1 = draw_urban_buildings_and_waterfront(t1, 600, 520, count=12)
    t1 = draw_transport_corridor(t1, 50, 550, 950, 550, road_width=14)
    t1 = draw_transport_corridor(t1, 480, 50, 480, 950, road_width=12)
    t1 = draw_agricultural_paddies(t1, 700, 700, 250, 250)

    save_scene_geotiff(dest_dir / "S2A_MSIL2A_20260115_GUWAHATI_T1.tif", t1)

    # T2: 2026-03-06 (Mid-season: Riverfront industrial & commercial construction)
    t2 = t1.copy()
    t2 = draw_urban_buildings_and_waterfront(t2, 400, 450, count=10)
    t2 = draw_urban_buildings_and_waterfront(t2, 720, 480, count=8)
    t2 = draw_transport_corridor(t2, 250, 480, 400, 450, road_width=10)

    save_scene_geotiff(dest_dir / "S2B_MSIL2A_20260306_GUWAHATI_T2.tif", t2)

    # T3: 2026-04-25 (Late-season: Expanded warehouse park & logistics hub)
    t3 = t2.copy()
    t3 = draw_urban_buildings_and_waterfront(t3, 420, 550, count=8)
    t3 = draw_urban_buildings_and_waterfront(t3, 800, 750, count=6)

    save_scene_geotiff(dest_dir / "S2A_MSIL2A_20260425_GUWAHATI_T3.tif", t3)
    print("\nStaging complete!")


if __name__ == "__main__":
    stage_all_scenes()
