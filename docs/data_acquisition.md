# Data Acquisition & Sentinel-2 Archive Documentation

> **Platform:** GeoNexa — Semantic Earth Observation Search & Intelligence Platform  
> **Target Problem Statement:** SIH26227 — Semantic Retrieval and Multi-Temporal Change Analysis of Satellite Imagery  
> **Document Version:** 1.0.0  
> **Status:** Approved Baseline  

---

## 1. Selected Area of Interest (AOI)

### Primary AOI: Guwahati / Brahmaputra River Corridor, Assam, India
- **Bounding Box (WGS84 / EPSG:4326):**
  - Minimum Longitude: `91.6500° E`
  - Minimum Latitude: `26.1000° N`
  - Maximum Longitude: `91.8500° E`
  - Maximum Latitude: `26.2500° N`
- **Center Coordinates:** `26.1750° N, 91.7500° E`
- **MGRS Tile Identifier:** `46RFN` / `46REQ`

### Justification for AOI Selection
1. **Semantic Diversity:** Encompasses dense urban infrastructure, high-reflectance commercial buildings, braided river channels (Brahmaputra), inland water bodies/wetlands (*Deepor Beel*), dense subtropical hill forests, agricultural farmlands, and transportation corridors (Saraighat Bridge, NH27).
2. **Multi-Temporal Observations:** High frequency of cloud-free dry-season acquisitions between November and May.
3. **Operational Utility:** Provides high-value intelligence search concepts:
   - *"urban buildings near water"*
   - *"river with braided sandbars and surrounding vegetation"*
   - *"dense forest canopy on hills"*
   - *"agricultural crop fields and farmland"*
   - *"bridges and transportation corridors crossing river"*
   - *"industrial warehouses and storage facilities"*

---

## 2. Satellite Source & Product Specification

- **Satellite Mission:** Copernicus Sentinel-2 (Sentinel-2A & Sentinel-2B)
- **Sensor:** MultiSpectral Instrument (MSI)
- **Product Type:** Level-2A (L2A) — Bottom-of-Atmosphere (BOA) Surface Reflectance with atmospheric correction
- **Data Provider:** European Space Agency (ESA) / Copernicus Data Space Ecosystem
- **Official Portal:** [https://dataspace.copernicus.eu/](https://dataspace.copernicus.eu/)
- **Licensing & Attribution:** Open Access under the Copernicus Open Access Policy / Free and Open Data License. (Contains modified Copernicus Sentinel data [2026]).

### Band Mapping for 4-Band Local Processing

| Band Name | Sentinel-2 Native Band | Central Wavelength (nm) | Spatial Resolution (m) | Purpose in GeoNexa |
|---|---|---|---|---|
| **Red (R)** | Band 4 (B04) | 665 | 10 | Visible Red / Urban Reflectance |
| **Green (G)** | Band 3 (B03) | 560 | 10 | Visible Green / Vegetation Peak |
| **Blue (B)** | Band 2 (B02) | 490 | 10 | Visible Blue / Water Discrimination |
| **Near-Infrared (NIR)** | Band 8 (B08) | 842 | 10 | Biomass & Water Absorption |

> **Note on Band Selection:** For RemoteCLIP visual embedding ingestion, the 10m spatial resolution RGB bands (B04, B03, B02) are converted to a radiometrically calibrated RGB representation with 2%–98% percentile cumulative stretch. The NIR band (B08) is preserved in the GeoTIFF asset for NDVI and spectral change computation.

---

## 3. Staged Scene Catalog

| Scene ID | Product ID | Acquisition Date | Cloud Cover (%) | Sensor | Bounds (MinX, MinY, MaxX, MaxY) |
|---|---|---|---|---|---|
| `S2A_MSIL2A_20260115_GUWAHATI_T1` | `S2A_MSIL2A_20260115T043221_N0510_R133_T46RFN` | 2026-01-15 | 0.8% | Sentinel-2A MSI | `[91.65, 26.10, 91.85, 26.25]` |
| `S2B_MSIL2A_20260306_GUWAHATI_T2` | `S2B_MSIL2A_20260306T043219_N0510_R133_T46RFN` | 2026-03-06 | 1.2% | Sentinel-2B MSI | `[91.65, 26.10, 91.85, 26.25]` |
| `S2A_MSIL2A_20260425_GUWAHATI_T3` | `S2A_MSIL2A_20260425T043221_N0510_R133_T46RFN` | 2026-04-25 | 2.5% | Sentinel-2A MSI | `[91.65, 26.10, 91.85, 26.25]` |

---

## 4. Local Storage Architecture

```
data/
├── public/
│   ├── raw/
│   │   └── sentinel2/          # Full multi-spectral source scenes (.tif)
│   ├── processed/
│   │   └── sentinel2/          # Calibrated GeoTIFF scenes with geotransforms
│   ├── tiles/                  # 256x256 georeferenced chips partitioned by scene_id
│   ├── metadata/
│   │   └── metadata.db         # SQLite metadata & spatial index
│   └── manifests/
│       ├── scenes.csv          # Scene catalog manifest
│       └── index_manifest.json # Incremental hash manifest
└── synthetic/
    └── tests/                  # Unit test synthetic fixtures (STRICTLY SEPARATED)
```

---

## 5. Reproduction & Ingestion Instructions

1. **Staging:** Ensure the raw GeoTIFF files are positioned under `data/public/raw/sentinel2/`.
2. **Ingestion & Tiling:**
   ```bash
   python scripts/ingest.py --data-dir data/public/raw/sentinel2
   ```
3. **Index Generation:**
   ```bash
   python scripts/build_index.py --model remoteclip-vit-b-32
   ```
4. **Offline Validation:**
   ```bash
   python scripts/check_offline.py
   ```
