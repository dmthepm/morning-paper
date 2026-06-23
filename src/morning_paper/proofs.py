from __future__ import annotations

import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

from .config import MorningPaperConfig
from .renderers import count_pages


def utc_stamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def pdf_basic_proof(pdf_path: Path) -> dict[str, object]:
    path = pdf_path.expanduser()
    proof: dict[str, object] = {
        "path": str(path),
        "exists": path.is_file(),
        "size_bytes": path.stat().st_size if path.is_file() else 0,
        "header_ok": False,
        "pages": 0,
        "method": "",
        "ok": False,
        "error": "",
    }
    if not path.is_file():
        proof["error"] = "PDF path does not exist"
        return proof
    try:
        data = path.read_bytes()
    except OSError as exc:
        proof["error"] = str(exc)
        return proof
    proof["header_ok"] = data.startswith(b"%PDF-")
    if not proof["header_ok"]:
        proof["error"] = "file does not start with %PDF-"
        return proof

    pdfinfo = shutil.which("pdfinfo")
    if pdfinfo:
        result = subprocess.run(
            [pdfinfo, str(path)],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if result.returncode == 0:
            match = re.search(r"^Pages:\s+(\d+)\s*$", result.stdout, flags=re.MULTILINE)
            if match:
                proof["pages"] = int(match.group(1))
                proof["method"] = "pdfinfo"
    if not proof["pages"]:
        # Lightweight fallback for tests and minimal PDFs. Avoid matching /Pages.
        proof["pages"] = len(re.findall(rb"/Type\s*/Page\b", data))
        proof["method"] = "pdf-token-scan"
    proof["ok"] = bool(proof["header_ok"] and int(proof["pages"] or 0) > 0)
    if not proof["ok"] and not proof["error"]:
        proof["error"] = "could not prove positive page count"
    return proof


def estimate_markdown(
    draft_path: Path,
    config: MorningPaperConfig,
    *,
    date_str: str,
) -> dict[str, object]:
    source = draft_path.expanduser().resolve()
    payload: dict[str, object] = {
        "status": "pending",
        "date": date_str,
        "file": str(source),
        "style": config.outputs.style,
        "palette": config.outputs.palette,
        "font_scale": config.outputs.font_scale,
        "command": f"morning-paper estimate {source}",
        "updated_at": utc_stamp(),
    }
    if not source.is_file():
        payload.update({"status": "error", "error": "draft file does not exist"})
        return payload
    markdown = source.read_text(encoding="utf-8")
    payload["words"] = len(markdown.split())
    payload["file_mtime"] = source.stat().st_mtime
    try:
        payload["est_pages"] = count_pages(
            markdown,
            style=config.outputs.style,
            palette=config.outputs.palette,
            font_scale=config.outputs.font_scale,
        )
    except Exception as exc:  # noqa: BLE001 - proof artifact should report plainly.
        payload.update({"status": "error", "error": str(exc)})
        return payload
    payload["status"] = "estimated"
    return payload


def _markdown_visual_markers(markdown_path: Path | None) -> dict[str, object]:
    if not markdown_path or not markdown_path.is_file():
        return {"file": str(markdown_path or ""), "visual_markers": 0, "has_visuals": False}
    text = markdown_path.read_text(encoding="utf-8", errors="ignore")
    patterns = [
        r"<figure\b",
        r"<img\b",
        r"!\[[^\]]*\]\(",
        r"```mp-(?:bars|spark|stats)",
        r"class=[\"'][^\"']*mp-figure",
    ]
    count = sum(len(re.findall(pattern, text, flags=re.IGNORECASE)) for pattern in patterns)
    return {"file": str(markdown_path), "visual_markers": count, "has_visuals": count > 0}


def _select_pages(page_count: int, *, has_visuals: bool) -> list[int]:
    if page_count <= 0:
        return []
    if has_visuals:
        return list(range(1, min(page_count, 5) + 1))
    return sorted({1, page_count})


def _rasterize_page(pdf_path: Path, page: int, output_prefix: Path) -> Path | None:
    pdftoppm = shutil.which("pdftoppm")
    if not pdftoppm:
        return None
    result = subprocess.run(
        [
            pdftoppm,
            "-png",
            "-f",
            str(page),
            "-l",
            str(page),
            "-singlefile",
            str(pdf_path),
            str(output_prefix),
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "pdftoppm failed")
    return output_prefix.with_suffix(".png")


def visual_qa_from_render(
    *,
    render_result: dict[str, object],
    edition_dir: Path,
) -> dict[str, object]:
    outputs = render_result.get("outputs") if isinstance(render_result.get("outputs"), dict) else {}
    pdf_path = Path(str(outputs.get("pdf", ""))).expanduser() if outputs else Path()
    markdown_path = Path(str(outputs.get("markdown", ""))).expanduser() if outputs and outputs.get("markdown") else None
    proof = pdf_basic_proof(pdf_path)
    visual_markers = _markdown_visual_markers(markdown_path)
    pages = int(proof.get("pages") or 0)
    selected = _select_pages(pages, has_visuals=bool(visual_markers.get("has_visuals")))
    qa_dir = edition_dir / "_visual_qa"
    qa_dir.mkdir(parents=True, exist_ok=True)
    findings: list[dict[str, object]] = []
    inspected: list[dict[str, object]] = []
    status = "clean"

    if not proof.get("ok"):
        findings.append({"severity": "flag", "issue": proof.get("error") or "PDF proof failed"})
        status = "fail"
    elif not shutil.which("pdftoppm"):
        findings.append({"severity": "nudge", "issue": "pdftoppm not found; raster QA skipped"})
        status = "notes"
    else:
        for page in selected:
            prefix = qa_dir / f"page-{page}"
            try:
                png = _rasterize_page(pdf_path, page, prefix)
                if not png or not png.is_file():
                    raise RuntimeError("rasterized page was not written")
                with Image.open(png) as image:
                    gray = image.convert("L")
                    extrema = gray.getextrema()
                    width, height = image.size
                spread = int(extrema[1]) - int(extrema[0])
                blank = spread < 3
                inspected.append(
                    {
                        "page": page,
                        "image": str(png),
                        "width": width,
                        "height": height,
                        "gray_extrema": list(extrema),
                        "blank": blank,
                    }
                )
                if blank:
                    findings.append({"severity": "flag", "issue": f"page {page} rasterized blank"})
                    status = "fail"
            except Exception as exc:  # noqa: BLE001 - QA should report concrete page failures.
                findings.append({"severity": "flag", "issue": f"page {page} rasterization failed: {exc}"})
                status = "fail"

    return {
        "status": status,
        "updated_at": utc_stamp(),
        "pdf": proof,
        "markdown": visual_markers,
        "selected_pages": selected,
        "inspected_pages": inspected,
        "findings": findings,
    }


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
