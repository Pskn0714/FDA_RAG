#!/usr/bin/env python3
"""
ขั้นที่ 1 — แตก chunk จากไฟล์ JSON ที่ผ่าน OCR แล้ว

อ่าน:  JSONforOCR/<หมวด>/*.json   (fileName, sourceUrl, text)
เขียน: data/chunks.jsonl

แบ่งตามโครงสร้าง "ข้อ" / "มาตรา" ถ้าหาไม่เจอจะซอยตามย่อหน้าแทน

ใช้งาน: python 1_chunk.py
"""

import json
import re
from pathlib import Path
from urllib.parse import urlparse, parse_qs

SRC_DIR = Path("JSONforOCR")
OUT_DIR = Path("data")
OUT_FILE = OUT_DIR / "chunks.jsonl"

MAX_CHARS = 1200     # ข้อไหนยาวเกินนี้ ซอยย่อย
MIN_CHARS = 40       # สั้นกว่านี้ทิ้ง

THAI_DIGITS = str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789")

# ต้องขึ้นต้นบรรทัด + ตามด้วยตัวเลข เพื่อไม่ให้ไปจับคำว่า ข้อมูล / ข้อความ
CLAUSE_RE = re.compile(
    r"(?m)^[ \t\-•]*(ข้อ|มาตรา)[ \t]*([๐-๙\d]+(?:[ \t]*(?:ทวิ|ตรี|จัตวา|เบญจ))?)(?=[ \t\n])"
)


def media_id_of(url):
    return parse_qs(urlparse(url or "").query).get("id", [""])[0]


def normalize(text):
    text = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_long(text, limit):
    """ซอยข้อความยาวตามย่อหน้า ไม่ตัดกลางประโยคถ้าเลี่ยงได้"""
    if len(text) <= limit:
        return [text]
    parts, buf = [], ""
    for para in re.split(r"\n\s*\n", text):
        if len(buf) + len(para) + 2 <= limit:
            buf = f"{buf}\n\n{para}".strip()
        else:
            if buf:
                parts.append(buf)
            while len(para) > limit:
                parts.append(para[:limit])
                para = para[limit:]
            buf = para
    if buf:
        parts.append(buf)
    return parts


def split_by_clause(text):
    """คืน [{clause, body}] — 'หัวประกาศ' คือส่วนก่อนถึงข้อแรก"""
    matches = list(CLAUSE_RE.finditer(text))
    if not matches:
        return [{"clause": "", "body": text}]

    out = []
    head = text[:matches[0].start()].strip()
    if len(head) >= MIN_CHARS:
        out.append({"clause": "หัวประกาศ", "body": head})

    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[m.start():end].strip()
        num = m.group(2).translate(THAI_DIGITS).strip()
        out.append({"clause": f"{m.group(1)} {num}", "body": body})
    return out


def main():
    if not SRC_DIR.exists():
        raise SystemExit(f"ไม่พบโฟลเดอร์ {SRC_DIR}")
    OUT_DIR.mkdir(exist_ok=True)

    files = sorted(SRC_DIR.rglob("*.json"))
    print(f"เจอไฟล์ JSON {len(files)} ไฟล์\n")

    chunks, by_folder = [], {}
    n_empty = n_no_clause = 0

    for path in files:
        try:
            d = json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"  อ่านไม่ได้: {path.name} — {e}")
            continue

        text = normalize(d.get("text", ""))
        if len(text) < MIN_CHARS:
            n_empty += 1
            continue

        folder = path.parent.name if path.parent != SRC_DIR else "(root)"
        by_folder[folder] = by_folder.get(folder, 0) + 1
        title = (d.get("fileName") or path.stem).replace(".pdf", "").strip()
        src = d.get("sourceUrl", "")

        parts = split_by_clause(text)
        if len(parts) == 1 and not parts[0]["clause"]:
            n_no_clause += 1

        for p in parts:
            for piece in split_long(p["body"], MAX_CHARS):
                piece = piece.strip()
                if len(piece) < MIN_CHARS:
                    continue
                chunks.append({
                    "text": piece,
                    "clause": p["clause"],
                    "doc_title": title,
                    "folder": folder,
                    "file_name": path.name,
                    "source_url": src,
                    "media_id": media_id_of(src),
                })

    for i, c in enumerate(chunks):
        c["id"] = f"c{i:06d}"

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    print("ไฟล์ต่อโฟลเดอร์")
    for k, v in sorted(by_folder.items()):
        print(f"   {v:4}  {k}")

    lens = [len(c["text"]) for c in chunks]
    with_clause = sum(1 for c in chunks if c["clause"] not in ("", "หัวประกาศ"))

    print(f"\nสรุป")
    print(f"   ไฟล์ที่ใช้ได้         : {len(files) - n_empty}")
    print(f"   ไฟล์ที่ text ว่าง     : {n_empty}")
    print(f"   ไฟล์ไม่มีโครงสร้าง 'ข้อ': {n_no_clause}  (คู่มือ/ฟอร์ม/ตาราง — ปกติ)")
    print(f"   chunk ทั้งหมด         : {len(chunks)}")
    print(f"   chunk ที่มีเลขข้อ     : {with_clause}")
    if lens:
        print(f"   ความยาว: เฉลี่ย {sum(lens)//len(lens)} | สั้นสุด {min(lens)} | ยาวสุด {max(lens)}")
    print(f"\n-> {OUT_FILE}")

    sample = [c for c in chunks if c["clause"] not in ("", "หัวประกาศ")][:2]
    if sample:
        print("\nตัวอย่าง chunk ที่จับ 'ข้อ' ได้")
        for c in sample:
            print(f"   [{c['clause']}] {c['doc_title'][:50]}")
            print(f"      {c['text'][:120]}...\n")


if __name__ == "__main__":
    main()
