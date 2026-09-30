# 🛰️ GeoNexa — Semantic Earth Observation Search & Multi-Temporal Intelligence Platform

> **Target Problem Statement:** SIH26227 — Semantic Retrieval and Multi-Temporal Change Analysis of Satellite Imagery  
> **Architecture:** 100% Air-Gapped, On-Premises Cross-Modal Earth Observation Engine powered by Fine-Tuned **RemoteCLIP (ViT-B-32)**, **FAISS Vector Indexing**, and **Multi-Band False Change Suppression**.

---

## 1. Executive Summary

**GeoNexa** is an air-gapped, on-premises Earth Observation (EO) intelligence and discovery platform designed for remote sensing analysts, defence reconnaissance, and environmental monitoring agencies. 

It solves two critical bottlenecks in contemporary satellite data exploitation:
1. **The Semantic Discovery Bottleneck**: Searching massive multi-terabyte optical satellite archives without relying on rigid, pre-annotated metadata tags — enabling intuitive natural-language queries (e.g., *"agricultural crop fields with distinct parcel boundaries"*, *"urban industrial roofs near Bengaluru"*).
2. **The False Change Alarm Bottleneck**: Traditional pixel differencing suffers from catastrophic false alarms caused by seasonal phenology shifts, slight sub-pixel satellite misalignment, and illumination changes. GeoNexa integrates **physical spectral index verification ($\Delta\text{NDVI}$, $\Delta\text{NDWI}$, $\Delta\text{NDBI}$)**, **2D FFT sub-pixel phase correlation registration**, and **circular Day-of-Year (DOY) seasonal penalty models** to ensure only genuine structural and environmental changes are flagged.

---

## 2. Core Analyst Workflow & Capabilities

```
┌──────────────┐      ┌───────────────┐      ┌────────────────┐      ┌─────────────────┐      ┌──────────────────┐
│   NATURAL    │      │  CALIBRATED   │      │ TILE INSPECTOR │      │ MULTI-TEMPORAL  │      │    IMMUTABLE     │
│   LANGUAGE   │ ──▶  │ VECTOR SEARCH │ ──▶  │ & RADIOMETRIC  │ ──▶  │  CHANGE ENGINE  │ ──▶  │ PROVENANCE TRACE │
│  ROUTED NLP  │      │ (FAISS IP-512)│      │  VERIFICATION  │      │ (PHYSICAL + ML) │      │  AUDIT LINEAGE   │
└──────────────┘      └───────────────┘      └────────────────┘      └─────────────────┘      └──────────────────┘
```

* **Zero-Cloud Air-Gap Offline Compliance**: 100% self-contained on local hardware. Zero external API calls, zero telemetry, local GPU inference, local FAISS vector store, and local SQLite metadata.
* **Fine-Tuned RemoteCLIP Foundation Model**: ViT-B-32 vision-language model domain fine-tuned on 27,000 real Sentinel-2 optical satellite scenes across 10 land cover classes with WiSE-FT weight-space ensembling.
* **Natural Language Intent Router**: Automatically parses analyst queries, extracts geographic spatial bounds (e.g. Indian gazetteer bounds for Guwahati, Kochi, Bengaluru), date ranges, cloud cover constraints, and distinguishes between semantic search vs change analysis intent.
* **Calibrated Confidence Scoring**: Sigmoid-calibrated similarity scores translating raw CLIP dot products into realistic analyst match percentages (75%–98%).
* **Multi-Band Physical Change Confirmation**: Combines deep feature distance with physical NDVI (vegetation), NDWI (water bodies), and NDBI (built-up/impervious) index shifts.
* **Sub-Pixel Coregistration & Seasonal Filtering**: 2D FFT Phase Correlation shift $(\Delta x, \Delta y)$ measurement prevents sensor vibration false alarms, while circular Day-Of-Year (DOY) temporal normalization suppresses seasonal crop phenology cycles.
* **Reverse Visual Similarity**: Select any interesting satellite tile to immediately retrieve morphologically and spectrally similar landforms across the entire multi-scene archive.
* **Cryptographic Provenance Lineage**: Every query, similarity match, and change analysis produces an immutable audit trace recording model weights hash, input tile hashes, execution parameters, and timestamps.

---

## 3. End-to-End System Architecture

