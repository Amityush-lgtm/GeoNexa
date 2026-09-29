# Semantic EO Search

**Semantic Retrieval and Multi-Temporal Change Analysis of Satellite Imagery**

> SIH26227 — Smart India Hackathon 2026

---

## Overview

Semantic EO Search is an offline, on-premises Earth Observation search and analysis platform. It enables analysts to search a local satellite-imagery archive using natural language and image similarity, investigate locations, analyze changes over time, and trace evidence provenance.

### Core Workflow

```
SEARCH → DISCOVER → INVESTIGATE → CHANGE → SIMILARITY → EVIDENCE
```

### Key Capabilities

- **Semantic Search** — Find satellite tiles using natural language ("newly built structures near a river")
- **Image Similarity** — Discover locations that look similar to a selected tile
- **Change Analysis** — Detect and analyze changes between temporal observations
- **False-Alarm Suppression** — Confidence-aware change detection that accounts for seasonal, atmospheric, and sensor confounders
- **Provenance** — Full traceability of every result back to source data, models, and parameters
- **Offline Operation** — Runs entirely on-premises with no external API dependencies

---

## Architecture

```
React Frontend  ──▶  FastAPI Backend  ──▶  SQLite + FAISS
                                           │
                          ┌────────────────┼────────────────┐
                          ▼                ▼                ▼
                     Archive           Retrieval         Change
                     Service           Service          Service
                          │                │                │
                          ▼                ▼                ▼
                      rasterio          CLIP ViT        Temporal
                      Tiler             FAISS           Detector
```

See [docs/architecture.md](docs/architecture.md) for the full architecture diagram.

---

## Prerequisites

- Python 3.10+
- Node.js 18+ and npm
- GDAL (system library — required by rasterio)
- ~2 GB disk space for models
- ~4 GB RAM minimum (8 GB recommended)
- GPU optional (CUDA-capable GPU accelerates embeddings)

---

## Setup

### 1. Clone and create environment

```bash
git clone <repository-url>
cd semantic-eo-search

# Create Python virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Activate (Linux/macOS)
source .venv/bin/activate

# Install backend dependencies
pip install -r requirements.txt
```

### 2. Frontend setup

```bash
cd frontend
npm install
cd ..
```

---

## Offline Setup

All models and data must be available locally before disconnecting from the internet.

### 3. Download models

```bash
python scripts/download_models.py
```

This downloads:
- CLIP ViT-B/32 weights → `models/clip-vit-b-32/`

After download, no internet connection is required.

### 4. Verify offline readiness

```bash
python scripts/check_offline.py
```

Expected output:
```
OFFLINE READINESS CHECK
✓ Model weights present
✓ Embedding model loadable
✓ Vector index present (or empty — will be created on first ingest)
✓ SQLite database present (or will be created)
✓ No external inference endpoint required
```

---

## Dataset Setup

### 5. Prepare satellite imagery

Place GeoTIFF files in the data directory:

```
data/
    archive/
        scenes/
            scene_001.tif
            scene_002.tif
            ...
```

**Requirements:**
- GeoTIFF format (.tif / .tiff)
- Valid CRS (coordinate reference system)
- At least 3 bands (RGB) for embedding generation
- Acquisition date in filename or metadata

### 6. Ingest scenes

```bash
# Ingest a single scene
python scripts/ingest.py --scene data/archive/scenes/scene_001.tif

# Ingest all scenes in a directory
python scripts/ingest.py --directory data/archive/scenes/
```

This will:
1. Validate each scene
2. Extract metadata
3. Generate tiles (256×256 with 32px overlap)
4. Store metadata in SQLite

---

## Index Build

### 7. Build the vector index

```bash
python scripts/build_index.py
```

This will:
1. Load the CLIP model
2. Encode all tiles
3. Build the FAISS index
4. Save to `indexes/main.index`

---

## Incremental Ingestion

### 8. Add new imagery without rebuilding

```bash
python scripts/incremental_ingest.py --directory data/archive/scenes/
```

This will:
1. Hash each tile's content
2. Compare against the index manifest
3. Skip unchanged tiles
4. Embed and index only new/modified tiles
5. Update the FAISS index and manifest

---

