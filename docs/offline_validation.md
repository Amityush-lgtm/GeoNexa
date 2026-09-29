# Offline Validation & Air-Gap Compliance

> **Platform:** GeoNexa — Semantic Earth Observation Search & Intelligence Platform  
> **Target Problem Statement:** SIH26227 — Semantic Retrieval and Multi-Temporal Change Analysis of Satellite Imagery  

---

## 1. Offline Readiness Architecture

GeoNexa is engineered for operational deployment in secure, air-gapped on-premises computing environments. It operates with zero external network connectivity.

### Compliance Checklist

| Subsystem | Requirement | Implementation in GeoNexa | Status |
|---|---|---|---|
| **Embeddings** | No runtime weight downloads or external inference APIs | Loads local `RemoteCLIP-ViT-B-32.pt` checkpoint directly via OpenCLIP | **PASS** |
| **Vector Index** | Local persistence and sub-millisecond search | Memory-mapped local FAISS `IndexFlatIP` | **PASS** |
| **Spatiotemporal DB** | Zero external database server dependencies | Local SQLite engine with WAL mode (`metadata.db`) | **PASS** |
| **Imagery Storage** | Offline local GeoTIFF tiles & manifests | Stored under `data/public/tiles` with `scenes.csv` | **PASS** |
| **Frontend/Backend** | Standalone local execution | Uvicorn (FastAPI) + Vite Static Bundle | **PASS** |

---

## 2. Automated Offline Validation Script

Run the verification suite:

```bash
python scripts/check_offline.py
```

### Validation Procedure:
1. Validates that `OFFLINE_MODE=true` is set in configuration.
2. Checks that `models/remoteclip-vit-b-32/` contains valid weights.
3. Performs a mock forward pass on CPU/CUDA with network disconnected.
4. Checks that FAISS index file exists and is loadable.
5. Verifies that SQLite database is accessible.
6. Verifies that real satellite tiles exist and are readable by `rasterio`.
7. Asserts zero outgoing network sockets during test query execution.
