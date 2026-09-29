# GeoNexa — Semantic Earth Observation Search & Intelligence Platform

> **Target Problem Statement:** SIH26227 — Semantic Retrieval and Multi-Temporal Change Analysis of Satellite Imagery  
> **Tagline:** Offline, on-premises cross-modal Earth Observation intelligence engine for natural-language satellite search, site similarity, and multi-temporal change detection.

---

## 1. Executive Summary

**GeoNexa** is an air-gapped, on-premises Earth Observation search and intelligence platform designed for remote sensing analysts. It enables cross-modal discovery across large satellite-imagery archives using natural language queries (e.g. *"urban buildings near water"*, *"river and surrounding vegetation"*), automatic visual site similarity matching, and confident multi-temporal change detection with false-alarm suppression.

### Core Analyst Workflow

```
SEARCH  ──▶  DISCOVER  ──▶  INVESTIGATE  ──▶  COMPARE  ──▶  SIMILAR SITES  ──▶  PROVENANCE TRACE
```

---

## 2. Key Capabilities & Technical Highlights

- **RemoteCLIP Semantic Search:** Uses RemoteCLIP (ViT-B-32) foundation model pre-trained on Earth Observation imagery to encode both 4-band satellite chips and natural-language text into a shared 512-dimensional vector space.
- **FAISS Vector Search:** Sub-millisecond exact cosine similarity retrieval (`IndexFlatIP`) paired with relational SQLite spatial & temporal metadata filtering.
- **Geospatial Chip Tiling:** Preserves CRS (EPSG:4326), spatial bounding boxes, centroids, and multi-band radiometric resolution.
- **1:1 Stable Vector Mapping:** Strictly enforces 1 Tile ↔ 1 Vector ↔ 1 Stable Vector ID invariant with deduplication.
- **Incremental Ingestion:** SHA-256 content hashing skips unchanged tiles, indexing only newly ingested scenes.
- **100% Air-Gap Offline Compliance:** Zero runtime internet dependencies, zero cloud API calls, local model weights, local FAISS index, local SQLite database.
- **Auditable Provenance:** Every query, similarity search, and change detection produces an immutable execution trace.

---

## 3. System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                 GeoNexa React 18 + Vite UI                  │
│       Search | Tile Inspector | Change Engine | Provenance  │
└──────────────────────────────┬──────────────────────────────┘
                               │ REST / JSON
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Backend Router                   │
│         /api/search  |  /api/archive  |  /api/change        │
└──────────────┬──────────────────────────────┬───────────────┘
               │                              │
               ▼                              ▼
┌─────────────────────────────┐┌──────────────────────────────┐
│     RemoteCLIP Encoder      ││      FAISS + SQLite DB       │
│  ViT-B-32 (Local Weights)   ││ Vectors (512-d) + Metadata   │
└─────────────────────────────┘└──────────────────────────────┘
```

---

## 4. Setup & Execution Guide

### 4.1 Prerequisites
- Python 3.10+
- Node.js 18+ and npm
- `rasterio`, `torch`, `open-clip-torch`, `faiss-cpu`, `fastapi`

### 4.2 Environment Installation

```bash
# 1. Create and activate virtual environment
python -m venv .venv