```
┌───────────────────────────────────────────────────────────────────────────────────────────┐
│                                GeoNexa Web Application                                    │
│                 React 18 + Vite + Tailwind/Modern Glassmorphism UI                        │
│   [Semantic Search]   [Tile Inspector]   [Change Engine]   [Site Similarity]   [Provenance]│
└─────────────────────────────────────────────┬─────────────────────────────────────────────┘
                                              │ REST JSON / Binary Tile Stream
                                              ▼
┌───────────────────────────────────────────────────────────────────────────────────────────┐
│                                FastAPI Backend Engine                                     │
│  ┌───────────────────────┐  ┌─────────────────────────┐  ┌─────────────────────────────┐  │
│  │ Natural Language NLP  │  │ Multi-Temporal Change   │  │ Provenance & Audit Tracker  │  │
│  │ Intent & Filter Router│  │ False Change Suppression│  │ Cryptographic Lineage Logs  │  │
│  └──────────┬────────────┘  └────────────┬────────────┘  └──────────────┬──────────────┘  │
└─────────────┼────────────────────────────┼──────────────────────────────┼─────────────────┘
              │                            │                              │
              ▼                            ▼                              ▼
┌───────────────────────────┐┌───────────────────────────┐┌────────────────────────────────┐
│   RemoteCLIP ViT-B-32     ││  Physical Spectral Engine ││     Storage & Index Layer      │
│ 512-dim Normalized Vector ││  ΔNDVI | ΔNDWI | ΔNDBI    ││ • FAISS Vector Store (512-d)  │
│ PyTorch CUDA / FP16 AMP   ││  2D FFT Phase Correlation ││ • SQLite Metadata Database    │
│ Domain Fine-Tuned Weights ││  Circular DOY Penalty     ││ • 4-Band Georeferenced Tiles  │
└───────────────────────────┘└───────────────────────────┘└────────────────────────────────┘
```

---

## 4. Live Demonstration Guide for Judges & Evaluators

Follow this step-by-step walkthrough during live project presentation and hackathon evaluation:

### 🎬 Phase 1: Natural Language Semantic Discovery
1. **Open the Web UI**: Navigate to `http://localhost:5173`.
2. **Search Query 1 (Urban & Industrial infrastructure)**:
   * Enter: `urban industrial roofs and logistics warehouses`
   * **Key Highlights to Show**:
     - Sub-50ms search latency across indexed Sentinel-2 satellite tiles.
     - Calibrated Match Percentages (e.g. 94%–98%).
     - Top retrieved tiles show commercial warehouses, metal roofs, and transportation networks.
3. **Search Query 2 (Coastal & Sediment Plumes)**:
   * Enter: `coastal sea water with turquoise sediment runoff`
   * **Key Highlights to Show**:
     - Accurately retrieves coastal ocean tiles showing azure waters and sediment plume runoff along shorelines.
4. **Search Query 3 (Agricultural Land)**:
   * Enter: `agricultural crop fields with distinct parcel boundaries`
   * **Key Highlights to Show**:
     - Returns agricultural cropland patchwork and irrigation parcel grids.
5. **Search Query 4 (Intent Router & Spatial Filter Extraction)**:
   * Enter: `show urban residential areas in Bengaluru after May 2024`
   * **Key Highlights to Show**:
     - Look at the **Intent Banner**: The system automatically extracted spatial bounds for Bengaluru and temporal filters without needing manual dropdowns!

---

### 🎬 Phase 2: Deep Radiometric Tile Inspection
1. Click **"Inspect"** on any retrieved tile (e.g., `S2A_MSIL2A_20240825_URBAN_INDUSTRIAL_HUB_x00_y00`).
2. **Switch Visualization Modes**:
   * **True Color (RGB)**: Crisp 10m spatial resolution optical imagery.
   * **False Color (NIR-R-G)**: Highlights dense vegetative chlorophyll in bright red and built-up areas in cyan/grey.
3. **Inspect Physical Spectral Indices**:
   * $\text{NDVI} = \frac{\text{NIR} - \text{Red}}{\text{NIR} + \text{Red}}$ (Vegetation density)
   * $\text{NDWI} = \frac{\text{Green} - \text{NIR}}{\text{Green} + \text{NIR}}$ (Surface water delineator)
   * $\text{NDBI} = \frac{\text{SWIR/Red} - \text{NIR}}{\text{SWIR/Red} + \text{NIR}}$ (Built-up index)
4. **Geographic Coordinates**: Bounding box coordinates, centroid latitude/longitude, acquisition date, and sensor metadata.

---

