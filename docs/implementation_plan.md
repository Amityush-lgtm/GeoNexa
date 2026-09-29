# Implementation Plan — Semantic EO Search

> **Project:** SIH26227 — Semantic Retrieval and Multi-Temporal Change Analysis of Satellite Imagery
> **Version:** 0.1.0-plan
> **Date:** 2026-09-29

---

## 1. Problem Interpretation

### What the PS asks for

An **offline, on-premises Earth Observation search and analysis platform** that allows an intelligence analyst to:

1. **Search** a local satellite-imagery archive using **natural language** and **image similarity**.
2. **Discover** relevant locations ranked by semantic relevance.
3. **Investigate** what is visible at a location (VQA).
4. **Analyze change** over time with false-alarm suppression.
5. **Find similar** locations via embedding-based discovery.
6. **Trace provenance** — every result must be explainable and auditable.

### Core product identity

| NOT this | THIS |
|---|---|
| Generic chatbot | Semantic satellite search engine |
| "Upload and ask" tool | Search → Discover → Investigate workflow |
| Cloud-dependent SaaS | Fully offline after setup |
| Pixel-diff change detector | Confidence-aware change analysis |

### Mandatory vs optional

| Mandatory (P0) | Optional (P1) | Future (P2) |
|---|---|---|
| Local GeoTIFF ingestion + tiling | Change-type classification | Distributed indexing |
| Metadata extraction & storage | Analyst confirm/reject workflow | Multi-sensor fusion |
| Local image + text embeddings | Clustering / discovery | Sophisticated rerankers |
| FAISS vector index | Map interaction | Enterprise deployment |
| Natural-language semantic search | Report export (PDF) | Many change classes |
| Image-to-image similarity | Feedback / reranking | |
| Metadata filtering (date, sensor, AOI) | | |
| Temporal retrieval | | |
| Basic change detection | | |
| False-alarm / confounder handling | | |
| Earliest supported observation | | |
| Provenance records | | |
| Investigation page | | |
| Incremental ingestion | | |
| Offline operation | | |

---

## 2. System Architecture

### High-level

```
                    ┌──────────────────────┐
                    │    React Frontend    │
                    │ Search / Map / Review│
                    └──────────┬───────────┘
                               │ HTTP / REST
                               ▼
                    ┌──────────────────────┐
                    │       FastAPI        │
                    │      API Gateway     │
                    └──────────┬───────────┘
                               │
         ┌─────────────────────┼──────────────────────┐
         │                     │                      │
         ▼                     ▼                      ▼
   Archive Service       Retrieval Service      Change Service
   (Ingest/Tile/Meta)   (Embed/Search/Filter)  (Temporal/Detect)
         │                     │                      │
         ▼                     ▼                      ▼
     rasterio              CLIP Model            Change Engine
     tile builder          FAISS Index           Quality Checks
         │                     │                      │
         └─────────────────────┼──────────────────────┘
                               ▼
                    ┌──────────────────────┐
                    │   SQLite + FAISS     │
                    │ Metadata / Vectors   │
                    └──────────────────────┘
```

### Data flow

```
INPUT SCENE (GeoTIFF)
    ↓
VALIDATION (format, CRS, bands)
    ↓
METADATA EXTRACTION (date, sensor, bounds, CRS)
    ↓
QUALITY CHECK (basic readability, band count)
    ↓
TILING (256×256 or 512×512 chips with overlap)
    ↓
IMAGE EMBEDDING (CLIP ViT-B/32 or similar)
    ↓
VECTOR INDEX (FAISS IndexFlatIP)
    ↓
METADATA DB (SQLite)
    ↓
PROVENANCE RECORD
    ↓
MANIFEST (content hash + embedding version)
```

---

## 3. Module Breakdown

### Backend modules

