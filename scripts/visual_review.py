#!/usr/bin/env python3
"""
Full-page screenshot and heuristic review for rendered Morning Brief PDFs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

try:
    import fitz  # type: ignore
except ImportError as exc:  # pragma: no cover
    raise SystemExit(f"PyMuPDF is required for visual_review.py: {exc}")


def save_screenshots(pdf_path: Path, out_dir: Path) -> list[dict[str, object]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(pdf_path)
    pages = []
    for i, page in enumerate(doc, start=1):
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        shot = out_dir / f"page-{i:02d}.png"
        pix.save(shot)
        text = page.get_text("text")
        words = len(text.split())
        pages.append(
            {
                "page": i,
                "screenshot": str(shot),
                "words": words,
                "chars": len(text),
                "text_preview": text[:300],
                "flags": [],
            }
        )
    doc.close()
    return pages


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def top_preview_lines(preview: str, *, count: int = 8) -> list[str]:
    return [line.strip() for line in preview.splitlines() if line.strip()][:count]


def inspect_pages(pages: list[dict[str, object]]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    total_pages = len(pages)
    if total_pages < 4:
        warnings.append(f"PDF is only {total_pages} pages; likely below target density.")
    for page in pages:
        preview = str(page["text_preview"])
        top_lines = top_preview_lines(preview)
        flags = page["flags"]
        if int(page["words"]) < 35:
            flags.append("LOW_TEXT")
            warnings.append(f"Page {page['page']} has very little text ({page['words']} words).")
        if "## " in preview or "```" in preview:
            flags.append("RAW_MARKDOWN")
            errors.append(f"Page {page['page']} preview still shows raw markdown heading markers.")
        hn_header_lines = [
            line for line in top_lines if "HACKER NEWS" in line and ("TOP 20" in line or line == "HACKER NEWS" or line.startswith("IV."))
        ]
        if hn_header_lines and not any(line.startswith("IV.") for line in top_lines):
            flags.append("HN_HEADER_ODD")
            warnings.append(f"Page {page['page']} mentions Hacker News but heading format may be off.")
        if int(page["page"]) == 1 and all(title not in preview for title in ("Morning Brief", "Morning Paper")):
            flags.append("TITLE_MISSING")
            errors.append("Page 1 does not appear to contain the Morning Paper title.")
    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate screenshots and heuristic review for each PDF page.")
    parser.add_argument("--pdf", required=True, help="Rendered PDF path")
    parser.add_argument("--out-dir", required=True, help="Directory for screenshots and review report")
    parser.add_argument("--report", help="Optional explicit JSON report path")
    args = parser.parse_args()

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        raise SystemExit(f"PDF not found: {pdf_path}")

    out_dir = Path(args.out_dir)
    pages = save_screenshots(pdf_path, out_dir)
    errors, warnings = inspect_pages(pages)
    report = {
        "pdf": str(pdf_path),
        "pdf_sha256": sha256_file(pdf_path),
        "page_count": len(pages),
        "errors": errors,
        "warnings": warnings,
        "pages": pages,
        "pass": len(errors) == 0,
    }
    report_path = Path(args.report) if args.report else out_dir / "visual-review.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
