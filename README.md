# Bill of Lading OCR

สกัดข้อมูลจากเอกสาร Bill of Lading (ใบตราส่งสินค้า) ในรูปแบบ PDF ให้กลายเป็น Markdown ที่มีโครงสร้าง โดยใช้ Vision LLM ทำงานบนเครื่องแบบ 100% ไม่ส่งข้อมูลออก internet

---

## ผลลัพธ์ที่ได้

นำ PDF ใบตราส่งสินค้าเข้า → ได้ไฟล์ `.md` ที่สกัดข้อมูลทุก field ออกมาเป็นโครงสร้าง เช่น:

```markdown
## Header Information

- **SHIPPER:** TRANG AGRO-INDUSTRY PUBLIC COMPANY LIMITED
- **WAYBILL NUMBER:** THD1461131
- **Vessel:** ZHONG GU RI ZHAO
- **Port of Loading:** LAEM CHABANG, THAILAND
- **Port of Discharge:** CHARLESTON, USA

## Cargo Description

| Container | Seal | Type | Quantity |
|---|---|---|---|
| CMAU2733634 | M4907121 | 20' ST | 180 BALES |
| CMU27484085 | M4907122 | 20' ST | 180 BALES |

- **GROSS WEIGHT:** 40,000 KG
- **MEASUREMENT:** 51.184 CBM
```

---

## วิธีทำงาน (Pipeline)

```
PDF File
   │
   ▼
Docling DocumentConverter
   │  แปลงแต่ละหน้าเป็นภาพ PNG (อยู่ใน RAM)
   │  ไม่ได้อ่าน text — เพราะ BL มักเป็น scanned image
   ▼
list[PIL.Image]  — bitmap ของแต่ละหน้า
   │
   ▼  (ทำซ้ำทีละหน้า)
base64 encode → POST /api/chat → Ollama
   │              model: qwen2.5vl:7b
   │              Qwen อ่านภาพ → เข้าใจ context → สกัดข้อมูล
   ▼
Markdown section ต่อหน้า
   │
   ▼
รวมทุกหน้า → บันทึกเป็น {ชื่อไฟล์}_extracted.md
```

> **ทำไมต้องแปลงเป็นภาพก่อน?**
> Qwen2.5-VL เป็น Vision LLM — รับ input ได้แค่ข้อความและรูปภาพ อ่าน binary ของ PDF โดยตรงไม่ได้
> จึงต้อง render แต่ละหน้าเป็นภาพก่อนส่งให้ model

---

## ความต้องการของระบบ

### Hardware
- **GPU:** NVIDIA พร้อม CUDA (แนะนำ VRAM ≥ 8 GB สำหรับ 7B Q4)
- **RAM:** ≥ 16 GB

### Software
| Software | Version | หมายเหตุ |
|---|---|---|
| OS | Nobara / Fedora Linux | หรือ distro Linux อื่นที่รองรับ CUDA |
| Python | 3.10+ | |
| Ollama | latest | ต้องติดตั้งแยก |
| CUDA Driver | ตามรุ่น GPU | ตรวจสอบด้วย `nvidia-smi` |

---

## ติดตั้ง

### ขั้นตอนที่ 1 — ติดตั้ง Ollama

```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

### ขั้นตอนที่ 2 — ดึง Model

```bash
ollama pull qwen2.5vl:7b
```

> Model มีขนาดประมาณ 5 GB ใช้เวลาดึงตามความเร็ว internet

### ขั้นตอนที่ 3 — ติดตั้ง Python Dependencies

```bash
# สร้าง virtual environment (แนะนำเสมอ — ห้ามติดตั้ง global)
python3 -m venv .venv
source .venv/bin/activate

# ติดตั้ง dependencies
pip install -r bl_ocr/requirements.txt
```

Dependencies ที่จะถูกติดตั้ง:
| Package | Version | บทบาท |
|---|---|---|
| `docling` | ≥2.5.0 | แปลง PDF → PIL Image |
| `Pillow` | ≥10.0.0 | จัดการรูปภาพ, encode base64 |
| `requests` | ≥2.31.0 | เรียก Ollama REST API |
| `tqdm` | ≥4.66.0 | แสดง progress bar |

### ขั้นตอนที่ 4 — ตรวจสอบว่าพร้อมใช้งาน

```bash
# ตรวจสอบ imports
python -c "import docling, requests, PIL, tqdm; print('OK')"

# ตรวจสอบ syntax
python -m py_compile bl_ocr/app.py bl_ocr/pipeline.py && echo "Syntax OK"

# ตรวจสอบ GPU
nvidia-smi
```

---

## วิธีใช้งาน

### เริ่ม Ollama (ต้องทำก่อนเสมอ)

```bash
ollama serve
```

> เปิดทิ้งไว้ใน terminal แยก หรือ run เป็น background service

### รัน OCR

```bash
# เปิด venv ก่อน (ถ้ายังไม่ได้เปิด)
source .venv/bin/activate

# ไปที่โฟลเดอร์โค้ด
cd bl_ocr

