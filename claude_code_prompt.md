# Claude Code Prompt: Bill of Lading OCR Demo

## Project Overview

สร้าง demo โปรแกรม OCR สำหรับ Bill of Lading โดยใช้:
- **Docling** สำหรับ preprocess PDF → page images
- **Qwen2.5-VL-7B Q4_K_M** ผ่าน **Ollama** สำหรับ vision extraction
- **Gradio** สำหรับ Web UI ให้ผู้ใช้เลือกไฟล์ PDF เอง
- Output เป็นไฟล์ **Markdown** ที่มีทุก field จากเอกสาร

---

## Environment & Assumptions

- OS: Nobara Linux (Fedora-based), Python 3.10+
- Ollama ติดตั้งและรันอยู่แล้วที่ `http://localhost:11434`
- Model `qwen2.5vl:7b-q4_K_M` pull ไว้แล้วใน Ollama
- GPU: มี NVIDIA GPU พร้อม CUDA (ใช้สำหรับ Ollama inference)

---

## Task

### 1. สร้าง project structure

```
bl_ocr/
├── app.py            # Gradio web app (main entry point)
├── pipeline.py       # OCR pipeline logic (Docling + Ollama)
├── requirements.txt
└── README.md
```

### 2. `pipeline.py` — OCR Pipeline

สร้าง module ที่มีฟังก์ชันต่อไปนี้:

#### `render_pages(pdf_path: str) -> list[PIL.Image.Image]`
- ใช้ `docling.document_converter.DocumentConverter` แปลง PDF เป็น page images
- ตั้งค่า `PdfPipelineOptions`:
  - `generate_page_images = True`
  - `images_scale = 2.0` (~200 DPI)
- Return list ของ `PIL.Image` เรียงตาม page number

#### `image_to_base64(img: PIL.Image.Image) -> str`
- แปลง PIL Image เป็น base64 string (PNG format)

#### `extract_page(image_b64: str, page_num: int, total_pages: int) -> str`
- เรียก Ollama `/api/chat` endpoint (POST)
- ใช้ model `qwen2.5vl:7b-q4_K_M`
- ส่ง image ใน messages content ตาม Ollama vision format
- Prompt ที่ใช้:
  ```
  You are an expert document analyst specializing in shipping documents.
  Extract ALL information from this Bill of Lading page.
  Include every field, value, address, date, number, and detail visible.
  Format your response as structured Markdown with:
  - Clear section headers (##) for each logical group
  - Field names in **bold** followed by their values
  - Tables for container list and cargo description
  - Do NOT skip any information, even if it looks minor.
  (Page {page_num} of {total_pages})
  ```
- Options: `temperature=0.05`, `num_ctx=8192`, `stream=False`
- Timeout: 600 วินาที
- Return: string ของ extracted markdown

#### `check_ollama() -> tuple[bool, str]`
- GET `/api/tags` เพื่อตรวจสอบว่า Ollama รันอยู่
- ตรวจสอบว่า model ที่ต้องการมีอยู่ใน list
- Return: `(True, "success message")` หรือ `(False, "error message")`

#### `process_pdf(pdf_path: str, progress_callback=None) -> tuple[str, str]`
- Orchestrate ทั้ง pipeline:
  1. เรียก `check_ollama()`
  2. เรียก `render_pages()`
  3. วนลูปแต่ละ page → `extract_page()`
  4. รวม markdown sections ทั้งหมด
  5. บันทึกไฟล์ output ที่ `{original_filename}_extracted.md` ใน directory เดียวกับ input
- Progress callback signature: `callback(ratio: float, message: str)`
- Return: `(full_markdown_string, output_file_path)`

### 3. `app.py` — Gradio Web UI

สร้าง UI ด้วย `gr.Blocks` (theme: `gr.themes.Soft`) ที่มี:

#### Layout:
- **Header**: ชื่อโปรแกรม + stack ที่ใช้ (Docling · Qwen2.5-VL · Ollama)
- **Status bar**: แสดงสถานะ Ollama (check ตอน page load)
- **Left panel** (scale=1):
  - `gr.File` สำหรับอัปโหลด PDF (file_types=[".pdf"])
  - ปุ่ม "เริ่ม Extract" (variant="primary")
  - อธิบาย pipeline สั้นๆ
- **Right panel** (scale=2):
  - `gr.Markdown` สำหรับ preview ผลลัพธ์
  - `gr.File` สำหรับ download (visible=False จนกว่าจะเสร็จ)

#### Behavior:
- กดปุ่ม → เรียก `process_pdf()` พร้อม `gr.Progress`
- แสดง progress message แต่ละขั้นตอน
- เมื่อเสร็จ: แสดง markdown preview + ปุ่ม download ไฟล์ .md
- Error handling: แสดง error message ใน markdown panel

#### Launch:
```python
demo.launch(server_name="0.0.0.0", server_port=7860, inbrowser=True)
```

### 4. `requirements.txt`

```
docling>=2.5.0
gradio>=4.40.0
requests>=2.31.0
Pillow>=10.0.0
```

### 5. `README.md`

สร้าง README ที่มี:
- วิธีติดตั้ง (`pip install -r requirements.txt`)
- วิธีรัน (`ollama serve` + `python app.py`)
- Pipeline diagram (ASCII)
- ตารางตัวแปรที่ปรับได้ (IMAGES_SCALE, OLLAMA_TIMEOUT, prompt, num_ctx)
- Troubleshooting table

---

## Constraints & Notes

- **อย่าใช้** `langchain`, `llama-index` หรือ library wrapper อื่น — ใช้ Ollama REST API โดยตรง
- Docling ใช้สำหรับ render images เท่านั้น ไม่ต้องใช้ built-in text extraction
- Error ทุกอย่างต้อง catch และแสดงใน UI ไม่ให้ crash
- Code ต้องมี type hints และ docstring สั้นๆ ทุกฟังก์ชัน
- ทดสอบว่า import ทั้งหมดถูกต้องก่อน present ไฟล์

---

## Verification Steps

หลังสร้างโค้ดแล้ว ให้ทำสิ่งต่อไปนี้:
1. `python -c "import docling, gradio, requests, PIL"` — ต้องไม่มี error
2. ตรวจสอบ syntax ด้วย `python -m py_compile app.py pipeline.py`
3. แสดงโครงสร้างไฟล์ทั้งหมดที่สร้าง
