#!/usr/bin/env python3
"""
ขั้นที่ 4 — หน้าเว็บ Streamlit

ใช้งาน: streamlit run 4_app.py
"""
import dotenv
dotenv.load_dotenv()
import importlib.util
import os
from pathlib import Path

import streamlit as st

_spec = importlib.util.spec_from_file_location(
    "rag", Path(__file__).parent / "3_rag.py"
)
rag = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rag)

st.set_page_config(page_title="ผู้ช่วยกฎหมายอาหาร อย.", page_icon="📋", layout="wide")

st.title("📋 ผู้ช่วยค้นหากฎหมายอาหาร อย.")
st.caption("ต้นแบบระบบ RAG สำหรับสืบค้นประกาศและกฎหมายอาหาร — Proof of Concept")

with st.sidebar:
    st.header("ตั้งค่า")
    api_key = st.text_input(
        "Typhoon API Key",
        value=os.getenv("TYPHOON_API_KEY", ""),
        type="password",
        help="ไม่ใส่ก็ได้ ระบบจะแสดงเฉพาะผลการค้นหา",
    )
    k = st.slider("จำนวนเอกสารที่ดึงมา", 3, 10, 5)

    st.divider()
    try:
        col = rag.get_collection()
        st.metric("chunk ในฐานข้อมูล", f"{col.count():,}")
        folders = sorted({
            m["folder"] for m in col.get(include=["metadatas"])["metadatas"]
        })
        pick = st.selectbox("จำกัดหมวด", ["(ทุกหมวด)"] + folders)
        folder = None if pick == "(ทุกหมวด)" else pick
    except Exception as e:
        st.error("ยังไม่มีฐานข้อมูล — รัน 1_chunk.py และ 2_embed.py ก่อน")
        st.caption(str(e))
        folder = None

EXAMPLES = [
    "การกล่าวอ้างทางสุขภาพบนฉลากทำได้แค่ไหน",
    "การใช้จุลินทรีย์โพรไบโอติกในอาหารมีเงื่อนไขอะไร",
    "ฉลากโภชนาการต้องแสดงข้อมูลอะไรบ้าง",
    "ภาชนะบรรจุอาหารต้องเป็นไปตามข้อกำหนดใด",
]

st.write("**ตัวอย่างคำถาม**")
cols = st.columns(len(EXAMPLES))
for c, ex in zip(cols, EXAMPLES):
    if c.button(ex, use_container_width=True):
        st.session_state["q"] = ex

query = st.text_input(
    "พิมพ์คำถาม",
    value=st.session_state.get("q", ""),
    placeholder="เช่น ฉลากโภชนาการต้องแสดงข้อมูลอะไรบ้าง",
)

if query.strip():
    with st.spinner("กำลังค้นหาและเรียบเรียงคำตอบ..."):
        result = rag.answer(query, k=k, folder=folder, api_key=api_key or None)

    st.subheader("คำตอบ")
    st.markdown(result["answer"])

    st.divider()
    st.subheader(f"เอกสารอ้างอิง ({len(result['hits'])} รายการ)")

    for i, h in enumerate(result["hits"], 1):
        clause = h.get("clause", "-")
        with st.expander(
            f"[{i}] {h['doc_title'][:70]} — {clause}  (ความคล้าย {h['score']:.3f})"
        ):
            c1, c2 = st.columns(2)
            c1.markdown(f"**หมวด**  \n{h.get('folder','-')}")
            c2.markdown(f"**ตำแหน่งในเอกสาร**  \n{clause}")
            st.text(h["text"])
            url = h.get("source_url", "")
            if url and url != "-":
                st.markdown(f"[เปิดไฟล์ต้นฉบับ]({url})")

st.divider()
st.caption(
    "ระบบนี้เป็นเครื่องมือช่วยค้นหาเบื้องต้น ไม่ใช่คำวินิจฉัยทางกฎหมาย "
    "กรุณาตรวจสอบกับเอกสารต้นฉบับและเจ้าหน้าที่ก่อนนำไปใช้อ้างอิง"
)
