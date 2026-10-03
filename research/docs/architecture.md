# Architecture — Semantic EO Search

> **Project:** SIH26227 — Semantic Retrieval and Multi-Temporal Change Analysis of Satellite Imagery
> **Version:** 0.1.0

---

## 1. System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        ANALYST BROWSER                             │
│                                                                     │
│  ┌───────────┐  ┌──────────┐  ┌─────────────┐  ┌───────────────┐  │
│  │  Search    │  │ Results  │  │Investigation│  │ Change View   │  │
│  │  Page      │  │  Grid    │  │    Page     │  │ Before/After  │  │
│  └─────┬─────┘  └────┬─────┘  └──────┬──────┘  └──────┬────────┘  │
│        └──────────────┼───────────────┼─────────────────┘          │
│                       │  React + Vite │                             │
└───────────────────────┼───────────────┼─────────────────────────────┘
                        │  HTTP / REST  │
                        ▼               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         FastAPI BACKEND                             │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                      API Layer (Routes)                      │   │
│  │  /api/search  /api/archive  /api/change  /api/provenance    │   │
│  └──────────────────────┬───────────────────────────────────────┘   │
│                         │                                           │
│  ┌──────────────────────┼───────────────────────────────────────┐   │
│  │                  Service Layer                                │   │
│  │                                                               │   │
│  │  ┌────────────┐  ┌──────────────┐  ┌───────────────┐        │   │
│  │  │  Archive   │  │  Retrieval   │  │    Change     │        │   │
│  │  │  Service   │  │  Service     │  │   Service     │        │   │
│  │  └─────┬──────┘  └──────┬───────┘  └──────┬────────┘        │   │
│  │        │                │                  │                  │   │
│  │  ┌─────┴──────┐  ┌──────┴───────┐  ┌──────┴────────┐        │   │
│  │  │ Ingestion  │  │  Embedding   │  │  Temporal     │        │   │
│  │  │ Tiler      │  │  Model       │  │  Index        │        │   │
│  │  │ Metadata   │  │  Vector Store│  │  Detector     │        │   │
│  │  │ Manifest   │  │  Search Eng. │  │  Confidence   │        │   │
│  │  └─────┬──────┘  └──────┬───────┘  └──────┬────────┘        │   │
│  │        │                │                  │                  │   │
│  └────────┼────────────────┼──────────────────┼─────────────────┘   │
│           │                │                  │                      │
│  ┌────────┼────────────────┼──────────────────┼─────────────────┐   │
│  │        ▼                ▼                  ▼                  │   │
│  │   ┌─────────┐    ┌───────────┐    ┌────────────┐             │   │
│  │   │ rasterio│    │   FAISS   │    │  Change    │             │   │
│  │   │  GDAL   │    │  Index    │    │  Engine    │             │   │
│  │   └────┬────┘    └─────┬─────┘    └─────┬──────┘             │   │
│  │        │               │                │                     │   │
│  │        └───────────────┼────────────────┘                     │   │
│  │                        ▼                                      │   │
│  │              ┌──────────────────┐                             │   │
│  │              │     SQLite       │                             │   │
│  │              │  (metadata, prov │                             │   │
│  │              │   manifest, log) │                             │   │
│  │              └──────────────────┘                             │   │
│  │                  Storage Layer                                │   │
│  └───────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                   Query Router                                │   │
│  │  SEMANTIC_SEARCH │ IMAGE_SIMILARITY │ CHANGE │ VQA │ PROV   │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                  Provenance Tracker                           │   │
│  │  Records every operation: query, model, params, result       │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

                        FILE SYSTEM

┌──────────────────────────────────────────────────────────────────┐
│  data/archive/scenes/     — Original GeoTIFF scene files        │
│  data/archive/tiles/      — Generated tile chips                │
│  data/archive/metadata.db — SQLite database                     │
│  indexes/main.index       — FAISS vector index                  │
│  models/clip-vit-b-32/    — Local model weights                 │
│  reports/                 — Evaluation outputs                   │
└──────────────────────────────────────────────────────────────────┘
```

---

## 2. Module Architecture

### 2.1 Archive Module

```
app/archive/
    __init__.py
    ingestion.py      — Scene validation + orchestration
    tiler.py          — GeoTIFF → tile chips
    metadata.py       — Metadata extraction from rasters
    manifest.py       — Content hashing + incremental indexing
    quality.py        — Basic quality checks (readable, valid CRS, etc.)