| Module | Responsibility |
|---|---|
| `app.archive.ingestion` | Scene validation, metadata extraction, tiling |
| `app.archive.tiler` | GeoTIFF → chips with georeference preservation |
| `app.archive.metadata` | Metadata parsing + SQLite persistence |
| `app.embeddings.model` | Abstract `EmbeddingModel` interface |
| `app.embeddings.clip_model` | CLIP-based image/text encoder |
| `app.retrieval.vector_store` | FAISS wrapper (add/search/save/load) |
| `app.retrieval.search` | Semantic search pipeline (embed → search → filter → rank) |
| `app.retrieval.similarity` | Image-to-image search |
| `app.change.temporal` | Temporal observation retrieval + spatial correspondence |
| `app.change.detector` | Change detection pipeline |
| `app.change.quality` | Quality checks, confounder scoring |
| `app.change.confidence` | Confidence scoring for changes |
| `app.provenance.tracker` | Provenance record creation + storage |
| `app.query.router` | Task classification (search/similar/change/VQA/provenance) |
| `app.vqa.engine` | Visual question answering (optional, P1) |
| `app.api.*` | FastAPI route handlers |
| `app.models.*` | Pydantic schemas |
| `app.services.*` | Service orchestration layer |
| `app.db` | SQLite connection + schema management |

### Frontend pages

| Page | Purpose |
|---|---|
| Search | Homepage — semantic search with filters |
| Results | Ranked tile cards |
| Investigation | Selected tile detail + actions |
| Change | Before/after/change-map view |
| Similar | Similar-site results |
| Provenance | Trace viewer |
| Archive | Archive stats + management |
| History | Past queries + analyst decisions |

---

## 4. Data Model

### SQLite Schema

```sql
-- Source scenes
CREATE TABLE scenes (
    scene_id        TEXT PRIMARY KEY,
    file_path       TEXT NOT NULL,
    sensor          TEXT,
    acquisition_date TEXT,
    crs             TEXT,
    bounds_minx     REAL,
    bounds_miny     REAL,
    bounds_maxx     REAL,
    bounds_maxy     REAL,
    width           INTEGER,
    height          INTEGER,
    band_count      INTEGER,
    file_size_bytes INTEGER,
    ingested_at     TEXT NOT NULL,
    processing_version TEXT
);

-- Tiles / chips
CREATE TABLE tiles (
    tile_id         TEXT PRIMARY KEY,
    scene_id        TEXT NOT NULL REFERENCES scenes(scene_id),
    file_path       TEXT NOT NULL,
    x_index         INTEGER,
    y_index         INTEGER,
    crs             TEXT,
    bounds_minx     REAL,
    bounds_miny     REAL,
    bounds_maxx     REAL,
    bounds_maxy     REAL,
    center_lat      REAL,
    center_lon      REAL,
    width           INTEGER,
    height          INTEGER,
    band_count      INTEGER,
    created_at      TEXT NOT NULL
);

-- Embedding records
CREATE TABLE embeddings (
    embedding_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    tile_id         TEXT NOT NULL REFERENCES tiles(tile_id),
    model_name      TEXT NOT NULL,
    model_version   TEXT NOT NULL,
    vector_dim      INTEGER NOT NULL,
    faiss_index_id  INTEGER NOT NULL,
    created_at      TEXT NOT NULL
);

-- Index manifest (incremental ingestion)
CREATE TABLE index_manifest (
    tile_id         TEXT NOT NULL,
    content_hash    TEXT NOT NULL,
    embedding_model TEXT NOT NULL,
    embedding_version TEXT NOT NULL,
    indexed_at      TEXT NOT NULL,
    PRIMARY KEY (tile_id, embedding_model)
);

-- Change analyses
CREATE TABLE change_analyses (
    analysis_id     TEXT PRIMARY KEY,
    tile_id         TEXT NOT NULL,
    t1_tile_id      TEXT,
    t2_tile_id      TEXT,
    change_type     TEXT,
    confidence      REAL,
    structural_confidence REAL,
    seasonal_confound     REAL,
    cloud_contamination   REAL,
    earliest_supported    TEXT,
    change_mask_path      TEXT,
    status          TEXT DEFAULT 'pending',
    created_at      TEXT NOT NULL,
    completed_at    TEXT
);

-- Analyst reviews
CREATE TABLE analyst_reviews (
    review_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_id     TEXT REFERENCES change_analyses(analysis_id),
    tile_id         TEXT,
    decision        TEXT CHECK(decision IN ('confirmed', 'rejected', 'uncertain')),
    notes           TEXT,
    analyst         TEXT,
    created_at      TEXT NOT NULL
);

-- Provenance records
CREATE TABLE provenance_records (
    provenance_id   TEXT PRIMARY KEY,
    entity_type     TEXT NOT NULL,  -- 'search', 'change', 'similarity', 'vqa'
    entity_id       TEXT,
    query_text      TEXT,
    query_tile_id   TEXT,
    embedding_model TEXT,
    embedding_version TEXT,
    processing_version TEXT,
    parameters      TEXT,          -- JSON
    result_summary  TEXT,          -- JSON
    confidence      REAL,
    created_at      TEXT NOT NULL
);

-- Search / query audit log
CREATE TABLE query_log (
    query_id        TEXT PRIMARY KEY,
    query_type      TEXT NOT NULL,  -- SEMANTIC_SEARCH, IMAGE_SIMILARITY, etc.
    query_text      TEXT,
    query_tile_id   TEXT,
    filters         TEXT,          -- JSON
    result_count    INTEGER,
    latency_ms      REAL,
    created_at      TEXT NOT NULL
);
```