### 🎬 Phase 3: False Change Suppression & Multi-Temporal Change Engine
1. Click the **"Change Engine"** tab or click **"Change Analysis"** from any tile card.
2. Select a multi-temporal pair:
   * **T1 (Baseline)**: `SENT_20260115_S2A_MSIL2A_20260115_GUWAHATI_T1_x00_y00` (Winter 2026)
   * **T2 (Observation)**: `SENT_20260425_S2A_MSIL2A_20260425_GUWAHATI_T3_x01_y01` (Pre-monsoon 2026)
3. Click **"Run Multi-Temporal Analysis"**.
4. **Key Technical Highlights to Explain to Judges**:
   * **Interactive Split-Screen Swipe Slider**: Smoothly compare before vs after imagery.
   * **Binary Change Mask Overlay**: Red pixels highlight verified structural changes.
   * **Confidence Breakdown Cards**:
     - **$\Delta\text{NDVI} = -0.3319$**: Physical confirmation of vegetation canopy loss/clearing.
     - **Sub-Pixel Registration Shift**: Measured via 2D FFT phase correlation to prevent parallax false alarms.
     - **Seasonal DOY Confounder Score**: Calculates circular day-of-year distance (100 days) to prevent confusing winter harvest with permanent deforestation.
     - **Overall Confidence Rating**: Categorized with high precision into Verified vs Confounded change.

---

### 🎬 Phase 4: Reverse Visual Site Similarity
1. Click the **"Site Similarity"** tab.
2. Select any reference satellite tile (e.g., a river corridor or dense forest patch).
3. Set Top-K to `8` and click **"Find Visually Similar Sites"**.
4. **Key Highlights to Show**:
   - The engine performs pure visual embedding vector search in the 512-dim RemoteCLIP feature space.
   - Finds topologically and spectrally matching landforms across different satellite acquisition dates and locations.

---

### 🎬 Phase 5: Cryptographic Provenance & Audit Trail
1. Click **"Provenance Trace"** tab.
2. Select any recent Execution Trace ID.
3. **Key Highlights to Show**:
   - Complete audit trail of the analysis:
     - Exact model checkpoint hash (`RemoteCLIP-ViT-B-32-finetuned.pt`)
     - Input tile IDs and source file paths
     - Execution parameters (thresholds, index weights)
     - Timestamp and millisecond processing latency
   - Crucial for defence, environmental legal auditing, and regulatory compliance.

---

## 5. Quick Start & Local Execution

### 5.1 Prerequisites
* Python 3.10+ with CUDA-enabled PyTorch (GPU recommended: NVIDIA RTX 3050/4050/4060 or Google Colab T4)
* Node.js 18+ and npm

### 5.2 Environment Setup
```powershell
# 1. Clone repository
git clone https://github.com/Amityush-lgtm/GeoNexa.git
cd GeoNexa

# 2. Setup Python environment
python -m venv venv_cuda
.\venv_cuda\Scripts\activate
pip install -r requirements.txt

# 3. Setup Frontend dependencies
cd frontend
npm install
cd ..
```

### 5.3 Staging Data & Building Vector Index
```powershell
# Stage real Sentinel-2 satellite imagery (4-band R,G,B,NIR)
python scripts/stage_eurosat_scenes.py

# Build FAISS vector database
python scripts/build_index.py --force-rebuild
```

### 5.4 Starting the Live Platform
```powershell
# Terminal 1: Launch Backend API Server
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload

# Terminal 2: Launch Frontend Development Server
cd frontend
npm run dev
```
* Backend API Documentation: `http://localhost:8000/docs`  
* Analyst Web Application: `http://localhost:5173`

---

## 6. RemoteCLIP Foundation Model Fine-Tuning

GeoNexa includes a complete contrastive fine-tuning pipeline on **27,000 real Sentinel-2 optical satellite scenes (EuroSAT)** across 10 land cover categories:

```
EuroSAT Classes:
├── AnnualCrop (Cultivated cropland parcel grids)
├── Forest (Dense canopy woodland & natural reserves)
├── HerbaceousVegetation (Prairie meadows & grasslands)
├── Highway (Asphalt transportation corridors)
├── Industrial (Commercial logistics parks & warehouses)
├── Pasture (Grazing fields & farm paddocks)
├── PermanentCrop (Orchards & vineyard plantation rows)
├── Residential (Suburban housing & urban street grids)
├── River (Freshwater channels & sediment riparian banks)
└── SeaLake (Marine coastal waters & turquoise sediment plumes)
```

