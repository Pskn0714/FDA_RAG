#!/usr/bin/env python3
"""
ขั้นที่ 3 — ตัว RAG: ค้นหา + ให้ Typhoon เรียบเรียงคำตอบ

ทดสอบ: python 3_rag.py "ผลิตภัณฑ์เสริมอาหารต้องขออนุญาตอย่างไร"
"""

import os
import sys
from functools import lru_cache
import dotenv
dotenv.load_dotenv()
import torch
import chromadb
from sentence_transformers import SentenceTransformer
from openai import OpenAI

DB_DIR = "data/chroma"
COLLECTION = "fda_law"
MODEL_NAME = "BAAI/bge-m3"          # ต้องตรงกับ 2_embed.py

TYPHOON_BASE = "https://api.opentyphoon.ai/v1"
TYPHOON_MODEL = "typhoon-v2.5-30b-a3b-instruct"

SYSTEM_PROMPT = """คุณเป็นผู้ช่วยตอบคำถามเกี่ยวกับกฎหมายและประกาศด้านอาหารของไทย
(สำนักงานคณะกรรมการอาหารและยา)

กติกาที่ต้องทำตามอย่างเคร่งครัด
1. ตอบจากเอกสารอ้างอิงที่ให้มาเท่านั้น ห้ามใช้ความรู้อื่นนอกเหนือจากนี้
2. ทุกข้อความที่อ้างกฎหมาย ต้องใส่หมายเลขอ้างอิง [1] [2] ตามเอกสารที่ให้มา
3. ถ้าเอกสารที่ให้มาไม่มีข้อมูลเพียงพอ ให้ตอบตรงๆ ว่า
   "ไม่พบข้อมูลที่เกี่ยวข้องในเอกสารที่มีอยู่" แล้วแนะนำให้ติดต่อเจ้าหน้าที่
   ห้ามเดาหรือแต่งข้อมูลขึ้นเอง
4. ตอบเป็นภาษาไทย กระชับ ตรงประเด็น
5. ถ้าเอกสารระบุเลขข้อ ให้อ้างเลขข้อนั้นด้วย
"""


@lru_cache(maxsize=1)
def get_model():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    m = SentenceTransformer(MODEL_NAME, device=device)
    if device == "cuda":
        try:
            m = m.half()
        except Exception:
            pass
    return m


@lru_cache(maxsize=1)
def get_collection():
    return chromadb.PersistentClient(path=DB_DIR).get_collection(COLLECTION)


def search(query, k=5, folder=None):
    vec = get_model().encode(
        [query], normalize_embeddings=True, convert_to_numpy=True
    )[0].tolist()

    where = {"folder": folder} if folder else None
    res = get_collection().query(
        query_embeddings=[vec],
        n_results=k,
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    hits = []
    for doc, meta, dist in zip(
        res["documents"][0], res["metadatas"][0], res["distances"][0]
    ):
        hits.append({"text": doc, "score": round(1 - dist, 4), **meta})
    return hits


def build_context(hits):
    blocks = []
    for i, h in enumerate(hits, 1):
        head = f"[{i}] {h['doc_title']}"
        if h.get("clause") and h["clause"] not in ("-", "หัวประกาศ"):
            head += f" ({h['clause']})"
        blocks.append(f"{head}\n---\n{h['text']}")
    return "\n\n".join(blocks)


def answer(query, k=5, folder=None, api_key=None):
    hits = search(query, k=k, folder=folder)
    if not hits:
        return {"answer": "ไม่พบเอกสารที่เกี่ยวข้อง", "hits": []}

    key = api_key or os.getenv("TYPHOON_API_KEY", "sk-iMO7HbgqNjMae9LPSxhcGm1pXDz0yrYMMoFvGTM6LH3eU0ss")
    if not key:
        return {
            "answer": "(ยังไม่ได้ใส่ TYPHOON_API_KEY — แสดงเฉพาะผลการค้นหาด้านล่าง)",
            "hits": hits,
        }

    client = OpenAI(api_key=key, base_url=TYPHOON_BASE)
    user_msg = f"เอกสารอ้างอิง:\n\n{build_context(hits)}\n\n{'='*40}\nคำถาม: {query}"

    try:
        resp = client.chat.completions.create(
            model=TYPHOON_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.2,
            max_tokens=1000,
        )
        text = resp.choices[0].message.content
    except Exception as e:
        text = f"เรียก Typhoon API ไม่สำเร็จ: {e}"

    return {"answer": text, "hits": hits}


if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) or "ผลิตภัณฑ์เสริมอาหารต้องขออนุญาตอย่างไร"
    print(f"คำถาม: {q}\n")
    r = answer(q, k=5)
    print("=" * 60)
    print(r["answer"])
    print("=" * 60)
    print("\nเอกสารที่ใช้อ้างอิง")
    for i, h in enumerate(r["hits"], 1):
        print(f"  [{i}] {h['score']:.3f} | {h['doc_title'][:55]} ({h.get('clause','-')})")