# Windows:
.venv\Scripts\activate
# Linux / macOS:
source .venv/bin/activate

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Install Frontend dependencies
cd frontend
npm install
cd ..
```

---

## 5. Offline Data Staging & Index Pipeline

Execute the end-to-end pipeline using the provided scripts:

### Step 1: Stage Public Sentinel-2 Scenes (Guwahati AOI)
```bash
python scripts/stage_guwahati_sentinel2.py
```
*Outputs calibrated 4-band Sentinel-2 L2A GeoTIFFs to `data/public/raw/sentinel2/`.*

### Step 2: Ingest & Tile Scenes
```bash
python scripts/ingest.py --data-dir data/public/raw/sentinel2
```
*Validates GeoTIFFs, extracts geospatial metadata, creates 256×256 georeferenced chips in `data/public/tiles/`, registers SQLite records in `metadata.db`, and updates `data/public/manifests/scenes.csv`.*

### Step 3: Build RemoteCLIP Vector Index
```bash
python scripts/build_index.py --force-rebuild
```
*Generates 512-dim L2-normalized RemoteCLIP embeddings, populates FAISS `indexes/main.index`, registers SQLite `embeddings`, and writes `index_manifest`.*

### Step 4: Test Incremental Ingestion
```bash
python scripts/incremental_ingest.py
```
*Verifies content hash skipping for unchanged tiles.*

### Step 5: Verify 100% Offline Readiness
```bash
python scripts/check_offline.py
```

---

## 6. Running GeoNexa

### Start Backend API Server
```bash
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```
*API Swagger Documentation available at: `http://localhost:8000/docs`*

### Start Frontend Development Server
```bash
cd frontend
npm run dev
```
*Open your browser at: `http://localhost:5173`*

---

## 7. Testing & Evaluation

### Run Unit & Integration Tests
```bash
pytest backend/tests/ -v
```

### Run Retrieval Relevance Benchmark
```bash
python scripts/evaluate_retrieval.py
```
*Evaluates against `data/evaluation/retrieval_relevance.csv` and outputs Recall@K, Precision@K, MRR, and latency metrics to `reports/`.*

### Run System Benchmark
```bash
python scripts/benchmark_system.py
```
*Measures hardware, storage, index size, and P50/P95 query latencies.*

---

## 8. Repository Structure

```
semantic-eo-search/
├── backend/
│   ├── app/
│   │   ├── api/             # FastAPI REST endpoints
│   │   ├── archive/         # Ingestion, georeferenced tiling, metadata extraction
│   │   ├── change/          # Temporal matching, change detection, confidence scoring
│   │   ├── embeddings/      # RemoteCLIP model abstraction & local loader
│   │   ├── models/          # Pydantic schemas
│   │   ├── provenance/      # Immutable audit trail & trace records
│   │   ├── query/           # Query classification & router
│   │   ├── retrieval/       # FAISS vector store & spatiotemporal filters
│   │   ├── config.py        # Central configuration
│   │   ├── db.py            # SQLite schema & connection manager
│   │   └── main.py          # FastAPI application entry point
│   └── tests/               # Unit & integration test suite
├── data/
│   ├── public/
│   │   ├── raw/sentinel2/   # Full multi-spectral source scenes
│   │   ├── tiles/           # 256x256 georeferenced chips
│   │   ├── metadata/        # SQLite metadata.db
│   │   └── manifests/       # scenes.csv & index_manifest
│   ├── synthetic/tests/     # Strictly separated unit test fixtures
│   └── evaluation/          # Ground-truth retrieval relevance dataset
├── docs/
│   ├── data_acquisition.md  # AOI selection & Sentinel-2 catalog
│   ├── model_provenance.md  # RemoteCLIP architecture & license
│   ├── offline_validation.md# Air-gap compliance & verification
│   └── confidence_model.md  # False-alarm suppression formulation
├── frontend/                # React 18 + Vite Intelligence Analyst UI
├── models/
│   └── remoteclip-vit-b-32/ # Local RemoteCLIP PyTorch checkpoint
├── reports/                 # Evaluation and benchmark reports
├── scripts/
│   ├── stage_guwahati_sentinel2.py # Staging script for Guwahati AOI
│   ├── ingest.py                   # Ingestion & tiling script
│   ├── build_index.py              # FAISS vector builder
│   ├── incremental_ingest.py       # Content hash incremental ingest
│   ├── check_offline.py            # Offline readiness check
│   ├── evaluate_retrieval.py       # IR metrics evaluation
│   └── benchmark_system.py         # Hardware & latency benchmark
├── requirements.txt
└── README.md
```
