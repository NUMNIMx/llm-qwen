"""Gradio web UI for Bill of Lading OCR extraction."""

import time
from pathlib import Path

import gradio as gr

from pipeline import check_ollama, process_pdf


def _fmt_duration(seconds: float) -> str:
    """Format seconds into a human-readable string (e.g. '1m 23s' or '45s')."""
    seconds = int(seconds)
    if seconds >= 60:
        return f"{seconds // 60}m {seconds % 60}s"
    return f"{seconds}s"


def get_ollama_status() -> str:
    """Return Ollama connectivity status as a Markdown string."""
    ok, msg = check_ollama()
    icon = "🟢" if ok else "🔴"
    return f"{icon} {msg}"


def extract_single(pdf_path: str | None, progress=gr.Progress()) -> tuple:
    """Process a single uploaded PDF and return (markdown, download_file_update)."""
    if pdf_path is None:
        return "กรุณาอัปโหลดไฟล์ PDF", gr.update(visible=False)

    def callback(ratio: float, message: str) -> None:
        progress(ratio, desc=message)

    t_start = time.perf_counter()
    try:
        markdown, output_path = process_pdf(pdf_path, progress_callback=callback)
    except Exception as e:
        return f"**ERROR:** {e}", gr.update(visible=False)
    elapsed = _fmt_duration(time.perf_counter() - t_start)

    header = f"_ใช้เวลา: **{elapsed}**_ · บันทึกที่: `{output_path}`\n\n---\n\n"
    return header + markdown, gr.update(value=output_path, visible=True)


def extract_batch(
    pdf_paths: list[str] | None,
    output_dir: str,
    progress=gr.Progress(),
) -> str:
    """Process multiple uploaded PDFs and return a Markdown summary."""
    if not pdf_paths:
        return "กรุณาอัปโหลดไฟล์ PDF อย่างน้อย 1 ไฟล์"

    out_dir = output_dir.strip() or None
    total = len(pdf_paths)
    results: list[str] = []
    t_batch_start = time.perf_counter()

    for i, pdf_path in enumerate(pdf_paths):
        name = Path(pdf_path).name
        progress(i / total, desc=f"[{i + 1}/{total}] {name}")
        t_file_start = time.perf_counter()
        try:
            _, saved_path = process_pdf(pdf_path, output_dir=out_dir)
            elapsed = _fmt_duration(time.perf_counter() - t_file_start)
            results.append(f"✅ **{name}** · {elapsed} → `{saved_path}`")
        except Exception as e:
            elapsed = _fmt_duration(time.perf_counter() - t_file_start)
            results.append(f"❌ **{name}** · {elapsed}: {e}")

    progress(1.0, desc="เสร็จสิ้น")
    total_elapsed = _fmt_duration(time.perf_counter() - t_batch_start)
    ok_count = sum(1 for r in results if r.startswith("✅"))
    summary = (
        f"### ผลลัพธ์: {ok_count}/{total} สำเร็จ · รวม {total_elapsed}\n\n"
        + "\n\n".join(results)
    )
    return summary


with gr.Blocks(theme=gr.themes.Soft(), title="BL OCR") as demo:
    gr.Markdown("# Bill of Lading OCR")
    status_bar = gr.Markdown("กำลังตรวจสอบ Ollama…")
    demo.load(get_ollama_status, outputs=status_bar)

    with gr.Tabs():

        # ── Tab 1: Single file ──────────────────────────────────────────
        with gr.Tab("ไฟล์เดียว"):
            with gr.Row():
                with gr.Column(scale=1):
                    pdf_input = gr.File(
                        label="อัปโหลด PDF",
                        file_types=[".pdf"],
                        type="filepath",
                    )
                    extract_btn = gr.Button("เริ่ม Extract", variant="primary")

                with gr.Column(scale=2):
                    result_md = gr.Markdown(label="ผลลัพธ์")
                    download_btn = gr.File(label="ดาวน์โหลด Markdown", visible=False)

            extract_btn.click(
                extract_single,
                inputs=pdf_input,
                outputs=[result_md, download_btn],
            )

        # ── Tab 2: Batch files ──────────────────────────────────────────
        with gr.Tab("หลายไฟล์"):
            with gr.Row():
                with gr.Column(scale=1):
                    pdfs_input = gr.Files(
                        label="อัปโหลด PDF (เลือกได้หลายไฟล์)",
                        file_types=[".pdf"],
                        type="filepath",
                    )
                    out_dir_input = gr.Textbox(
                        label="Output Directory",
                        placeholder="เว้นว่างไว้ = บันทึกในโฟลเดอร์เดียวกับไฟล์ต้นฉบับ",
                    )
                    batch_btn = gr.Button("เริ่ม Extract ทั้งหมด", variant="primary")

                with gr.Column(scale=2):
                    batch_result_md = gr.Markdown(label="ผลลัพธ์")

            batch_btn.click(
                extract_batch,
                inputs=[pdfs_input, out_dir_input],
                outputs=batch_result_md,
            )


if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
