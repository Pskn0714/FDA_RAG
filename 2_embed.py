#!/usr/bin/env python3
"""
ขั้นที่ 2 — สร้าง embedding แล้วเก็บลง ChromaDB (local ไม่ต้องใช้ Docker)

อ่าน:  data/chunks.jsonl
เขียน: data/chroma/

ใช้งาน: python 2_embed.py
"""

import json
from pathlib import Path

import torch
import chromadb
from sentence_transformers import SentenceTransformer

CHUNKS = Path("data/chunks.jsonl")
DB_DIR = Path("data/chroma")
COLLECTION = "fda_law"

MODEL_NAME = "BAAI/bge-m3"   # ถ้า VRAM ไม่พอ เปลี่ยนเป็น intfloat/multilingual-e5-small
BATCH = 8                    # 3050 4GB ใช้ 8 | 8GB เพิ่มเป็น 16 ได้


def build_embed_text(c):
    """เติมชื่อประกาศ + เลขข้อ ไว้ข้างหน้าก่อน embed ช่วยให้ค้นแม่นขึ้น"""
    head = c["doc_title"]
    if c.get("clause") and c["clause"] != "หัวประกาศ":
        head += f" | {c['clause']}"
    return f"{head}\n{c['text']}"


def main():
    if not CHUNKS.exists():
        raise SystemExit("ยังไม่มี data/chunks.jsonl — รัน 1_chunk.py ก่อน")

    chunks = [json.loads(l) for l in CHUNKS.open(encoding="utf-8")]
    print(f"chunk ทั้งหมด {len(chunks)}")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"device: {device}")
    if device == "cuda":
        print(f"        {torch.cuda.get_device_name(0)}")
    else:
        print("        !! ไม่เจอ GPU จะช้ามาก — แนะนำเปลี่ยนเป็น e5-small")

    print(f"โหลดโมเดล {MODEL_NAME} (ครั้งแรกจะดาวน์โหลด รอสักครู่)")
    model = SentenceTransformer(MODEL_NAME, device=device)
    if device == "cuda":
        try:
            model = model.half()
            print("        ใช้ fp16")
        except Exception:
            print("        fp16 ไม่สำเร็จ ใช้ fp32")

    texts = [build_embed_text(c) for c in chunks]

    print("กำลังสร้าง embedding ...")
    emb = model.encode(
        texts,
        batch_size=BATCH,
        show_progress_bar=True,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )
    print(f"เสร็จ — ขนาด {emb.shape}")

    DB_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(DB_DIR))
    try:
        client.delete_collection(COLLECTION)
        print("ลบ collection เดิม")
    except Exception:
        pass

    col = client.create_collection(
        name=COLLECTION, metadata={"hnsw:space": "cosine"}
    )

    def meta_of(c):
        # Chroma รับได้แค่ str / int / float / bool
        return {
            "doc_title": c["doc_title"][:300],
            "clause": c.get("clause") or "-",
            "folder": c.get("folder") or "-",
            "file_name": c.get("file_name") or "-",
            "source_url": c.get("source_url") or "-",
        }

    STEP = 500
    for i in range(0, len(chunks), STEP):
        part = chunks[i:i + STEP]
        col.add(
            ids=[c["id"] for c in part],
            documents=[c["text"] for c in part],
            embeddings=emb[i:i + STEP].tolist(),
            metadatas=[meta_of(c) for c in part],
        )
        print(f"   บันทึกแล้ว {min(i + STEP, len(chunks))}/{len(chunks)}")

    print(f"\nเสร็จสิ้น — collection '{COLLECTION}' มี {col.count()} รายการ")
    print(f"-> {DB_DIR}")


if __name__ == "__main__":
    main()
