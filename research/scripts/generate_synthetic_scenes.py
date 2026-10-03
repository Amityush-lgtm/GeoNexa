"""
Synthetic GeoTIFF Scene Generator.

Generates realistic multi-temporal satellite imagery pairs for testing and demonstration:
1. Scene Pair A (New Construction): River + rural area -> new buildings and road expansion.
2. Scene Pair B (Seasonal Confounder): Crop greenness change between winter and summer.
3. Scene Pair C (Cloud / Confounder): Port / industrial zone with partial cloud cover.
4. Scene Multi-T (Temporal Sequence): 3-date progression of infrastructure development.

Outputs 4-band (R, G, B, NIR) GeoTIFFs with valid geospatial metadata (WGS84 / EPSG:4326).
"""

import math
import os
from pathlib import Path
import numpy as np

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


def create_base_canvas(width: int = 1024, height: int = 1024) -> np.ndarray:
    """Create a 4-band base canvas (R, G, B, NIR) with realistic natural terrain variation."""
    np.random.seed(42)
    # 4 bands: Red (B1), Green (B2), Blue (B3), NIR (B4)
    canvas = np.zeros((4, height, width), dtype=np.uint8)

    # Base terrain (grassland / light soil)
    # Soil/Grass: R ~ 90-120, G ~ 130-160, B ~ 60-90, NIR ~ 180-220
    base_noise = np.random.normal(0, 10, (height, width))

    canvas[0] = np.clip(100 + base_noise, 40, 220).astype(np.uint8)  # Red
    canvas[1] = np.clip(140 + base_noise * 1.2, 50, 240).astype(np.uint8)  # Green
    canvas[2] = np.clip(70 + base_noise * 0.8, 30, 200).astype(np.uint8)  # Blue
    canvas[3] = np.clip(190 + base_noise * 1.5, 60, 255).astype(np.uint8)  # NIR

    return canvas


def draw_river(canvas: np.ndarray, width: int = 1024, height: int = 1024) -> np.ndarray:
    """Draw a winding river across the scene."""
    img = canvas.copy()
    y_coords = np.arange(height)
    # Sine wave river path
    x_center = (width * 0.35 + 100 * np.sin(y_coords / 120.0)).astype(int)
    river_half_width = 24

    for y in range(height):
        xc = x_center[y]
        x_min = max(0, xc - river_half_width)
        x_max = min(width, xc + river_half_width)

        # Water: low R (20-40), medium B/G (40-80), very low NIR (5-25)
        img[0, y, x_min:x_max] = 30 + np.random.randint(-5, 5, x_max - x_min)
        img[1, y, x_min:x_max] = 65 + np.random.randint(-5, 5, x_max - x_min)
        img[2, y, x_min:x_max] = 95 + np.random.randint(-5, 5, x_max - x_min)
        img[3, y, x_min:x_max] = 15 + np.random.randint(-3, 3, x_max - x_min)

    return img


def draw_forest(canvas: np.ndarray, x0: int, y0: int, r: int) -> np.ndarray:
    """Draw a dense forest patch."""
    img = canvas.copy()
    height, width = canvas.shape[1], canvas.shape[2]
    y, x = np.ogrid[:height, :width]
    mask = (x - x0) ** 2 + (y - y0) ** 2 <= r ** 2

    # Forest: dark green, very high NIR
    noise = np.random.normal(0, 8, (height, width))
    img[0][mask] = np.clip(35 + noise[mask], 15, 60).astype(np.uint8)
    img[1][mask] = np.clip(90 + noise[mask] * 1.1, 60, 130).astype(np.uint8)
    img[2][mask] = np.clip(30 + noise[mask] * 0.7, 10, 50).astype(np.uint8)
    img[3][mask] = np.clip(230 + noise[mask] * 0.5, 190, 255).astype(np.uint8)
    return img