---

## 5. API Contracts

### Archive

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/archive/ingest` | Ingest a single scene |
| POST | `/api/archive/ingest/batch` | Ingest multiple scenes |
| GET | `/api/archive/stats` | Archive statistics |
| GET | `/api/archive/tiles/{tile_id}` | Get tile metadata + image |
| GET | `/api/archive/tiles/{tile_id}/image` | Get tile image (PNG/JPEG) |
| GET | `/api/archive/scenes` | List scenes |

### Search

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/search` | Semantic text search |
| POST | `/api/search/similar` | Image-to-image similarity |

#### POST /api/search — Request

```json
{
  "query": "newly built structures near a river",
  "bbox": [lon_min, lat_min, lon_max, lat_max],
  "date_from": "2026-01-01",
  "date_to": "2026-06-30",
  "sensor": "Sentinel-2",
  "top_k": 20
}
```

#### POST /api/search — Response

```json
{
  "query_id": "q-abc123",
  "results": [
    {
      "tile_id": "S2_20260418_001_x04_y08",
      "similarity": 0.87,
      "image_url": "/api/archive/tiles/S2_20260418_001_x04_y08/image",
      "location": {"lat": 28.61, "lon": 77.23},
      "bbox": [77.20, 28.59, 77.26, 28.63],
      "date": "2026-04-18",
      "sensor": "Sentinel-2",
      "scene_id": "S2_20260418_001",
      "provenance_id": "prov-xyz"
    }
  ],
  "total": 15,
  "latency_ms": 142
}
```

### Change

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/change/analyze` | Run change analysis |
| GET | `/api/change/{analysis_id}` | Get analysis result |
| GET | `/api/change/temporal/{tile_id}` | Get temporal observations |

### Query Router

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/query` | Route a natural-language query |

### Provenance

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/provenance/{id}` | Get provenance record |

### System

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/health` | Health + offline readiness check |

---

## 6. Embedding Strategy

### Primary model: CLIP (ViT-B/32)

**Rationale:**
- Supports both image and text encoding in a shared embedding space
- Well-studied, MIT-licensed
- Runs locally on CPU (slower) or GPU
- 512-dimensional vectors — manageable for FAISS
- Works with RGB imagery (we convert multi-band to 3-band for CLIP)

**Abstraction:**

```python
class EmbeddingModel(ABC):
    @abstractmethod
    def encode_image(self, image: np.ndarray) -> np.ndarray: ...

    @abstractmethod
    def encode_text(self, text: str) -> np.ndarray: ...

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

**Fallback models:**
- OpenCLIP ViT-B/32 (if standard CLIP unavailable)
- SigLIP (if higher quality needed and resources permit)

**Band handling:**
- For multi-band imagery (>3 bands), select RGB bands or use a configurable band mapping
- Normalize to 0–255 uint8 before CLIP preprocessing
- Document band selection in provenance

### Model storage

```
models/
    clip-vit-b-32/
        config.json
        model.safetensors (or pytorch_model.bin)
        preprocessor_config.json
        tokenizer.json
        LICENSE
