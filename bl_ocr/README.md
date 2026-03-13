# Bill of Lading OCR Demo

สกัดข้อมูลจาก Bill of Lading PDF ด้วย Vision LLM ทำงานบนเครื่องผ่าน Ollama

## ติดตั้ง

```bash
# สร้าง venv และติดตั้ง dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## วิธีรัน

```bash
# Terminal 1 — เริ่ม Ollama
ollama serve

# Terminal 2 — เริ่ม Web App
source .venv/bin/activate
python app.py
```

เข้าใช้งานที่ http://localhost:7860

## Pipeline Diagram

```
PDF File
   │
   ▼
Docling DocumentConverter
(generate_page_images=True, scale=2.0)
   │
   ▼
list[PIL.Image]  (~200 DPI per page)
   │
   ▼ (for each page)
base64 encode → POST /api/chat (Ollama)
   │            model: qwen2.5vl:7b-q4_K_M
   ▼
Markdown section per page
   │
   ▼
รวมทุก section → {filename}_extracted.md
```

## ตัวแปรที่ปรับได้ (ใน `pipeline.py`)

| ตัวแปร | ค่าเริ่มต้น | คำอธิบาย |
|---|---|---|
| `IMAGES_SCALE` | `2.0` | ความละเอียด DPI (1.0 = 96 DPI, 2.0 = 192 DPI) |
| `OLLAMA_TIMEOUT` | `600` | timeout ต่อหน้า (วินาที) |
| `MODEL_NAME` | `qwen2.5vl:7b-q4_K_M` | ชื่อ model ใน Ollama |
| `EXTRACT_PROMPT` | *(ดูใน pipeline.py)* | prompt ที่ส่งให้ VLM |
| `num_ctx` | `8192` | context window ของ model |

## Troubleshooting

| ปัญหา | วิธีแก้ |
|---|---|
| `ไม่สามารถเชื่อมต่อ Ollama` | รัน `ollama serve` ใน terminal แยก |
| `ไม่พบ model` | รัน `ollama pull qwen2.5vl:7b-q4_K_M` |
| หน้า PDF ว่างเปล่า | ตรวจสอบว่า PDF ไม่ได้ถูก encrypt |
| ช้ามาก / timeout | เพิ่ม `OLLAMA_TIMEOUT` หรือลด `IMAGES_SCALE` |
| GPU ไม่ถูกใช้งาน | ตรวจสอบ CUDA driver: `nvidia-smi` |