# รัน OCR บน PDF
python app.py path/to/document.pdf
```

**ตัวเลือกเพิ่มเติม:**

```bash
# พิมพ์ผลลัพธ์ออกมาบน terminal ด้วย
python app.py document.pdf --print

# บันทึกผลลัพธ์ไปยังโฟลเดอร์ที่ต้องการ
python app.py document.pdf --output-dir /path/to/output/
```

### ผลลัพธ์

ไฟล์ `{ชื่อ PDF}_extracted.md` จะถูกสร้างในโฟลเดอร์เดียวกับ PDF input:

```
document.pdf           ← input
document_extracted.md  ← output (สร้างโดยอัตโนมัติ)
```

---

## โครงสร้างโปรเจค

```
llm-qwen/
├── bl_ocr/
│   ├── app.py           # CLI entry point — รับ argument, แสดง progress bar
│   ├── pipeline.py      # OCR pipeline หลัก — logic ทั้งหมดอยู่ที่นี่
│   ├── requirements.txt
│   └── README.md        # README ย่อ
├── STACK.md             # อธิบาย tech stack และ architecture อย่างละเอียด
└── README.md            # ไฟล์นี้
```

### `pipeline.py` — ฟังก์ชันหลัก

| ฟังก์ชัน | บทบาท |
|---|---|
| `check_ollama()` | ตรวจสอบว่า Ollama รันอยู่และมี model ที่ต้องการ |
| `render_pages(pdf_path)` | แปลง PDF → list ของ PIL.Image ทีละหน้า |
| `image_to_base64(img)` | encode PIL.Image → base64 PNG string |
| `extract_page(image_b64, page_num, total_pages)` | ส่งภาพ 1 หน้าไปให้ Ollama → ได้ Markdown กลับมา |
| `process_pdf(pdf_path, progress_callback)` | orchestrate ทั้ง pipeline, บันทึกผลลัพธ์ |

---

## ปรับแต่งค่า

แก้ได้ที่ต้นไฟล์ `bl_ocr/pipeline.py`:

```python
OLLAMA_URL    = "http://localhost:11434"  # URL ของ Ollama
MODEL_NAME    = "qwen2.5vl:7b"           # ชื่อ model ที่ใช้
IMAGES_SCALE  = 1.0                       # ความละเอียด (1.0 = 96DPI, 2.0 = 192DPI)
OLLAMA_TIMEOUT = 600                      # timeout ต่อหน้า (วินาที)
```

และใน `extract_page()`:

```python
"num_ctx": 4096   # context window — เพิ่มได้ถ้า GPU มี VRAM เพียงพอ
"temperature": 0.05  # ต่ำ = ผลลัพธ์ deterministic มากขึ้น
```

> **เพิ่ม `IMAGES_SCALE`** → ภาพละเอียดขึ้น อ่านตัวเล็กได้ดีขึ้น แต่ใช้ RAM และเวลามากขึ้น
> **ลด `IMAGES_SCALE`** → เร็วขึ้น แต่อาจพลาดตัวอักษรเล็ก

---

## แก้ปัญหาที่พบบ่อย

| ปัญหา | สาเหตุ | วิธีแก้ |
|---|---|---|
| `ไม่สามารถเชื่อมต่อ Ollama` | Ollama ยังไม่ได้รัน | รัน `ollama serve` ในอีก terminal |
| `ไม่พบ model 'qwen2.5vl:7b'` | ยังไม่ได้ดึง model | รัน `ollama pull qwen2.5vl:7b` |
| ไม่มีหน้าใดใน PDF | PDF อาจถูก encrypt หรือ corrupt | ลองเปิด PDF ด้วย PDF viewer ก่อน |
| ช้ามาก / timeout | GPU ไม่ถูกใช้หรือ model ใหญ่เกินไป | ตรวจสอบ `nvidia-smi`, ลด `IMAGES_SCALE` หรือเพิ่ม `OLLAMA_TIMEOUT` |
| GPU ไม่ถูกใช้งาน | CUDA driver ไม่ถูกต้อง | รัน `nvidia-smi` และตรวจสอบว่า Ollama detect GPU ได้ |
| ผลลัพธ์ไม่ครบ | ภาพ resolution ต่ำเกินไป | เพิ่ม `IMAGES_SCALE` เป็น `2.0` |
| RAM หมด | PDF มีหลายหน้ามากและ scale สูง | ลด `IMAGES_SCALE` หรือแยก PDF ก่อน |

---

## ข้อจำกัด

- รองรับเฉพาะ PDF — ไม่รองรับ JPG, PNG โดยตรง (ต้องแปลงเป็น PDF ก่อน)
- เวลาในการประมวลผลขึ้นอยู่กับจำนวนหน้าและ GPU — โดยเฉลี่ยประมาณ 30–120 วินาที/หน้า
- ผลลัพธ์ขึ้นอยู่กับคุณภาพของ PDF ต้นฉบับ — ภาพเบลอหรือตัวเอียงมากอาจส่งผลต่อความแม่นยำ