```

All weights downloaded once during setup; no internet needed at runtime.

---

## 7. Vector-Search Strategy

### FAISS configuration

- **Index type:** `IndexFlatIP` (inner product on L2-normalized vectors = cosine similarity)
- **Dimensionality:** 512 (CLIP ViT-B/32)
- **Normalization:** All vectors L2-normalized before insertion
- **ID mapping:** FAISS internal sequential IDs mapped to `tile_id` via SQLite

### Operations

| Operation | Method |
|---|---|
| Add vectors | `index.add(vectors)` |
| Search | `index.search(query_vector, k)` |
| Save | `faiss.write_index(index, path)` |
| Load | `faiss.read_index(path)` |
| Size | `index.ntotal` |

### Scale considerations

- For MVP (500 tiles × 512 dims × 4 bytes) = ~1 MB — `IndexFlatIP` is fine
- For 100K+ tiles: migrate to `IndexIVFFlat` or `IndexHNSW`
- Incremental add: FAISS `IndexFlatIP` supports `index.add()` without rebuild

### Metadata-vector relationship

```
FAISS index position (integer) ←→ embeddings.faiss_index_id ←→ tiles.tile_id
```

Post-retrieval metadata filtering:
1. FAISS returns top-K×2 candidates
2. Filter by date, sensor, bbox in SQLite
3. Return top-K after filtering

---

## 8. Temporal / Change Strategy

### Temporal index

For any tile, find co-located tiles across time:

1. **Spatial correspondence:** Query SQLite for tiles whose bounding boxes overlap with the target tile (IoU > threshold or centroid distance < threshold)
2. **Temporal ordering:** Sort matched tiles by `acquisition_date`
3. **Result:** Ordered list of observations for the same location

### Change detection pipeline

```
T1 (earlier)   T2 (later)
      ↓              ↓
  Load raster    Load raster
      ↓              ↓
  Quality check  Quality check
      ↓              ↓
  ────── Co-registration ──────
              ↓
      Radiometric normalization
              ↓
      Difference computation
              ↓
      Threshold / segmentation
              ↓
      Change mask
              ↓
      Confidence scoring
              ↓
      Evidence generation
```

### MVP change detection approach

1. **Pixel-level difference** in normalized band values
2. **Morphological filtering** to remove salt-and-pepper noise
3. **Connected component analysis** for change regions
4. **Size filtering** — ignore regions below minimum area
5. **Confidence scoring** based on magnitude + persistence

### Earliest supported observation

Given a temporal stack for a location:

```python
for t in reversed(sorted_observations):
    if change_detected(t, t_reference):
        earliest = t
    else:
        break
return earliest
```

Report as: *"Earliest supported observation in the indexed archive: {date}"*

---

## 9. False-Alarm Suppression Strategy

### Confounder categories

| Confounder | Detection method | Mitigation |
|---|---|---|
| Cloud/haze | Band ratio thresholds, brightness | Mask cloudy pixels, reduce confidence |
| Seasonal vegetation | NDVI comparison | Seasonal-confound score |
| Shadow | Low-illumination detection | Shadow mask, reduce confidence |
| Illumination angle | Metadata sun-elevation | Normalize or flag |
| Co-registration error | Feature matching quality | Registration quality score |
| Radiometric inconsistency | Histogram comparison | Normalization |
| Snow | Brightness + NDSI if bands available | Snow mask |

### Confidence model

```python
confidence = ConfidenceScore(
    structural=0.0–1.0,      # magnitude of detected change
    seasonal_confound=0.0–1.0, # risk of seasonal false alarm
    cloud_contamination=0.0–1.0, # cloud/haze presence
    registration_quality=0.0–1.0, # co-registration quality
    persistence=0.0–1.0       # change visible across multiple dates
)