```

**Responsibilities:**
- Accept GeoTIFF/TIFF/COG files
- Validate format, CRS, readability
- Extract metadata (date, sensor, bounds, bands)
- Tile into 256×256 chips with configurable overlap
- Preserve georeference per tile
- Generate content hash per tile
- Record everything in SQLite

**Data flow:**

```
GeoTIFF file
    │
    ├── validate_scene(path) → SceneMetadata
    │
    ├── extract_metadata(path) → {sensor, date, crs, bounds, bands}
    │
    ├── quality_check(path) → {readable: bool, valid_crs: bool, ...}
    │
    ├── tile_scene(path, tile_size=256, overlap=32) → List[TileRecord]
    │       │
    │       ├── For each tile: save chip + compute bbox in original CRS
    │       └── Return: tile_id, file_path, bbox, parent_scene
    │
    └── register_in_db(scene_metadata, tiles) → SQLite records
```

### 2.2 Embedding Module

```
app/embeddings/
    __init__.py
    base.py           — Abstract EmbeddingModel interface
    clip_model.py     — CLIP ViT-B/32 implementation
    manager.py        — Model loading + caching
```

**Interface:**

```python
class EmbeddingModel(ABC):
    @abstractmethod
    def encode_image(self, image: np.ndarray) -> np.ndarray:
        """Encode image → normalized vector."""

    @abstractmethod
    def encode_text(self, text: str) -> np.ndarray:
        """Encode text → normalized vector."""

    @abstractmethod
    def encode_images_batch(self, images: List[np.ndarray]) -> np.ndarray:
        """Batch encode images."""

    @property
    @abstractmethod
    def model_name(self) -> str: ...

    @property
    @abstractmethod
    def model_version(self) -> str: ...

    @property
    @abstractmethod
    def vector_dim(self) -> int: ...
```

**Design decisions:**
- Model loaded once at startup, cached in memory
- All vectors L2-normalized
- Band mapping: multi-band → RGB (configurable)
- Image resized to model input size (224×224 for CLIP)

### 2.3 Retrieval Module

```
app/retrieval/
    __init__.py
    vector_store.py   — FAISS wrapper
    search.py         — Semantic search pipeline
    similarity.py     — Image-to-image search
    filters.py        — Post-retrieval metadata filtering
```

**FAISS wrapper:**

```python
class VectorStore:
    def __init__(self, dimension: int, index_path: str = None): ...
    def add(self, vectors: np.ndarray, ids: List[int]) -> None: ...
    def search(self, query: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]: ...
    def save(self, path: str) -> None: ...
    def load(self, path: str) -> None: ...
    @property
    def size(self) -> int: ...
```

**Search pipeline:**

```
Text query
    │
    ▼
Text embedding (CLIP)
    │
    ▼
FAISS search (top_k * 2 candidates)
    │
    ▼
SQLite metadata join (tile_id, date, sensor, bbox, ...)
    │
    ▼
Post-retrieval filtering (date range, sensor, bbox)
    │
    ▼
Re-rank by similarity (already ranked, just trim to top_k)
    │
    ▼
Build response with provenance
```

### 2.4 Change Module

```
app/change/
    __init__.py
    temporal.py       — Temporal observation retrieval
    detector.py       — Change detection algorithms
    quality.py        — Quality/confounder checks
    confidence.py     — Confidence scoring
    alignment.py      — Image co-registration
```

**Change detection pipeline:**

```
T1 tile, T2 tile
    │
    ▼
Quality check (cloud, haze, readability)
    │
    ▼
Co-registration (feature-based alignment)
    │
    ▼
Radiometric normalization (histogram matching)
    │
    ▼
Difference computation (per-band)
    │
    ▼
