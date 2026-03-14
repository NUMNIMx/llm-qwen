# Tech Stack — Bill of Lading OCR

โปรเจคนี้ทำงาน OCR บนเอกสาร Bill of Lading (ใบตราส่งสินค้า) โดยใช้ Vision LLM แบบ local ทั้งหมด ไม่พึ่งบริการ cloud

---

## ภาพรวม Pipeline

```
PDF → Docling (PDF→Image) → Ollama + Qwen2.5-VL (Vision LLM) → Markdown
```

---

## Components หลัก

### 1. Docling `>=2.5.0`
- **บทบาท:** แปลง PDF เป็นรูปภาพ (render pages)
- **ใช้เฉพาะ:** render PDF → `PIL.Image` เท่านั้น — ไม่ใช้ text extraction ของ Docling
- **Config:** `PdfPipelineOptions(generate_page_images=True, images_scale=1.0)`
- **Class:** `DocumentConverter` + `PdfFormatOption`

#### Docling ต่างจาก PyMuPDF / pdfplumber อย่างไร?

| | PyMuPDF / pdfplumber / pdfminer | Docling |
|---|---|---|
| **วิธีทำงาน** | อ่าน text layer ใน PDF โดยตรง | ใช้ ML model วิเคราะห์ layout ของเอกสาร |
| **ต้องการ text layer?** | ใช่ (ถ้าไม่มีต้องต่อ Tesseract) | ไม่จำเป็น |
| **ผลลัพธ์** | raw text / coordinates | structured document (table, header, figure แยกกัน) |
| **เหมาะกับ** | PDF ที่ embed text ไว้แล้ว | เอกสารซับซ้อน, scanned docs, mixed layout |

**PyMuPDF** ทำงานแบบ "parser" — อ่านข้อมูลที่ PDF เก็บไว้โดยตรง:
```
PDF binary → extract text stream → string
```
เร็วมาก แต่ถ้า PDF เป็น scanned image หรือไม่มี text layer → ได้ข้อมูลว่างเปล่า

**Docling** ทำงานแบบ "document understanding" — ใช้ ML วิเคราะห์ว่าแต่ละส่วนคืออะไร:
```
PDF → render เป็นภาพ → ML layout detection → "นี่คือ table", "นี่คือ header", "นี่คือ paragraph"
```
รู้ structure ของเอกสาร ไม่ใช่แค่ได้ text มา

#### ทำไมถึงใช้ Docling แต่ไม่ใช้ text extraction ของมัน?

Docling มี built-in table detection และ text extraction อยู่แล้ว แต่โปรเจคนี้ตัดส่วนนั้นออก แล้วให้ Qwen2.5-VL ทำแทน เหตุผล:

1. **BL มักเป็น scanned document** — text layer อาจไม่มีหรือเชื่อถือไม่ได้
2. **Qwen2.5-VL เข้าใจ context** — รู้ว่าตัวเลขในช่อง "Weight" คือน้ำหนักสินค้า ไม่ใช่แค่ตัวเลขลอยๆ
3. **Table detection ของ Docling อาจพลาด** ถ้า layout ของ BL ไม่ standard

สรุปการแบ่งหน้าที่:
```
Docling       → PDF → PIL.Image   (render เท่านั้น)
Qwen2.5-VL   → PIL.Image → Markdown  (อ่านและเข้าใจเอกสาร)
```

#### ทำไม Qwen2.5-VL ถึงอ่าน PDF โดยตรงไม่ได้?

Qwen2.5-VL (และ Vision LLM ทั่วไป) รับ input ได้แค่:
- ข้อความ (text prompt)
- รูปภาพ (base64 image)

PDF เป็น binary format ที่ซับซ้อน มี text layer, font embedding, vector graphics, metadata ฯลฯ — LLM ไม่มี parser สำหรับสิ่งนี้ จึงต้องมี Docling เป็นตัวกลางแปลงก่อนเสมอ

```
PDF  →  Docling (render)  →  PNG image (base64)  →  Qwen2.5-VL
        ↑ ขาดตรงนี้ไม่ได้
```

เหมือนกับที่คนเราต้องมีโปรแกรมเปิด PDF ก่อนถึงจะเห็นหน้าเอกสาร — Qwen ก็เช่นกัน "ตาเห็นได้แค่ภาพ" แต่อ่าน binary ของ PDF โดยตรงไม่ได้

### 2. Ollama (local LLM runtime)
- **บทบาท:** รัน Vision LLM บน GPU แบบ local
- **Endpoint:** `http://localhost:11434`
- **API ที่ใช้:** `POST /api/chat` (Ollama REST API)
- **ต้องติดตั้งแยก:** [ollama.ai](https://ollama.ai)

### 3. Qwen2.5-VL 7B (Q4_K_M)
- **บทบาท:** Vision Language Model — อ่านและวิเคราะห์ภาพเอกสาร
- **Model ID:** `qwen2.5vl:7b` (quantized Q4_K_M)
- **Parameters:**
  - `temperature: 0.05` — ผลลัพธ์ deterministic
  - `num_ctx: 4096` — context window
  - timeout: 600 วินาที/หน้า
- **Pull command:** `ollama pull qwen2.5vl:7b-q4_K_M`

### 4. Pillow `>=10.0.0`
- **บทบาท:** จัดการรูปภาพ — encode PIL Image → base64 PNG เพื่อส่งให้ Ollama

### 5. requests `>=2.31.0`
- **บทบาท:** เรียก Ollama REST API โดยตรง
- ไม่ใช้ LLM wrapper library (เช่น langchain, llama-index) — เรียก HTTP ตรง

### 6. tqdm `>=4.66.0`
- **บทบาท:** แสดง progress bar บน CLI

---

## Entry Points

| ไฟล์ | บทบาท |
|---|---|
| `bl_ocr/app.py` | CLI entry point — รับ argument `pdf`, แสดง progress bar |
| `bl_ocr/pipeline.py` | OCR pipeline หลัก — logic ทั้งหมดอยู่ที่นี่ |
| `bl_ocr/requirements.txt` | Python dependencies |

---

## Infrastructure

| Component | รายละเอียด |
|---|---|
| OS | Nobara Linux (Fedora-based) |
| Python | 3.10+ |
| GPU | NVIDIA + CUDA (สำหรับ Ollama inference) |
| Runtime | Ollama ต้องรันก่อนเรียกใช้ app |

---

## Output

- ไฟล์ Markdown (`{filename}_extracted.md`) บันทึกในโฟลเดอร์เดียวกับ PDF input
- แต่ละหน้าแยกด้วย `---` และมี header `# หน้า N`
- ข้อมูลในไฟล์: ทุก field ที่มองเห็นในเอกสาร จัดรูปแบบเป็น section headers, bold fields, และ table

---

## ข้อจำกัดของโปรเจค

- ห้ามใช้ langchain, llama-index หรือ LLM wrapper ใดๆ
- Docling ใช้เพื่อ render เท่านั้น ไม่ใช้ built-in text extraction
- ทุก function ต้องมี type hints และ docstring