final_confidence = (
    structural * w1
    - seasonal_confound * w2
    - cloud_contamination * w3
    - (1 - registration_quality) * w4
    + persistence * w5
)
```

Weights tuned on validation cases; documented in `docs/confidence_model.md`.

---

## 10. Provenance Strategy

Every system output (search result, change analysis, similarity result, VQA answer) generates a provenance record:

```json
{
  "provenance_id": "prov-abc123",
  "entity_type": "search",
  "query_text": "newly built structures near a river",
  "embedding_model": "clip-vit-b-32",
  "embedding_version": "openai-clip-vit-b-32-v1",
  "processing_version": "semantic-eo-search-0.1.0",
  "parameters": {
    "top_k": 20,
    "filters": {"date_from": "2026-01-01"}
  },
  "result_summary": {
    "total_results": 15,
    "top_similarity": 0.87
  },
  "created_at": "2026-09-29T23:00:00Z"
}
```

Stored in SQLite `provenance_records` table.

**Principle:** An evaluator should be able to trace any result back to:
- the query that produced it
- the model that encoded it
- the index that matched it
- the tile and scene it came from
- the confidence and processing parameters

---

## 11. Offline Strategy

### Startup readiness check

```python
def check_offline_readiness() -> dict:
    checks = {
        "model_weights": path_exists(CLIP_MODEL_PATH),
        "embedding_model": model_loadable(CLIP_MODEL_PATH),
        "vector_index": path_exists(FAISS_INDEX_PATH),
        "sqlite_database": path_exists(SQLITE_DB_PATH),
        "change_model": True,  # using deterministic pipeline
        "datasets": count_tiles() > 0,
        "external_api_required": False,
    }
    return checks
```

### Configuration

```env
OFFLINE_MODE=true
MODEL_PATH=./models/clip-vit-b-32
FAISS_INDEX_PATH=./indexes/main.index
DATABASE_PATH=./data/archive/metadata.db
DATA_DIR=./data/archive
```

### Model download script

```bash
python scripts/download_models.py
# Downloads CLIP weights to models/ — run once with internet
```

After this, no internet is needed.

---

## 12. Testing Strategy

### Unit tests

| Area | Tests |
|---|---|
| Ingestion | Valid GeoTIFF, invalid file, corrupt file, missing CRS |
| Metadata | Extraction accuracy, date parsing, CRS handling |
| Tiling | Correct count, overlap, georeference preservation |
| Embeddings | Output shape, normalization, determinism |
| Vector store | Add, search, save/load, ID mapping |
| Search | Ranked results, filtering, top-k |
| Similarity | Image-to-image returns relevant results |
| Temporal | Correct co-location, ordering |
| Change | Known positive, known negative, confounder case |
| Confidence | Score computation, boundary cases |
| Incremental | New tile added, unchanged skipped, modified reprocessed |
| Provenance | Record created for every operation |

### Integration tests

- Full pipeline: ingest → embed → search → result
- Change pipeline: select tile → temporal → detect → evidence
- Incremental: add tiles → verify skip → add new → verify indexed

### Test data

- 5–10 synthetic or real GeoTIFFs in `data/samples/`
- Known-change pair (before/after)
- Known no-change pair
- Seasonal-variation pair (false alarm test)

---

## 13. Evaluation Strategy

### Scripts

- `scripts/evaluate_retrieval.py` — measures search quality + latency
- `scripts/evaluate_change.py` — measures change detection accuracy

### Metrics to track

| Category | Metric |
|---|---|
| Archive | Number of scenes, tiles, total size |
| Index | FAISS index size, build time |
| Ingestion | Incremental ingestion time per tile |
| Search | Average query latency, p95 latency |
| Search quality | Subjective relevance (manual for MVP) |
| Change | True positive rate, false positive rate (on test set) |
| Change | Latency per analysis |
| System | Hardware used, model used |

### Output

```
reports/
    retrieval_evaluation_YYYYMMDD.json
    change_evaluation_YYYYMMDD.json
    system_metrics_YYYYMMDD.json
