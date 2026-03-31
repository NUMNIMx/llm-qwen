"""OCR pipeline for Bill of Lading documents using Docling + Ollama."""

import base64
import io
import os
from pathlib import Path
from typing import Callable, Optional

import requests
from PIL import Image

OLLAMA_URL = "http://localhost:11434"
MODEL_NAME = "qwen2.5vl:7b"
IMAGES_SCALE = 2.8
OLLAMA_TIMEOUT = 600

EXTRACT_PROMPT = """\
You are an expert document analyst specializing in shipping documents.
Extract ALL information from this Bill of Lading page.
Include every field, value, address, date, number, and detail visible.
Format your response as structured Markdown with:
- Clear section headers (##) for each logical group
- Field names in **bold** followed by their values
- Tables for container list and cargo description
- Do NOT skip any information, even if it looks minor.
(Page {page_num} of {total_pages})"""


def render_pages(pdf_path: str) -> list[Image.Image]:
    """Convert a PDF file to a list of PIL Images using Docling at ~200 DPI."""
    from docling.document_converter import DocumentConverter
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.datamodel.base_models import InputFormat
    from docling.document_converter import PdfFormatOption

    pipeline_options = PdfPipelineOptions()
    pipeline_options.generate_page_images = True
    pipeline_options.images_scale = IMAGES_SCALE

    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )

    result = converter.convert(pdf_path)
    doc = result.document

    images: list[Image.Image] = []
    for page in doc.pages.values():
        if page.image is not None and page.image.pil_image is not None:
            images.append(page.image.pil_image)

    return images


def image_to_base64(img: Image.Image) -> str:
    """Encode a PIL Image to a base64 PNG string."""
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def extract_page(image_b64: str, page_num: int, total_pages: int) -> str:
    """Send one page image to Ollama and return extracted Markdown text."""
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "user",
                "content": EXTRACT_PROMPT.format(
                    page_num=page_num, total_pages=total_pages
                ),
                "images": [image_b64],
            }
        ],
        "options": {
            "temperature": 0.05,
            "num_ctx": 8192,
        },
        "stream": False,
    }

    response = requests.post(
        f"{OLLAMA_URL}/api/chat",
        json=payload,
        timeout=OLLAMA_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()["message"]["content"]


def check_ollama() -> tuple[bool, str]:
    """Check that Ollama is running and the required model is available."""
    try:
        resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=10)
        resp.raise_for_status()
    except requests.exceptions.ConnectionError:
        return False, f"ไม่สามารถเชื่อมต่อ Ollama ได้ที่ {OLLAMA_URL} — รัน `ollama serve` ก่อน"
    except requests.exceptions.RequestException as e:
        return False, f"Ollama error: {e}"

    models = [m["name"] for m in resp.json().get("models", [])]
    if not any(MODEL_NAME in m for m in models):
        return (
            False,
            f"ไม่พบ model '{MODEL_NAME}' — รัน `ollama pull {MODEL_NAME}` ก่อน\n"
            f"Models ที่มีอยู่: {', '.join(models) or '(ไม่มี)'}",
        )

    return True, f"Ollama พร้อมใช้งาน · model: {MODEL_NAME}"


def process_pdf(
    pdf_path: str,
    progress_callback: Optional[Callable[[float, str], None]] = None,
    output_dir: Optional[str] = None,
) -> tuple[str, str]:
    """Run the full OCR pipeline on a PDF and return (markdown, output_path).

    Args:
        pdf_path: Path to the input PDF file.
        progress_callback: Optional callback(ratio, message) for progress updates.
        output_dir: Directory to save the output Markdown file. Defaults to same directory as input.
    """

    def _progress(ratio: float, message: str) -> None:
        if progress_callback:
            progress_callback(ratio, message)

    _progress(0.0, "กำลังตรวจสอบ Ollama…")
    ok, msg = check_ollama()
    if not ok:
        raise RuntimeError(msg)

    _progress(0.05, "กำลัง render หน้า PDF…")
    images = render_pages(pdf_path)
    total = len(images)
    if total == 0:
        raise RuntimeError("ไม่พบหน้าใดๆ ใน PDF")

    sections: list[str] = []
    for i, img in enumerate(images, start=1):
        _progress(0.1 + 0.85 * (i - 1) / total, f"กำลัง extract หน้า {i}/{total}…")
        b64 = image_to_base64(img)
        md = extract_page(b64, i, total)
        sections.append(f"# หน้า {i}\n\n{md}")

    full_markdown = "\n\n---\n\n".join(sections)

    input_path = Path(pdf_path)
    out_dir = Path(output_dir) if output_dir else input_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    output_path = out_dir / f"{input_path.stem}_extracted.md"
    output_path.write_text(full_markdown, encoding="utf-8")

    _progress(1.0, f"เสร็จสิ้น — บันทึกที่ {output_path}")
    return full_markdown, str(output_path)