## Running

### Backend

```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

API docs available at: http://localhost:8000/docs

### Frontend

```bash
cd frontend
npm run dev
```

Application available at: http://localhost:5173

---

## Configuration

Create a `.env` file in the project root:

```env
# Core paths
DATA_DIR=./data/archive
MODEL_PATH=./models/clip-vit-b-32
FAISS_INDEX_PATH=./indexes/main.index
DATABASE_PATH=./data/archive/metadata.db

# Offline mode
OFFLINE_MODE=true

# Tiling
TILE_SIZE=256
TILE_OVERLAP=32

# Search
DEFAULT_TOP_K=20

# Embedding
EMBEDDING_MODEL=clip-vit-b-32
DEVICE=cpu  # or cuda

# Server
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
```

---

## Running Tests

```bash
# Run all tests
pytest backend/tests/ -v

# Run specific test modules
pytest backend/tests/test_ingestion.py -v
pytest backend/tests/test_retrieval.py -v
pytest backend/tests/test_change.py -v
pytest backend/tests/test_incremental.py -v
```

---

## Running Evaluation

### Retrieval evaluation

```bash
python scripts/evaluate_retrieval.py --output reports/retrieval_evaluation.json
```

### Change detection evaluation

```bash
python scripts/evaluate_change.py --output reports/change_evaluation.json
```

### System metrics

```bash
python scripts/evaluate_system.py --output reports/system_metrics.json
```

Reports are saved as JSON in the `reports/` directory.

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/archive/ingest` | Ingest a single scene |
| `POST` | `/api/archive/ingest/batch` | Ingest multiple scenes |
| `GET` | `/api/archive/stats` | Archive statistics |
| `GET` | `/api/archive/tiles/{tile_id}` | Get tile metadata |
| `GET` | `/api/archive/tiles/{tile_id}/image` | Get tile image |
| `POST` | `/api/search` | Semantic text search |
| `POST` | `/api/search/similar` | Image-to-image similarity |
| `POST` | `/api/change/analyze` | Run change analysis |
| `GET` | `/api/change/{analysis_id}` | Get analysis result |
| `GET` | `/api/change/temporal/{tile_id}` | Temporal observations |
| `POST` | `/api/query` | Route a natural-language query |
| `GET` | `/api/provenance/{id}` | Get provenance record |
| `GET` | `/api/health` | Health + offline readiness |

---

## Demo Cases

1. **Semantic Search** — "newly built structures near a river" → ranked tiles
2. **Similar Sites** — Select tile → find similar locations
3. **Change Analysis** — Select tile → before/after/change map
4. **Question Answering** — "What changed here?" → evidence-grounded answer
5. **False Alarm** — Seasonal variation → system reduces confidence
6. **Incremental Ingestion** — Add 20 tiles → only new tiles processed

---

## Project Structure

```
semantic-eo-search/
├── backend/
│   ├── app/
│   │   ├── api/              — FastAPI route handlers
│   │   ├── archive/          — Ingestion, tiling, metadata
│   │   ├── embeddings/       — Embedding model interface + CLIP
│   │   ├── retrieval/        — FAISS, search, similarity, filters
│   │   ├── change/           — Temporal, detection, confidence
│   │   ├── provenance/       — Provenance tracking
│   │   ├── query/            — Query routing
│   │   ├── models/           — Pydantic schemas
│   │   ├── services/         — Service orchestration
│   │   ├── db.py             — Database connection
│   │   └── main.py           — FastAPI application
│   └── tests/                — Test suite
├── frontend/
│   ├── src/
│   │   ├── components/       — React components
│   │   ├── pages/            — Page components
│   │   ├── services/         — API client
│   │   └── ...
│   └── ...
├── data/
│   ├── archive/              — Scene + tile storage
│   ├── evaluation/           — Evaluation data
│   └── samples/              — Sample imagery
├── models/                   — Local model weights
├── indexes/                  — FAISS index files
├── scripts/                  — Utility scripts
├── docs/                     — Documentation
├── reports/                  — Evaluation reports
├── requirements.txt
├── .env.example
└── README.md
```

---

## License

[To be determined]

---

## Team

Smart India Hackathon 2026 — SIH26227