def draw_buildings(canvas: np.ndarray, x0: int, y0: int, count: int = 5) -> np.ndarray:
    """Draw a cluster of buildings (concrete roofs, bright reflectance)."""
    img = canvas.copy()
    np.random.seed(y0 + x0)
    for i in range(count):
        bx = x0 + (i % 3) * 60 + np.random.randint(-5, 5)
        by = y0 + (i // 3) * 60 + np.random.randint(-5, 5)
        bw, bh = np.random.randint(30, 45), np.random.randint(30, 45)

        # Concrete / roof: high R, G, B, moderate NIR
        r_val = np.random.randint(180, 230)
        g_val = np.random.randint(180, 225)
        b_val = np.random.randint(180, 220)
        nir_val = np.random.randint(120, 150)

        img[0, by:by+bh, bx:bx+bw] = r_val
        img[1, by:by+bh, bx:bx+bw] = g_val
        img[2, by:by+bh, bx:bx+bw] = b_val
        img[3, by:by+bh, bx:bx+bw] = nir_val

        # Add a subtle shadow
        shadow_h = 10
        img[0:3, by+bh:by+bh+shadow_h, bx:bx+bw] = (img[0:3, by+bh:by+bh+shadow_h, bx:bx+bw] * 0.4).astype(np.uint8)

    return img


def draw_road(canvas: np.ndarray, x1: int, y1: int, x2: int, y2: int, road_width: int = 12) -> np.ndarray:
    """Draw an asphalt road between two points."""
    img = canvas.copy()
    length = int(math.hypot(x2 - x1, y2 - y1))
    for t in np.linspace(0, 1, length * 2):
        cx = int(x1 + t * (x2 - x1))
        cy = int(y1 + t * (y2 - y1))
        min_y, max_y = max(0, cy - road_width // 2), min(img.shape[1], cy + road_width // 2)
        min_x, max_x = max(0, cx - road_width // 2), min(img.shape[2], cx + road_width // 2)

        # Asphalt: dark grey in RGB, low NIR
        img[0, min_y:max_y, min_x:max_x] = 60
        img[1, min_y:max_y, min_x:max_x] = 62
        img[2, min_y:max_y, min_x:max_x] = 65
        img[3, min_y:max_y, min_x:max_x] = 50

    return img


def add_cloud_cover(canvas: np.ndarray, x0: int, y0: int, radius: int = 150) -> np.ndarray:
    """Add a cloud patch with white brightness and shadow."""
    img = canvas.copy()
    height, width = canvas.shape[1], canvas.shape[2]
    y, x = np.ogrid[:height, :width]
    dist = np.sqrt((x - x0) ** 2 + (y - y0) ** 2)

    cloud_alpha = np.clip(1.0 - (dist / radius), 0, 1.0) ** 1.5

    for c in range(4):
        cloud_val = 250 if c < 3 else 230
        img[c] = (img[c] * (1.0 - cloud_alpha) + cloud_val * cloud_alpha).astype(np.uint8)

    # Cloud shadow offset (to the south-east)
    sx, sy = x0 + 40, y0 + 40
    shadow_dist = np.sqrt((x - sx) ** 2 + (y - sy) ** 2)
    shadow_alpha = np.clip(1.0 - (shadow_dist / radius), 0, 1.0) * 0.5
    for c in range(4):
        img[c] = (img[c] * (1.0 - shadow_alpha * (dist > radius * 0.5))).astype(np.uint8)

    return img


def save_geotiff(
    path: Path,
    array: np.ndarray,
    bounds: tuple = (77.10, 28.50, 77.30, 28.70),
    crs: str = "EPSG:4326",
):
    """Save multi-band array as GeoTIFF using rasterio or raw TIFF."""
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
            crs=crs,
            transform=transform,
        ) as dst:
            for b in range(count):
                dst.write(array[b], b + 1)
        print(f"  [GeoTIFF] Saved {path.name} ({width}x{height}, {count} bands, CRS: {crs})")
    elif HAS_PIL:
        # Fallback to saving RGB PNG / TIFF via PIL if rasterio is missing
        rgb = np.transpose(array[:3], (1, 2, 0))
        img = Image.fromarray(rgb)
        img.save(str(path))
        print(f"  [Image fallback] Saved {path.name} via PIL")
    else:
        raise RuntimeError("Neither rasterio nor PIL is available.")


def generate_all_sample_scenes(output_dir: Path):
    """Generate complete suite of synthetic scenes for demo & evaluation."""
    output_dir.mkdir(parents=True, exist_ok=True)
    print("Generating synthetic satellite scenes for SIH26227 test archive...")

    # Bounds for Delhi / Yamuna river mock region (EPSG:4326)
    delhi_bounds = (77.20, 28.55, 77.35, 28.70)

    # -------------------------------------------------------------
    # 1. Progression: Delhi Yamuna River Corridor (3 dates)
    # -------------------------------------------------------------
    # T1: 2026-01-15 (Baseline: River, dense forest, agricultural land, few buildings)
    t1 = create_base_canvas(1024, 1024)
    t1 = draw_river(t1)
    t1 = draw_forest(t1, 650, 300, 160)
    t1 = draw_forest(t1, 750, 700, 140)
    t1 = draw_road(t1, 100, 100, 350, 950, road_width=10)
    t1 = draw_buildings(t1, 150, 250, count=4)

    save_geotiff(
        output_dir / "DELHI_S2_20260115_T1.tif",
        t1,
        bounds=delhi_bounds,
    )

    # T2: 2026-03-20 (Change: New industrial structures constructed near the river bank)
    t2 = t1.copy()
    t2 = draw_road(t2, 350, 500, 700, 500, road_width=14)
    t2 = draw_buildings(t2, 500, 460, count=8)  # New structures near river!

    save_geotiff(
        output_dir / "DELHI_S2_20260320_T2.tif",
        t2,
        bounds=delhi_bounds,
    )

    # T3: 2026-05-10 (Expansion: Further building expansion and warehouse development)
    t3 = t2.copy()
    t3 = draw_buildings(t3, 520, 600, count=6)
    t3 = draw_buildings(t3, 200, 750, count=5)

    save_geotiff(
        output_dir / "DELHI_S2_20260510_T3.tif",
        t3,
        bounds=delhi_bounds,
    )

    # -------------------------------------------------------------
    # 2. Agricultural Seasonal Confounder (Punjab farm region)
    # -------------------------------------------------------------
    punjab_bounds = (75.80, 30.85, 75.95, 31.00)

    # T1: 2026-02-10 (High NDVI - lush winter crops)
    agri_t1 = create_base_canvas(1024, 1024)
    # Boost green and NIR for active crops
    agri_t1[1] = np.clip(agri_t1[1] * 1.35, 0, 255).astype(np.uint8)
    agri_t1[3] = np.clip(agri_t1[3] * 1.25, 0, 255).astype(np.uint8)
    agri_t1 = draw_road(agri_t1, 50, 512, 950, 512, road_width=8)
    agri_t1 = draw_buildings(agri_t1, 480, 480, count=3)

    save_geotiff(
        output_dir / "PUNJAB_S2_20260210_CROPS_LUSH.tif",
        agri_t1,
        bounds=punjab_bounds,
    )

    # T2: 2026-05-25 (Post-harvest fallow / dry soil - seasonal change, NOT structural change)
    agri_t2 = agri_t1.copy()
    # Brown / dry soil: High Red, low Green, low NIR
    agri_t2[0] = np.clip(agri_t2[0] * 1.4, 0, 255).astype(np.uint8)
    agri_t2[1] = np.clip(agri_t2[1] * 0.7, 0, 255).astype(np.uint8)
    agri_t2[3] = np.clip(agri_t2[3] * 0.55, 0, 255).astype(np.uint8)
    # Buildings and road remain EXACTLY identical
    agri_t2 = draw_road(agri_t2, 50, 512, 950, 512, road_width=8)
    agri_t2 = draw_buildings(agri_t2, 480, 480, count=3)

    save_geotiff(
        output_dir / "PUNJAB_S2_20260525_CROPS_DRY.tif",
        agri_t2,
        bounds=punjab_bounds,
    )

    # -------------------------------------------------------------
    # 3. Coastal Port & Cloud Confounder (Mumbai port region)
    # -------------------------------------------------------------
    mumbai_bounds = (72.80, 18.90, 72.95, 19.05)

    port_t1 = create_base_canvas(1024, 1024)
    # Water on western half
    port_t1[:, :, :512] = 0
    port_t1[0, :, :512] = 25
    port_t1[1, :, :512] = 60
    port_t1[2, :, :512] = 110
    port_t1[3, :, :512] = 10
    # Port docks and cargo
    port_t1 = draw_buildings(port_t1, 560, 200, count=12)
    port_t1 = draw_buildings(port_t1, 560, 500, count=10)
    port_t1 = draw_road(port_t1, 530, 50, 530, 950, road_width=16)

    save_geotiff(
        output_dir / "MUMBAI_S2_20260120_PORT_CLEAR.tif",
        port_t1,
        bounds=mumbai_bounds,
    )

    # T2: Same port scene with cloud contamination
    port_t2 = port_t1.copy()
    port_t2 = add_cloud_cover(port_t2, 600, 350, radius=180)

    save_geotiff(
        output_dir / "MUMBAI_S2_20260215_PORT_CLOUDY.tif",
        port_t2,
        bounds=mumbai_bounds,
    )

    print("\nSuccessfully generated all sample GeoTIFF scenes in:", output_dir)


if __name__ == "__main__":
    import sys
    dest = Path(__file__).resolve().parent.parent / "data" / "samples"
    if len(sys.argv) > 1:
        dest = Path(sys.argv[1])
    generate_all_sample_scenes(dest)