Threshold + morphological filtering
    │
    ▼
Connected component analysis
    │
    ▼
Size filtering (min area)
    │
    ▼
Change mask generation
    │
    ▼
Confidence scoring
    │
    ▼
Evidence packaging
```

**Confidence model:**

```python
@dataclass
class ChangeConfidence:
    structural: float       # 0–1: magnitude of structural change
    seasonal_confound: float # 0–1: risk of seasonal false alarm
    cloud_contamination: float # 0–1: cloud/haze presence
    registration_quality: float # 0–1: co-registration quality
    persistence: float       # 0–1: change visible in multiple dates

    @property
    def final_score(self) -> float:
        """Weighted combination."""
        return max(0, min(1,
            self.structural * 0.4
            + self.persistence * 0.25
            + self.registration_quality * 0.15
            - self.seasonal_confound * 0.1
            - self.cloud_contamination * 0.1
        ))

    @property
    def label(self) -> str:
        score = self.final_score
        if score >= 0.7: return "HIGH"
        if score >= 0.4: return "MEDIUM"
        return "LOW"
```

### 2.5 Provenance Module

```
app/provenance/
    __init__.py
    tracker.py        — Provenance record creation
    models.py         — Provenance data structures
```

Every operation (search, change, similarity) calls:

```python
provenance_tracker.record(
    entity_type="search",
    query_text=query,
    embedding_model=model.model_name,
    parameters={"top_k": 20, "filters": filters},
    result_summary={"count": len(results), "top_score": results[0].score}
)
```

### 2.6 Query Router

```
app/query/
    __init__.py
    router.py         — Intent classification
```

**Rule-based routing (no LLM dependency):**

```python
PATTERNS = {
    "SEMANTIC_SEARCH": ["find", "search", "show", "locate", "where"],
    "IMAGE_SIMILARITY": ["similar", "like this", "looks like"],
    "CHANGE_ANALYSIS": ["changed", "change", "different", "before and after"],
    "VQA": ["what is", "describe", "visible", "identify"],
    "PROVENANCE": ["source", "where did", "provenance", "trace"],
}

def classify_query(text: str, context: dict) -> QueryType:
    # Keyword matching + context (e.g., if a tile is selected)
    ...