```

**Rule:** No fabricated numbers. If we don't have ground truth, we report what we can measure (latency, counts) and note qualitative observations.

---

## 14. Exact MVP Scope

### In scope (build this)

1. GeoTIFF ingestion pipeline (single + batch)
2. 256×256 tiling with overlap
3. CLIP ViT-B/32 local embeddings
4. FAISS IndexFlatIP
5. SQLite metadata store
6. Natural-language semantic search with ranking
7. Metadata filtering (date, sensor, bbox)
8. Image-to-image similarity search
9. Temporal observation retrieval
10. Basic pixel-difference change detection with morphological filtering
11. Confidence scoring (structural + confounder)
12. Earliest supported observation
13. Provenance records for all operations
14. Incremental ingestion with content hashing
15. Offline readiness check
16. React frontend: search, results, investigation, change view
17. 5+ demo cases
18. Evaluation scripts

### Out of scope for MVP

- Map interaction (P1)
- VQA with VLM (P1 — stub the endpoint)
- Analyst confirm/reject persistence (P1 — UI buttons present, minimal backend)
- Report export (P1)
- Clustering (P1)
- Advanced change-type classification (P1)
- Distributed indexing (P2)

---

## 15. Implementation Sequence

| Phase | Duration (est.) | Deliverable |
|---|---|---|
| 0. Architecture | 1–2 hours | This plan, architecture doc, README |
| 1. Data layer | 3–4 hours | Ingestion, tiling, metadata, SQLite schema |
| 2. Embeddings | 2–3 hours | CLIP model wrapper, embedding generation |
| 3. Search | 3–4 hours | FAISS index, semantic search, similarity, filtering |
| 4. Temporal + Change | 4–5 hours | Temporal index, change detection, confidence |
| 5. API | 3–4 hours | FastAPI endpoints, query router |
| 6. Frontend | 6–8 hours | Search, results, investigation, change views |
| 7. Incremental | 2–3 hours | Content hashing, manifest, partial updates |
| 8. Evaluation | 2–3 hours | Benchmark scripts, demo cases |
| 9. Polish | 3–4 hours | Error handling, loading states, provenance UI |

**Total estimated: ~30–40 hours of focused work**

---

## 16. Technical Risks

| Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|
| CLIP embedding quality on satellite imagery | Medium | Medium | Test early; swap to RemoteCLIP or SatCLIP if available |
| GPU not available on demo hardware | High | Medium | Ensure CPU inference works (slower but functional) |
| Large GeoTIFF memory issues | Medium | Low | Stream-read with rasterio windowed reads |
| FAISS search too slow at scale | Low | Low | MVP is small; upgrade index type if needed |
| Change detection too noisy | High | Medium | Conservative thresholds; multi-date persistence requirement |
| Co-registration errors | Medium | Medium | Simple feature-based alignment; quality score |
| No good test dataset available | High | Medium | Generate synthetic scenes or use Sentinel-2 L2A samples |
| Frontend complexity delays backend work | Medium | High | Build minimal UI; focus on backend pipelines |

---

## 17. Fallback Plans

| Scenario | Fallback |
|---|---|
| CLIP doesn't work well on EO imagery | Use RemoteCLIP, or fine-tuned CLIP variant, or SigLIP |
| No GPU available | CPU inference with batch size 1; pre-compute all embeddings |
| GeoTIFF library issues on target OS | Use GDAL directly via subprocess if rasterio fails |
| FAISS installation fails | Use scikit-learn NearestNeighbors (slower but functional) |
| VLM too large to run locally | Stub VQA endpoint; demonstrate with pre-computed answers |
| Change detection too many false alarms | Increase thresholds; require multi-date persistence |
| Dataset not available | Create synthetic GeoTIFFs with known properties |
| Time runs out | Prioritize search pipeline (P0 items 1–10); skip change/provenance polish |

---

## Decision Log

| Decision | Rationale |
|---|---|
| CLIP ViT-B/32 as primary model | Balance of quality, speed, and license; shared image-text space |
| FAISS IndexFlatIP | Exact search is fine for MVP scale; no parameter tuning needed |
| SQLite over Postgres | Zero-config, file-based, perfect for offline/hackathon |
| 256×256 tiles | Matches CLIP input (224→resize); reasonable spatial extent |
| Pixel-diff + morphology for change | Deterministic, explainable, no training data needed |
| React + Vite frontend | Fast dev, good ecosystem, team familiarity |
| Content hashing for incremental | Simple, reliable, no external dependencies |
