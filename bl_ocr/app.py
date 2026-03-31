"""CLI entry point for Bill of Lading OCR extraction."""

import argparse
import sys
from pathlib import Path

from tqdm import tqdm

from pipeline import check_ollama, process_pdf


def run_single(
    pdf_path: str,
    output_dir: str | None,
    print_result: bool,
) -> bool:
    """Run OCR on a single PDF file. Returns True on success."""
    bar: tqdm | None = None

    def callback(ratio: float, message: str) -> None:
        nonlocal bar
        if bar is None:
            bar = tqdm(total=100, unit="%", desc="Extracting", ncols=70)
        bar.n = int(ratio * 100)
        bar.set_description(message[:40])
        bar.refresh()

    try:
        markdown, output_path = process_pdf(
            pdf_path, progress_callback=callback, output_dir=output_dir
        )
    except Exception as e:
        if bar:
            bar.close()
        print(f"\nERROR: {e}", file=sys.stderr)
        return False

    if bar:
        bar.n = 100
        bar.set_description("Done")
        bar.refresh()
        bar.close()

    print(f"\nSaved: {output_path}")

    if print_result:
        print("\n" + "=" * 60 + "\n")
        print(markdown)

    return True


def main() -> None:
    """Parse arguments and run the OCR pipeline."""
    parser = argparse.ArgumentParser(
        description="Bill of Lading OCR — extract structured data from PDF using Qwen2.5-VL via Ollama"
    )
    parser.add_argument(
        "pdf",
        nargs="?",
        help="Path to input PDF file (mutually exclusive with --folder)",
    )
    parser.add_argument(
        "--folder",
        "-d",
        metavar="DIR",
        help="Process all PDF files in this folder (mutually exclusive with pdf)",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory to save output Markdown files (default: same directory as each input PDF)",
    )
    parser.add_argument(
        "--print",
        dest="print_result",
        action="store_true",
        help="Print extracted Markdown to stdout after saving",
    )
    args = parser.parse_args()

    if not args.pdf and not args.folder:
        parser.error("ระบุ PDF file หรือ --folder อย่างใดอย่างหนึ่ง")
    if args.pdf and args.folder:
        parser.error("ระบุได้แค่ PDF file หรือ --folder อย่างเดียว ไม่ใช่ทั้งสอง")

    # Check Ollama once before starting
    print("Checking Ollama...", flush=True)
    ok, msg = check_ollama()
    if not ok:
        print(f"ERROR: {msg}", file=sys.stderr)
        sys.exit(1)
    print(f"OK: {msg}\n", flush=True)

    if args.folder:
        # Batch mode — process all PDFs in a folder
        folder = Path(args.folder)
        if not folder.is_dir():
            print(f"ERROR: '{args.folder}' ไม่ใช่ directory ที่ถูกต้อง", file=sys.stderr)
            sys.exit(1)

        pdf_files = sorted(folder.glob("*.pdf"))
        if not pdf_files:
            print(f"ไม่พบไฟล์ PDF ใน '{args.folder}'", file=sys.stderr)
            sys.exit(1)

        print(f"พบ {len(pdf_files)} ไฟล์ PDF ใน '{args.folder}'\n")

        succeeded, failed = 0, []
        for i, pdf_path in enumerate(pdf_files, start=1):
            print(f"[{i}/{len(pdf_files)}] {pdf_path.name}")
            if run_single(str(pdf_path), args.output_dir, args.print_result):
                succeeded += 1
            else:
                failed.append(pdf_path.name)
            print()

        print("=" * 60)
        print(f"Batch complete: {succeeded}/{len(pdf_files)} สำเร็จ")
        if failed:
            print(f"ล้มเหลว: {', '.join(failed)}")
            sys.exit(1)
    else:
        # Single file mode
        if not run_single(args.pdf, args.output_dir, args.print_result):
            sys.exit(1)


if __name__ == "__main__":
    main()