```

### 2.7 API Layer

```
app/api/
    __init__.py
    archive.py        — /api/archive/* routes
    search.py         — /api/search* routes
    change.py         — /api/change/* routes
    query.py          — /api/query route
    provenance.py     — /api/provenance/* routes
    health.py         — /api/health route
```

---

## 3. Data Architecture

### 3.1 Storage layout

```
semantic-eo-search/
│
├── data/
│   ├── archive/
│   │   ├── scenes/          — Original GeoTIFF files
│   │   │   ├── S2_20260118_001.tif
│   │   │   └── S2_20260418_001.tif
│   │   ├── tiles/           — Generated tile chips
│   │   │   ├── S2_20260118_001/
│   │   │   │   ├── S2_20260118_001_x00_y00.tif
│   │   │   │   ├── S2_20260118_001_x00_y01.tif
│   │   │   │   └── ...
│   │   │   └── S2_20260418_001/
│   │   │       └── ...
│   │   └── metadata.db     — SQLite database
│   │
│   ├── evaluation/          — Test/evaluation data
│   └── samples/             — Sample imagery for testing
│
├── indexes/
│   ├── main.index           — FAISS index file
│   └── id_mapping.json      — FAISS ID ↔ tile_id mapping
│
├── models/
│   └── clip-vit-b-32/       — Local model weights
│
└── reports/                 — Evaluation results
```

### 3.2 ID Design

| Entity | ID Format | Example |
|---|---|---|
| Scene | `{sensor}_{YYYYMMDD}_{seq}` | `S2_20260418_001` |
| Tile | `{scene_id}_x{XX}_y{YY}` | `S2_20260418_001_x04_y08` |
| Analysis | `chg-{uuid4_short}` | `chg-a1b2c3d4` |
| Provenance | `prov-{uuid4_short}` | `prov-e5f6g7h8` |
| Query | `q-{uuid4_short}` | `q-i9j0k1l2` |

---

## 4. Frontend Architecture

```
frontend/src/
│
├── components/
│   ├── SearchBar.jsx         — Main search input + filters
│   ├── FilterPanel.jsx       — Date, sensor, AOI filters
│   ├── ResultCard.jsx        — Individual result card
│   ├── ResultGrid.jsx        — Grid of result cards
│   ├── TileViewer.jsx        — Satellite image viewer
│   ├── ChangeView.jsx        — Before/after/change overlay
│   ├── TimelineView.jsx      — Temporal observation timeline
│   ├── ProvenancePanel.jsx   — Provenance trace display
│   ├── ConfidenceBadge.jsx   — Confidence level indicator
│   └── Layout/
│       ├── Navbar.jsx
│       └── Sidebar.jsx
│
├── pages/
│   ├── SearchPage.jsx        — Homepage: search + results
│   ├── InvestigationPage.jsx — Tile detail + actions
│   ├── ChangePage.jsx        — Change analysis view
│   ├── SimilarPage.jsx       — Similar sites view
│   ├── ArchivePage.jsx       — Archive management
│   └── HistoryPage.jsx       — Query + review history
│
├── services/
│   ├── api.js                — HTTP client for backend
│   └── config.js             — API URL, constants
│
├── App.jsx
├── main.jsx
└── index.css
```

### Page flow

```
SearchPage
    │ user enters query
    ▼
ResultGrid (ranked tiles)
    │ user clicks "Investigate"
    ▼
InvestigationPage
    │
    ├── "Analyze Change" → ChangePage
    ├── "Find Similar"   → SimilarPage
    ├── "Ask"            → inline VQA
    └── "Provenance"     → ProvenancePanel
```

---

## 5. Deployment Architecture (MVP)

```
┌─────────────────────────────────────┐
│          Single Machine             │
│                                     │
│  ┌───────────┐    ┌──────────────┐  │
│  │  Vite     │    │   FastAPI    │  │
│  │  Dev      │───▶│   (uvicorn) │  │
│  │  Server   │    │   Port 8000 │  │
│  │  Port 5173│    └──────┬───────┘  │
│  └───────────┘           │          │
│                    ┌─────┴──────┐   │
│                    │  SQLite    │   │
│                    │  FAISS     │   │
│                    │  Models    │   │
│                    │  (files)   │   │
│                    └────────────┘   │
│                                     │
│  No Docker, no external services    │
│  Everything runs locally            │
└─────────────────────────────────────┘
```

---

## 6. Key Design Principles

1. **Search-first product** — the homepage is a search engine, not a chatbot
2. **Models behind interfaces** — swap CLIP for any other model without touching search logic
3. **Metadata separate from vectors** — FAISS stores geometry, SQLite stores meaning
4. **Provenance by default** — every operation recorded automatically
5. **Offline by design** — no external API calls at runtime
6. **Deterministic where possible** — pixel-diff change detection needs no training data
7. **Incremental by design** — never rebuild the full index for new data
8. **Modular pipeline** — each stage (ingest → embed → index → search → change) is independently testable

---

## 7. Technology Stack Summary

| Layer | Technology | Rationale |
|---|---|---|
| Backend framework | FastAPI | Async, fast, good DX, auto-docs |
| Frontend framework | React + Vite | Fast builds, good ecosystem |
| Frontend styling | Tailwind CSS | Rapid UI development |
| Database | SQLite | Zero-config, file-based, offline |
| Vector search | FAISS | Standard, fast, local |
| Embeddings | CLIP ViT-B/32 | Shared image-text space, MIT license |
| Raster I/O | rasterio + GDAL | Industry standard for EO |
| Numerical | NumPy, scikit-image | Standard scientific Python |
| ML framework | PyTorch | CLIP dependency |
| Image processing | Pillow, OpenCV | Standard image ops |

---

## 8. Security & Access (MVP)

- Single-user desktop application for MVP
- No authentication in MVP
- SQLite file permissions for data protection
- No network exposure beyond localhost
- No cloud storage or transmission
