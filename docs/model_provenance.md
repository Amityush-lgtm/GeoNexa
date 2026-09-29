# Model Provenance & Architecture: RemoteCLIP

> **Platform:** GeoNexa — Semantic Earth Observation Search & Intelligence Platform  
> **Model:** RemoteCLIP ViT-B-32  
> **Target Problem Statement:** SIH26227 — Semantic Retrieval and Multi-Temporal Change Analysis of Satellite Imagery  

---

## 1. Model Overview

**RemoteCLIP** is a vision-language foundation model pre-trained specifically on remote sensing image-text datasets for cross-modal Earth Observation retrieval, semantic search, and zero-shot geospatial classification.

- **Primary Repository:** [https://github.com/ChenDelong1999/RemoteCLIP](https://github.com/ChenDelong1999/RemoteCLIP)
- **Paper Reference:** *"RemoteCLIP: A Vision Language Foundation Model for Remote Sensing"*, IEEE Transactions on Geoscience and Remote Sensing (TGRS).
- **Authors:** Fan Liu, Delong Chen, Zhangqingyun Guan, Xiaomin Zhou, Jiale Zhu, Qiaolin Ye, Lixiang Rong, Jun Zhou.
- **Base Architecture:** Vision Transformer `ViT-B-32` (Visual Encoder) + Transformer (Text Encoder).
- **Embedding Vector Dimension:** `512`
- **License:** CC BY-NC-SA 4.0 / Academic & Competition Research.

---

## 2. Technical Architecture & Preprocessing

```
IMAGE PATH (RGB Satellite Tile)
    ↓
Image Preprocessing:
  - Input resolution: 224 x 224 x 3
  - Channel Normalization: Mean = [0.48145466, 0.4578275, 0.40821073]
                          Std  = [0.26862954, 0.26130258, 0.27577711]
  - Bicubic Interpolation
    ↓
ViT-B-32 Visual Transformer (12 layers, 12 attention heads, patch size 32x32)
    ↓
Image Embedding (512-dim)
    ↓
L2 Normalization: v_norm = v / ||v||_2
    ↓
FAISS Index (Inner Product / Cosine Similarity)

--------------------------------------------------------------------------------

TEXT QUERY ("urban buildings near water")
    ↓
Byte-Pair Encoding (BPE) Tokenization (Vocabulary Size: 49,408; Context Length: 77)
    ↓
Text Transformer Encoder (12 layers, 8 attention heads)
    ↓
Text Embedding (512-dim)
    ↓
L2 Normalization: q_norm = q / ||q||_2
    ↓
Cosine Similarity Score = <q_norm, v_norm>
```

---

## 3. Local Model Checkpoint & Offline Enforcement

### Checkpoint File Layout
```
models/
└── remoteclip-vit-b-32/
    ├── RemoteCLIP-ViT-B-32.pt   # PyTorch Model Checkpoint (State Dict)
    ├── config.json              # OpenCLIP ViT-B-32 architecture definition
    └── tokenizer.json / bpe     # Local BPE tokenizer vocabulary
```

### Strict Offline Loading Guarantees
1. **Zero Runtime Downloads:** The model loader in `app.embeddings.clip_model` loads directly from `models/remoteclip-vit-b-32/RemoteCLIP-ViT-B-32.pt`.
2. **Deterministic Failure Policy:** If the local checkpoint file is not found at the configured path, the application raises a clear, descriptive `FileNotFoundError` immediately during startup or readiness check.
3. **No Fallback:** The system strictly prohibits falling back to online OpenAI weights at runtime.