### Option A: 1-Click Google Colab GPU Training (Free T4 / A100)
Open `notebooks/GeoNexa_Colab_FineTuning.ipynb` in Google Colab and run all 5 cells sequentially. It automatically:
1. Clones the repository & installs dependencies.
2. Downloads base foundation weights and 27,000 Sentinel-2 EuroSAT images.
3. Generates 25,200 contrastive image-text pairs.
4. Trains for 15 epochs with InfoNCE loss + Cosine LR schedule + AdamW on GPU.
5. Applies **WiSE-FT (Weight-Space Ensemble)** blending fine-tuned domain weights ($\alpha=0.4$) with robust zero-shot foundation features, exporting `RemoteCLIP-ViT-B-32-finetuned.pt`.

### Option B: Local GPU Training
```powershell
python -m training.train `
    --train-data training_data/train_pairs.json `
    --val-data training_data/val_pairs.json `
    --checkpoint models/remoteclip-vit-b-32/RemoteCLIP-ViT-B-32.pt `
    --output-dir checkpoints `
    --epochs 15 `
    --batch-size 32 `
    --lr 1e-5 `
    --device cuda `
    --unfreeze-last-n 4
```

---

## 7. Verification & Benchmarking

Execute the evaluation benchmark suite to measure Information Retrieval (IR) performance and system latency:

```powershell
# Run Retrieval Quality Benchmark (Recall@K, Precision@K, MRR)
python scripts/evaluate_retrieval.py

# Run System Performance Benchmark (Disk I/O, FAISS latency, RAM)
python scripts/benchmark_system.py

# Run Offline Air-Gap Verification
python scripts/check_offline.py
```

---

## 8. Repository Structure

```
GeoNexa/
├── backend/
│   ├── app/
│   │   ├── api/             # FastAPI REST endpoints (Search, Change, Archive, Provenance, Query)
│   │   ├── archive/         # GeoTIFF tiling, radiometric metadata extraction
│   │   ├── change/          # Spectral index deltas, FFT phase correlation, DOY seasonal penalty
│   │   ├── embeddings/      # RemoteCLIP ViT-B-32 PyTorch inference engine
│   │   ├── models/          # Pydantic schemas and API contracts
│   │   ├── provenance/      # Immutable audit trail tracker
│   │   ├── query/           # Natural language query router & Indian gazetteer
│   │   ├── retrieval/       # FAISS vector store & metadata filtered search
│   │   ├── config.py        # Central application settings
│   │   ├── db.py            # SQLite database manager
│   │   └── main.py          # FastAPI application entry point
│   └── tests/               # Backend test suite
├── data/
│   ├── public/
│   │   ├── raw/sentinel2/   # 4-band calibrated Sentinel-2 GeoTIFF scenes
│   │   ├── tiles/           # 256x256 georeferenced satellite chips
│   │   ├── metadata/        # SQLite metadata.db
│   │   └── change_results/  # Binary change masks and spectral diff maps
│   └── evaluation/          # Benchmark ground-truth datasets
├── frontend/                # React 18 + Vite Intelligence Analyst UI
│   ├── src/
│   │   ├── components/      # SearchPage, TileInspector, ChangeEngine, ProvenanceTrace, etc.
│   │   └── api/             # REST client
├── models/                  # RemoteCLIP-ViT-B-32-finetuned.pt (Local weights)
├── notebooks/
│   └── GeoNexa_Colab_FineTuning.ipynb  # Self-contained Google Colab GPU notebook
├── reports/                 # Benchmark evaluation reports
├── scripts/
│   ├── stage_eurosat_scenes.py     # High-res seamless Sentinel-2 scene builder
│   ├── prepare_eurosat_pairs.py    # 25,200 image-caption contrastive pair generator
│   ├── build_index.py              # FAISS vector indexing engine
│   ├── export_finetuned_model.py   # WiSE-FT checkpoint exporter
│   ├── evaluate_retrieval.py       # IR metrics evaluation
│   └── check_offline.py            # Air-gap verification
├── training/
│   ├── dataset.py                  # PyTorch EO dataset loader & augmentations
│   └── train.py                    # Multi-worker GPU training loop (InfoNCE loss)
├── requirements.txt
└── README.md
```

---

## 9. Hackathon Team & Acknowledgments
* **Smart India Hackathon (SIH 2026)** — Problem Statement **SIH26227**
* Built with PyTorch, OpenCLIP, FAISS, Rasterio, FastAPI, React 18, and Vite.
* Dedicated to high-accuracy, privacy-preserving, air-gapped Earth Observation search and intelligence.
