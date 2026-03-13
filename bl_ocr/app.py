"""CLI entry point for Bill of Lading OCR extraction."""

import argparse
import sys

from tqdm import tqdm

from pipeline import check_ollama, process_pdf


def main() -> None:
    """Parse arguments and run the OCR pipeline."""
    parser = argparse.ArgumentParser(
        description="Bill of Lading OCR — extract structured data from PDF using Qwen2.5-VL via Ollama"
    )
    parser.add_argument("pdf", help="Path to input PDF file")
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory to save the output Markdown file (default: same directory as input PDF)",
    )
    parser.add_argument(
        "--print",
        dest="print_result",
        action="store_true",
        help="Print extracted Markdown to stdout after saving",
    )
    args = parser.parse_args()

    # Check Ollama
    print("Checking Ollama...", flush=True)
    ok, msg = check_ollama()
    if not ok:
        print(f"ERROR: {msg}", file=sys.stderr)
        sys.exit(1)
    print(f"OK: {msg}\n", flush=True)

    # Progress bar
    bar: tqdm | None = None

    def callback(ratio: float, message: str) -> None:
        nonlocal bar
        if bar is None:
            bar = tqdm(total=100, unit="%", desc="Extracting", ncols=70)
        current = int(ratio * 100)
        bar.n = current
        bar.set_description(message[:40])
        bar.refresh()

    # Run pipeline
    try:
        markdown, output_path = process_pdf(args.pdf, progress_callback=callback)
    except Exception as e:
        if bar:
            bar.close()
        print(f"\nERROR: {e}", file=sys.stderr)
        sys.exit(1)

    if bar:
        bar.n = 100
        bar.set_description("Done")
        bar.refresh()
        bar.close()

    print(f"\nSaved: {output_path}")

    if args.print_result:
        print("\n" + "=" * 60 + "\n")
        print(markdown)


if __name__ == "__main__":
    main()
