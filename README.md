# FDA_RAG

ระบบ RAG ต้นแบบสำหรับค้นหาและตอบคำถามเกี่ยวกับกฎหมายและประกาศด้านอาหารของ อย.
ถามเป็นภาษาไทยได้ ระบบจะค้นจากประกาศจริง แล้วตอบพร้อมอ้างอิงถึงระดับ **ข้อ** และเปิดไฟล์ PDF ต้นฉบับได้

---

## ต้องเตรียมอะไรบ้าง

| สิ่งที่ต้องมี | หมายเหตุ |
|---|---|
| Python 3.10+ | ทดสอบบน 3.13 |
| Typhoon API Key | สมัครฟรีที่ [opentyphoon.ai](https://opentyphoon.ai) |
| GPU (ถ้ามี) | ไม่มีก็รันได้ แต่ช้ากว่า |

---

## ขั้นตอนติดตั้ง

### 1. โคลนโปรเจค

```bash
git clone https://github.com/Pskn0714/FDA_RAG.git
cd FDA_RAG
```

### 2. ติดตั้งไลบรารี

```bash
pip install sentence-transformers chromadb streamlit openai
```

**ถ้ามี GPU (NVIDIA)** ติดตั้ง PyTorch เวอร์ชัน CUDA ด้วย

```bash
pip install torch --index-url https://download.pytorch.org/whl/cu124
```

เช็คว่าเห็น GPU ไหม

```bash
python -c "import torch; print(torch.cuda.is_available())"
```

ได้ `True` = ใช้ GPU ได้ / ได้ `False` = จะรันบน CPU (ช้ากว่าแต่ใช้ได้)

### 3. โหลดข้อมูล

ไฟล์ข้อมูลใหญ่เกินกว่าจะ push ขึ้น GitHub ให้โหลดจาก Google Drive

**[⬇️ ดาวน์โหลด JSONforOCR.zip](https://drive.google.com/file/d/12I3KZcGiQdLkYP4FXNKbkPZeVYdpAra7/view?usp=drive_link)**

แตกไฟล์แล้ววางโฟลเดอร์ `JSONforOCR` ไว้ใน root ของโปรเจค

```
FDA_RAG/
├── JSONforOCR/          ← วางตรงนี้
│   ├── การกล่าวอ้างทางสุขภาพ/
│   ├── การแสดงฉลากอาหารและฉลากโภชนาการ/
│   ├── การใช้จุลินทรีย์โพรไบโอติกในอาหาร/
│   └── ภาชนะบรรจุ/
├── 1_chunk.py
├── 2_embed.py
├── 3_rag.py
└── 4_app.py
```

### 4. ตั้งค่า API Key

**Windows (cmd)**
```cmd
set TYPHOON_API_KEY=your_key_here
```

**Windows (PowerShell)**
```powershell
$env:TYPHOON_API_KEY = "your_key_here"
```

**Mac / Linux**
```bash
export TYPHOON_API_KEY=your_key_here
```

> ค่านี้อยู่แค่ในหน้าต่าง terminal นั้น ถ้าปิดแล้วเปิดใหม่ต้องตั้งใหม่
> หรือจะไม่ตั้งก็ได้ แล้วไปพิมพ์ในช่องบนหน้าเว็บแทน

---

## วิธีรัน

รันตามลำดับ **1 → 2 → 4**

### 1. แตกข้อความเป็น chunk

```bash
python 1_chunk.py
```

ใช้เวลาไม่กี่วินาที ได้ไฟล์ `data/chunks.jsonl`

### 2. สร้าง embedding

```bash
python 2_embed.py
```

ครั้งแรกจะดาวน์โหลดโมเดล BGE-M3 ประมาณ 2.2GB
จากนั้นใช้เวลา **3-6 นาที (GPU)** หรือ **40-90 นาที (CPU)**

### 3. ทดสอบผ่าน command line (ข้ามได้)

```bash
python 3_rag.py "การกล่าวอ้างทางสุขภาพ หมายความว่าอะไร"
```

### 4. เปิดหน้าเว็บ

```bash
streamlit run 4_app.py
```

เปิดเบราว์เซอร์ที่ `http://localhost:8501`

---

## ข้อจำกัด

- ข้อมูลชุดนี้มีแค่ **4 หมวด 86 ไฟล์** ยังไม่ครอบคลุมกฎหมายอาหารทั้งหมด
- **ยังไม่ได้กรองกฎหมายที่ถูกยกเลิก** — จากการสำรวจเว็บ อย. พบว่ากฎหมาย 1,067 ฉบับ มี 52% ที่ถูกยกเลิกไปแล้ว การกรองด้วยสถานะเป็นงานขั้นต่อไป
- ยังไม่มีการวัดความแม่นยำเชิงตัวเลข

> ระบบนี้เป็นเครื่องมือช่วยค้นหาเบื้องต้น ไม่ใช่คำวินิจฉัยทางกฎหมาย
> กรุณาตรวจสอบกับเอกสารต้นฉบับและเจ้าหน้าที่ก่อนนำไปใช้อ้างอิง
