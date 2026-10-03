import json
import sqlite3
from pathlib import Path
import numpy as np
import torch
import open_clip
import faiss
from PIL import Image

def main():
    print("[INFO] Initializing fine-tuned RemoteCLIP encoder...")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")

    model_path = Path("models/RemoteCLIP-ViT-B-32-finetuned.pt")
    if not model_path.exists():
        model_path = Path("models/remoteclip-vit-b-32/RemoteCLIP-ViT-B-32.pt")
    
    print(f"Loading weights from: {model_path}")
    model, _, preprocess = open_clip.create_model_and_transforms("ViT-B-32", pretrained=None)
    ckpt = torch.load(str(model_path), map_location=device)
    state_dict = ckpt.get("state_dict", ckpt)
    clean_state_dict = {k.replace("module.", ""): v for k, v in state_dict.items()}
    model.load_state_dict(clean_state_dict, strict=False)
    model.to(device)
    model.eval()
    tokenizer = open_clip.get_tokenizer("ViT-B-32")

    # Connect to DB
    db_path = Path("data/public/metadata/metadata.db")
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    c.execute("SELECT tile_id, file_path, scene_id FROM tiles")
    rows = c.fetchall()
    print(f"Total tiles in DB: {len(rows)}")

    id_to_tile = {}
    vectors = []

    for idx, (tid, fpath, sid) in enumerate(rows):
        img_p = Path(fpath)
        if not img_p.is_absolute():
            img_p = Path("data/public") / fpath
        if not img_p.exists():
            img_p = Path("data/public/tiles") / Path(fpath).name
        if not img_p.exists():
            img_p = Path("data/public/tiles") / f"{tid}.png"
        if not img_p.exists():
            img_p = Path("data/public/tiles") / f"{tid}.jpg"

        if img_p.exists():
            try:
                img = Image.open(img_p).convert("RGB")
                tensor = preprocess(img).unsqueeze(0).to(device)
                with torch.no_grad():
                    vec = model.encode_image(tensor)
                    vec = vec / vec.norm(dim=-1, keepdim=True)
                vectors.append(vec.cpu().numpy().flatten())
                id_to_tile[str(len(vectors) - 1)] = tid
            except Exception as e:
                print(f"Error encoding {tid}: {e}")
        else:
            print(f"Warning: file not found for {tid}: {img_p}")

    vectors_arr = np.array(vectors, dtype=np.float32)
    print(f"[OK] Encoded {len(vectors_arr)} tile vectors of dimension {vectors_arr.shape[1]}")

    index = faiss.IndexFlatIP(512)
    index.add(vectors_arr)

    Path("indexes").mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, "indexes/main.index")
    with open("indexes/main.idmap.json", "w") as f:
        json.dump(id_to_tile, f, indent=2)

    print("[OK] Index written to indexes/main.index and indexes/main.idmap.json")

    # Now let's test queries!
    test_queries = [
        "agricultural fields",
        "urban buildings and residential city",
        "river water and dense green vegetation",
        "solar panels in desert",
        "mangrove forest and tidal waterways",
        "mumbai port coastal ships and ocean"
    ]

    print("\n[TEST] Testing Retrieval Results on Fresh Index:")
    for tq in test_queries:
        prompts = [
            tq,
            f"a satellite photo of {tq}",
            f"satellite imagery showing {tq}",
            f"aerial view of {tq}",
        ]
        tokens = tokenizer(prompts).to(device)
        with torch.no_grad():
            t_vec = model.encode_text(tokens)
            t_vec = t_vec / t_vec.norm(dim=-1, keepdim=True)
            t_vec = t_vec.mean(dim=0, keepdim=True)
            t_vec = (t_vec / t_vec.norm(dim=-1, keepdim=True)).cpu().numpy().astype(np.float32)

        scores, indices = index.search(t_vec, 3)
        print(f"\nQuery: '{tq}'")
        for rank, (idx_found, score) in enumerate(zip(indices[0], scores[0])):
            tid_found = id_to_tile.get(str(idx_found), "UNKNOWN")
            print(f"  #{rank+1}: {tid_found} (Cosine: {score:.4f})")

if __name__ == "__main__":
    main()
