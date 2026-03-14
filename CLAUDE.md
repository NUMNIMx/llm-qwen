# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Bill of Lading OCR demo that extracts structured information from PDF shipping documents using a local vision LLM stack:

- **Docling** — renders PDF pages to images (not for text extraction)
- **Qwen2.5-VL-7B Q4_K_M via Ollama** — vision LLM for document understanding
- **Gradio** — web UI for file upload and result preview
- Output: structured Markdown files with all document fields extracted

The full specification is in `claude_code_prompt.md`.

## Target Structure

```
bl_ocr/
├── app.py           # Gradio web app (main entry point)
├── pipeline.py      # OCR pipeline (Docling + Ollama REST API)
├── requirements.txt
└── README.md
```

## Commands

```bash
# Install dependencies
pip install -r bl_ocr/requirements.txt

# Verify imports (run before presenting code)
python -c "import docling, gradio, requests, PIL"

# Syntax check
python -m py_compile bl_ocr/app.py bl_ocr/pipeline.py

# Start the app (Ollama must be running first)
ollama serve                    # terminal 1
python bl_ocr/app.py            # terminal 2 — serves at http://localhost:7860
```

## Architecture

### `pipeline.py`
Core OCR logic, no UI dependencies:
- `check_ollama()` — validates Ollama is reachable at `http://localhost:11434` and the required model exists
- `render_pages(pdf_path)` — uses `docling.document_converter.DocumentConverter` with `PdfPipelineOptions(generate_page_images=True, images_scale=2.0)` to get `list[PIL.Image]`
- `image_to_base64(img)` — encodes PIL Image to base64 PNG for Ollama's vision API
- `extract_page(image_b64, page_num, total_pages)` — POSTs to `/api/chat` with model `qwen2.5vl:7b-q4_K_M`, `temperature=0.05`, `num_ctx=8192`, timeout=600s
- `process_pdf(pdf_path, progress_callback)` — orchestrates the pipeline; saves `{filename}_extracted.md` alongside input; returns `(markdown_str, output_path)`

### `app.py`
Gradio `gr.Blocks` UI (Soft theme):
- Status bar showing Ollama connectivity (checked on page load)
- Left panel (scale=1): PDF upload + "เริ่ม Extract" button
- Right panel (scale=2): Markdown preview + hidden download button (shown on completion)
- All errors caught and displayed in the markdown panel — no crashes
- Launches on `0.0.0.0:7860`

## Key Constraints

- **No langchain, llama-index, or LLM wrapper libraries** — use Ollama REST API directly (`requests`)
- Docling is used for PDF→image rendering only, not its built-in text extraction
- All functions require type hints and short docstrings
- Progress callback signature: `callback(ratio: float, message: str)`

## Prerequisites

- Nobara Linux (Fedora-based), Python 3.10+
- Ollama running at `http://localhost:11434`
- Model pre-pulled: `ollama pull qwen2.5vl:7b-q4_K_M`
- NVIDIA GPU with CUDA (for Ollama inference)
