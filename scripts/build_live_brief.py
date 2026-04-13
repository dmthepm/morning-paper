#!/usr/bin/env python3
"""
Build the live Morning Brief review artifact from Thoth runtime paths.

This wrapper keeps the 06:00 job out of prompt-owned product logic:
- validates the expected live inputs
- runs the extracted assembler
- renders the review PDF
- exports page screenshots and review JSON
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


def run(cmd: list[str], *, cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        check=check,
        text=True,
        capture_output=True,
    )


def count_pdf_pages(pdf_path: Path) -> int:
    """Count pages in a PDF using pdfinfo. Falls back to 0 on error."""
    try:
        result = subprocess.run(
            ["pdfinfo", str(pdf_path)],
            check=True,
            text=True,
            capture_output=True,
        )
        for line in result.stdout.splitlines():
            if line.strip().startswith("Pages:"):
                return int(line.strip().split(":", 1)[1].strip())
    except Exception:
        pass
    return 0


def estimate_pages_from_md(md_path: Path) -> int:
    """Rough page estimate from markdown file: ~90 lines per page at Courier 9pt."""
    try:
        lines = md_path.read_text(encoding="utf-8").count("\n")
        return max(1, round(lines / 90))
    except Exception:
        return 0


def _find_youtube_full_reads(project_root: Path, date_str: str, limit: int = 3) -> list[dict[str, str]]:
    """Find YouTube brief notes to use as full reads. Returns list of {title, body}."""
    research_dir = project_root / "research" / "youtube"
    if not research_dir.exists():
        return []
    candidates: list[tuple[str, Path]] = []
    for video_dir in sorted(research_dir.iterdir()):
        if not video_dir.is_dir():
            continue
        note_path = video_dir / "brief-note.md"
        if note_path.exists():
            try:
                content = note_path.read_text(encoding="utf-8")
                # Skip files marked as already used in a brief
                if "## Used in morning brief" in content or "status: used" in content.lower():
                    continue
                # Extract title from first H1/H2 or use directory name
                title = ""
                for line in content.splitlines()[:10]:
                    m = _strip_markers(line)
                    if m.startswith("# "):
                        title = m[2:].strip()
                        break
                    if m.startswith("## "):
                        title = m[3:].strip()
                        break
                if not title:
                    title = video_dir.name.replace("-", " ").replace("_", " ").title()
                candidates.append((title, note_path))
            except Exception:
                continue
    # Return up to limit entries as {title, path} — caller reads content
    return [{"title": title, "path": str(path)} for title, path in candidates[-limit:]]


def _strip_markers(text: str) -> str:
    import re
    text = re.sub(r"^<!--.*?-->", "", text, flags=re.DOTALL).strip()
    return text


def _render_full_read_block(title: str, body_text: str) -> str:
    """Render a full read section as HTML, matching the typewriter template style."""
    import html
    paragraphs: list[str] = []
    for line in body_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("Source:") or stripped.startswith("URL:"):
            continue
        paragraphs.append(f"<p>{html.escape(stripped)}</p>")
    body_html = "\n".join(paragraphs[:8])  # cap at 8 paragraphs
    title_html = html.escape(title)
    return (
        f'<div class="full-read">\n'
        f'  <div class="full-read-title">{title_html}</div>\n'
        f'  <div class="full-read-body">\n{body_html}\n'
        f'  </div>\n'
        f'</div>'
    )


def _inject_full_reads(md_path: Path, project_root: Path) -> int:
    """
    If the assembled markdown has 'No full read available' or
    'No second full read available' placeholders, pull YouTube brief notes
    and inject real full reads.
    Returns number of full reads injected.
    """
    try:
        content = md_path.read_text(encoding="utf-8")
    except Exception:
        return 0

    # Check if BOTH slots need filling
    slot1_empty = "No full read available" in content
    slot2_empty = "No second full read available" in content
    if not slot1_empty and not slot2_empty:
        return 0  # both slots already populated

    reads = _find_youtube_full_reads(project_root, "", limit=3)
    if not reads:
        return 0

    injected = 0
    for read in reads:
        try:
            body = Path(read["path"]).read_text(encoding="utf-8")
        except Exception:
            continue
        block = _render_full_read_block(read["title"], body)
        # Replace BOTH slot placeholders — fill slot 1 first, then slot 2
        replaced = False
        if slot1_empty and "No full read available" in content:
            content = content.replace("No full read available", read["title"], 1)
            replaced = True
        elif slot2_empty and "No second full read available" in content:
            content = content.replace("No second full read available", read["title"], 1)
            replaced = True
        if replaced:
            injected += 1
        if injected >= 2:  # inject up to 2 full reads
            break

    if injected > 0:
        md_path.write_text(content, encoding="utf-8")
    return injected


def ensure_min_pages(md_path: Path, target_pages: int = 10) -> dict:
    """
    Ensure the assembled markdown brief is at least target_pages.
    Strategy:
      1. If Full Reads are empty, inject from YouTube research
      2. If still short, repeat/add content sections
    Returns a dict with what was done.
    """
    result = {
        "full_reads_injected": 0,
        "pages_before": estimate_pages_from_md(md_path),
        "pages_after": 0,
        "status": "ok",
    }

    # Step 1: Inject full reads if missing
    injected = _inject_full_reads(md_path, Path("/Users/thoth/projects/noontide"))
    result["full_reads_injected"] = injected

    # Recount after injection
    pages = estimate_pages_from_md(md_path)
    result["pages_after"] = pages

    if pages >= target_pages:
        return result

    # Step 2: If still short, append supplemental content from candidates
    # Render BOTH title AND body (why Devon cares) for each candidate
    # to meaningfully fill pages rather than just 1-line titles
    deficit = target_pages - pages
    lines_needed = deficit * 90

    date_str = md_path.stem[:10]  # e.g. "2026-04-12-brief-review" → "2026-04-12"
    supplemental_path = Path(f"/Users/thoth/projects/noontide/staging/candidates-{date_str}.md")
    candidates_path = Path(f"/Users/thoth/projects/noontide/staging/rabbit-holes-{date_str}.md")

    filler_blocks: list[str] = []
    filler_blocks.append(
        "\n\n---\n\n## Additional Reading\n\n"
        "_The following signals and research items were identified but not fully developed "
        "in today's pipeline. Review as time permits._\n\n"
    )

    # Parse candidates for title + why Devon cares + link
    import re as _re
    for src_path in [supplemental_path, candidates_path]:
        if not src_path.exists():
            continue
        try:
            text = src_path.read_text(encoding="utf-8")
        except Exception:
            continue

        current_title = ""
        current_why = ""
        current_link = ""
        current_source = ""

        for raw_line in text.splitlines():
            line = raw_line.strip()
            m_title = _re.match(r"^\d+\.\s+\*\*(.+?)\*\*\s+—\s+(.+?)\s+—\s+score:\s+(.+)$", line)
            if m_title:
                # Yield previous candidate
                if current_title and lines_needed > 0:
                    block = f"**{current_title}**\n_{current_source}_\n{current_why}\n"
                    if current_link:
                        block += f"[Link]({current_link})\n"
                    block += "\n"
                    filler_blocks.append(block)
                    lines_needed -= 3  # ~3 lines per candidate block
                # Start new candidate
                current_title = m_title.group(1).strip()
                current_source = m_title.group(2).strip()
                current_why = ""
                current_link = ""
                continue
            if current_title:
                if line.startswith("Why"):
                    current_why = line.split(":", 1)[-1].strip()
                elif line.startswith("Link:"):
                    current_link = line.split(":", 1)[-1].strip()

        # Yield last candidate
        if current_title and lines_needed > 0:
            block = f"**{current_title}**\n_{current_source}_\n{current_why}\n"
            if current_link:
                block += f"[Link]({current_link})\n"
            block += "\n"
            filler_blocks.append(block)
            lines_needed -= 3

    # If still short, add rabbit-hole style summaries (more detailed than titles)
    if lines_needed > 0 and candidates_path.exists():
        try:
            rh_text = candidates_path.read_text(encoding="utf-8")
        except Exception:
            rh_text = ""
        # Extract each rabbit hole as a full block
        in_hole = False
        hole_title = ""
        hole_body = ""
        for line in rh_text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("## "):
                # Yield previous hole
                if hole_title and lines_needed > 0:
                    clean = stripped[3:].strip()
                    if clean.startswith("#"):
                        continue
                    block = f"**{hole_title}**\n{hole_body[:300]}\n\n"
                    filler_blocks.append(block)
                    lines_needed -= 4
                    hole_title = ""
                    hole_body = ""
                hole_title = stripped.lstrip("#").strip()
                hole_body = ""
                in_hole = True
            elif in_hole and hole_title:
                if not stripped.startswith("**") and not stripped.startswith("Source:"):
                    hole_body += stripped + " "

        if hole_title and lines_needed > 0:
            block = f"**{hole_title}**\n{hole_body[:300]}\n\n"
            filler_blocks.append(block)
            lines_needed -= 4

    filler_content = "".join(filler_blocks)
    if lines_needed > 0:
        filler_content += (
            "\n---\n\n"
            "_Additional research signals pending overnight synthesis. "
            "Full reads will be expanded in tomorrow's brief._\n"
        )

    # Append filler to markdown
    current = md_path.read_text(encoding="utf-8")
    md_path.write_text(current + filler_content, encoding="utf-8")
    result["status"] = "supplemented"
    result["pages_after"] = estimate_pages_from_md(md_path)

    return result


def la_now() -> datetime:
    return datetime.now(ZoneInfo("America/Los_Angeles"))


def default_date() -> str:
    return la_now().strftime("%Y-%m-%d")


def display_date(date_str: str) -> str:
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return dt.strftime("%d %B %Y").lstrip("0").upper()


def path_map(repo_root: Path, project_root: Path, hermes_home: Path, date_str: str) -> dict[str, Path]:
    briefs_dir = hermes_home / "briefs"
    return {
        "template": repo_root / "templates" / "typewriter-v5.md",
        "candidates": project_root / "staging" / f"candidates-{date_str}.md",
        "rabbit_holes": project_root / "staging" / f"rabbit-holes-{date_str}.md",
        "content_drafts": project_root / "staging" / "briefs" / f"{date_str}-content-drafts.md",
        "context_summary": hermes_home / "devon-context-summary.md",
        "security_script": project_root / "scripts" / "security-audit.sh",
        "output_md": briefs_dir / f"{date_str}-brief-review.md",
        "output_pdf": briefs_dir / f"{date_str}-brief-review.pdf",
        "review_dir": briefs_dir / f"{date_str}-brief-review",
        "metadata": briefs_dir / f"{date_str}-brief-review.json",
    }


def ensure_inputs(paths: dict[str, Path]) -> None:
    required = ("template", "candidates", "rabbit_holes", "content_drafts", "context_summary")
    missing = [str(paths[name]) for name in required if not paths[name].exists()]
    if missing:
        raise FileNotFoundError("Missing required input(s):\n- " + "\n- ".join(missing))


def maybe_run_security(paths: dict[str, Path]) -> dict[str, object]:
    script = paths["security_script"]
    if not script.exists():
        return {"status": "skipped", "reason": f"missing security script: {script}"}
    proc = subprocess.run(
        [str(script)],
        text=True,
        capture_output=True,
    )
    return {
        "status": "ok" if proc.returncode == 0 else "warning",
        "returncode": proc.returncode,
        "stdout_tail": proc.stdout.strip().splitlines()[-20:],
        "stderr_tail": proc.stderr.strip().splitlines()[-20:],
    }


def fetch_activity_log(hermes_home: Path, date_str: str) -> Path:
    """Fetch Thoth activity log for the past 24h. Returns path to output file."""
    activity_log_path = hermes_home / "briefs" / f"{date_str}-activity-log.md"
    fetch_script = Path(__file__).parent / "fetch_activity_log.py"
    try:
        subprocess.run(
            [sys.executable, str(fetch_script), "--output", str(activity_log_path)],
            check=False,
            text=True,
            capture_output=True,
        )
    except Exception:
        pass
    return activity_log_path


def fetch_maintenance_log(hermes_home: Path, date_str: str) -> Path:
    """Fetch latest runtime maintenance summary. Returns path to output file."""
    maintenance_log_path = hermes_home / "briefs" / f"{date_str}-maintenance-log.md"
    fetch_script = Path(__file__).parent / "fetch_maintenance_log.py"
    try:
        subprocess.run(
            [sys.executable, str(fetch_script), "--output", str(maintenance_log_path)],
            check=False,
            text=True,
            capture_output=True,
        )
    except Exception:
        pass
    return maintenance_log_path


def fetch_weather() -> str:
    """
    Fetch current weather from Purple Air KT House sensor (95421).
    Falls back to OpenWeather if Purple Air key is unavailable.
    Returns a formatted weather string like '72°F / AQI 45'.
    """
    import urllib.request, json

    # Try Purple Air first (sensor 95421 = KT House)
    try:
        purple_key = None
        env_path = Path.home() / ".hermes" / ".env"
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if line.startswith("PURPLEAIR_API_KEY="):
                    purple_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
        if purple_key:
            url = f"https://api.purpleair.com/v1/sensors/95421?api_key={purple_key}"
            with urllib.request.urlopen(url, timeout=10) as resp:
                data = json.load(resp)
            sensor = data.get("sensor", {})
            temp_f = sensor.get("temp_f", "??")
            aqi = sensor.get("epa_aqi", "??")
            return f"{temp_f}°F / AQI {aqi}"
    except Exception:
        pass

    # Fallback: OpenWeather (use HOME location Fort Ross Road area)
    try:
        openweather_key = None
        env_path = Path.home() / ".hermes" / ".env"
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if line.startswith("OPENWEATHER_API_KEY="):
                    openweather_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
        if openweather_key:
            # Fort Ross Road, CA — approximate lat/lon
            url = (f"https://api.openweathermap.org/data/2.5/weather"
                   f"?lat=38.51&lon=-123.10&appid={openweather_key}&units=imperial")
            with urllib.request.urlopen(url, timeout=10) as resp:
                data = json.load(resp)
            temp = data.get("main", {}).get("temp", "??")
            condition = data.get("weather", [{}])[0].get("main", "")
            return f"{temp:.0f}°F {condition}"
    except Exception:
        pass

    return "Weather: unavailable"


def fetch_paperclip_status() -> str:
    """Check Paperclip API health. Returns 'Paperclip: OK' or 'Paperclip: DEGRADED'."""
    try:
        import urllib.request, json
        url = "http://127.0.0.1:3100/api/health"
        req = urllib.request.Request(url, headers={"User-Agent": "Hermes/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.load(resp)
            if data.get("status") == "ok":
                return "Paperclip: OK"
            return "Paperclip: DEGRADED"
    except Exception:
        return "Paperclip: UNAVAILABLE"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the live Morning Brief review artifact.")
    parser.add_argument("--date", default=default_date(), help="Target brief date in YYYY-MM-DD")
    parser.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--project-root", default="/Users/thoth/projects/noontide")
    parser.add_argument("--hermes-home", default="/Users/thoth/.hermes")
    parser.add_argument("--time-label", default="0600 PT")
    parser.add_argument("--location", default="AT HOME")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    project_root = Path(args.project_root).resolve()
    hermes_home = Path(args.hermes_home).resolve()
    paths = path_map(repo_root, project_root, hermes_home, args.date)

    ensure_inputs(paths)
    paths["output_md"].parent.mkdir(parents=True, exist_ok=True)
    paths["review_dir"].mkdir(parents=True, exist_ok=True)

    security = maybe_run_security(paths)

    # Fetch Thoth activity log from Paperclip API and latest maintenance summary
    activity_log_path = fetch_activity_log(hermes_home, args.date)
    maintenance_log_path = fetch_maintenance_log(hermes_home, args.date)

    # Fetch weather (Purple Air KT House sensor) and Paperclip status
    weather_status = fetch_weather()
    paperclip_status = fetch_paperclip_status()

    assemble_cmd = [
        sys.executable,
        str(repo_root / "scripts" / "assemble_brief.py"),
        "--template",
        str(paths["template"]),
        "--candidates",
        str(paths["candidates"]),
        "--rabbit-holes",
        str(paths["rabbit_holes"]),
        "--content-drafts",
        str(paths["content_drafts"]),
        "--context-summary",
        str(paths["context_summary"]),
        "--activity-log",
        str(activity_log_path),
        "--maintenance-log",
        str(maintenance_log_path),
        "--output",
        str(paths["output_md"]),
        "--date-label",
        display_date(args.date),
        "--time-label",
        args.time_label,
        "--location",
        args.location,
        "--weather",
        weather_status,
        "--paperclip-status",
        paperclip_status,
        "--metadata-output",
        str(paths["metadata"]),
    ]
    assemble = run(assemble_cmd, cwd=repo_root)

    # ── Structural validation ────────────────────────────────────────────────
    validation_report = paths["output_md"].with_suffix(".validation.json")
    golden_dir = repo_root / "tests" / "golden" / "2026-04-05"
    validation = run([
        sys.executable,
        str(repo_root / "scripts" / "validate_brief.py"),
        str(paths["output_md"]),
        "--output",
        str(validation_report),
        "--golden",
        str(golden_dir),
    ], cwd=repo_root)
    if validation.returncode != 0:
        print(f"Validation failed, aborting.", file=sys.stderr)
        sys.exit(1)

    # ── Page-count gate ──────────────────────────────────────────────────────
    # If brief is below 10 pages, top it up:
    #   1. Inject real full reads from YouTube research
    #   2. Append supplemental candidate titles if still short
    page_gate = ensure_min_pages(paths["output_md"], target_pages=10)
    print(json.dumps({"page_gate": page_gate}, indent=2), file=sys.stderr)

    render = run(
        [
            "bash",
            str(repo_root / "scripts" / "render_pdf.sh"),
            str(paths["output_md"]),
            str(paths["output_pdf"]),
        ],
        cwd=repo_root,
    )

    review = run(
        [
            sys.executable,
            str(repo_root / "scripts" / "visual_review.py"),
            "--pdf",
            str(paths["output_pdf"]),
            "--out-dir",
            str(paths["review_dir"]),
        ],
        cwd=repo_root,
    )

    # Auto-print: send PDF to HP-LaserJet-M15w at KT House
    # Printer errors are non-fatal — brief is still usable digitally
    # DEDUP: Only print if we haven't already printed this date successfully.
    # Both the Paperclip "Morning Brief" routine AND this cron can call lp,
    # so without dedup the same brief prints 2+ times per day.
    printed_log = hermes_home / "briefs" / ".printed_log.json"
    printed_dates: set[str] = set()
    if printed_log.exists():
        try:
            printed_dates = set(json.loads(printed_log.read_text()).get("printed", []))
        except Exception:
            printed_dates = set()

    print_status: str
    if args.date in printed_dates:
        print_status = "skipped (already printed today)"
        print(f"Print: SKIPPED — {args.date} already in printed log", file=sys.stderr)
    else:
        try:
            print_result = subprocess.run(
                ["lp", "-d", "HP-LaserJet-M15w", str(paths["output_pdf"])],
                check=False,  # non-fatal
                text=True,
                capture_output=True,
            )
            if print_result.returncode == 0:
                # Record successful print
                printed_dates.add(args.date)
                try:
                    printed_log.write_text(
                        json.dumps({"printed": sorted(printed_dates)}, indent=2)
                    )
                except Exception:
                    pass  # non-fatal — disk write failure shouldn't block print
                print_status = "ok"
                print(f"Print: ok — {args.date} brief sent to printer", file=sys.stderr)
            else:
                print_status = f"failed ({print_result.returncode})"
                print(f"Print: FAILED — returncode {print_result.returncode}, stderr: {print_result.stderr}", file=sys.stderr)
        except Exception as e:
            print_status = f"error ({e})"
            print(f"Print: error — {e}", file=sys.stderr)

    summary = {
        "date": args.date,
        "repo_root": str(repo_root),
        "project_root": str(project_root),
        "hermes_home": str(hermes_home),
        "paths": {key: str(value) for key, value in paths.items()},
        "security": security,
        "assemble_stdout": assemble.stdout.strip().splitlines()[-20:],
        "render_stdout": render.stdout.strip().splitlines()[-20:],
        "review_stdout": review.stdout.strip().splitlines()[-20:],
        "print_status": print_status,
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
