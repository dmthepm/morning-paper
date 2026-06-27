from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import yaml

from .config import MorningPaperConfig
from .proofs import estimate_markdown, pdf_basic_proof, visual_qa_from_render, write_json
from .sources import source_inventory
from .staging import queue_status


FEEDBACK_ROUTES = {
    "editorial": "EDITORIAL.md",
    "visuals": "VISUALS.md",
    "sources": "SOURCES.md",
    "delivery": "DELIVERY.md",
    "taste": "TASTELOG.md",
    "voice": "preferences/voice.md",
    "interests": "preferences/interests.yaml",
    "budgets": "preferences/source-budgets.yaml",
    "checks": "preferences/checks.yaml",
    "the-read": "specs/the-read.md",
    "front-page": "specs/front-page.md",
    "reading": "specs/reading.md",
}

FEEDBACK_ROUTE_GUIDANCE: tuple[tuple[str, str, str], ...] = (
    ("Keep / cut / more / less / what earns ink", "editorial", FEEDBACK_ROUTES["editorial"]),
    ("Voice, density, register, tone, AI tells", "voice", FEEDBACK_ROUTES["voice"]),
    (
        "Section-specific taste",
        "the-read|front-page|reading",
        f'{FEEDBACK_ROUTES["the-read"]}, {FEEDBACK_ROUTES["front-page"]}, or {FEEDBACK_ROUTES["reading"]}',
    ),
    ("Visuals, charts, illustrations, layout, print readability", "visuals", FEEDBACK_ROUTES["visuals"]),
    ("Add, demote, remove, distrust, or change cadence of a source", "sources", FEEDBACK_ROUTES["sources"]),
    ("Standing interests and topic dampeners", "interests", FEEDBACK_ROUTES["interests"]),
    ("Page, source, beat, full-read, visual, or process budget", "budgets", FEEDBACK_ROUTES["budgets"]),
    ("Review thresholds or muted copy-desk findings", "checks", FEEDBACK_ROUTES["checks"]),
    (
        "PDF, print, email/article view, archive, routine/automation behavior",
        "delivery",
        FEEDBACK_ROUTES["delivery"],
    ),
    ("Stable accepted/rejected taste decision", "taste", FEEDBACK_ROUTES["taste"]),
)


DEFAULT_DESK_SHEET_PREFS: dict[str, object] = {
    "enabled": False,
    "template": "no10",
    "surface": "separate-sheet",
    "notes_lines": 14,
    "ask_count": 4,
    "tomorrow_choices": 5,
}

SUBSTANTIAL_PAGE_THRESHOLD = 8
REQUIRED_SUBSTANTIAL_PHASES = {
    "04": "editor",
    "05": "copy-desk",
    "06": "art-desk",
}
PRODUCER_PHASE = "07"


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _load_json_object(path: Path) -> dict[str, object]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _load_desk_sheet_preferences(root: Path) -> dict[str, object]:
    prefs = dict(DEFAULT_DESK_SHEET_PREFS)
    path = root / "preferences" / "desk-sheet.yaml"
    if not path.is_file():
        return prefs
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return prefs
    if not isinstance(loaded, dict):
        return prefs
    prefs.update(loaded)
    for key in ("notes_lines", "ask_count", "tomorrow_choices"):
        try:
            prefs[key] = int(prefs.get(key) or DEFAULT_DESK_SHEET_PREFS[key])
        except (TypeError, ValueError):
            prefs[key] = DEFAULT_DESK_SHEET_PREFS[key]
    return prefs


def _desk_sheet_enabled(root: Path) -> bool:
    return bool(_load_desk_sheet_preferences(root).get("enabled"))


def _positive_int(value: object) -> int | None:
    try:
        parsed = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _page_budget_policy(root: Path) -> dict[str, object]:
    fallback_target = 12
    fallback_max = 20
    policy: dict[str, object] = {
        "target_pages": fallback_target,
        "max_pages": fallback_max,
        "source": "default",
    }
    path = root / "preferences" / "source-budgets.yaml"
    if not path.is_file():
        return policy
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return policy
    if not isinstance(loaded, dict):
        return policy
    edition = loaded.get("edition")
    if not isinstance(edition, dict):
        return policy
    target = _positive_int(edition.get("target_pages")) or fallback_target
    max_pages = _positive_int(edition.get("max_pages")) or max(target, fallback_max)
    if max_pages < target:
        max_pages = target
    return {
        "target_pages": target,
        "max_pages": max_pages,
        "source": "preferences/source-budgets.yaml",
    }


def _int_or_zero(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _final_finding(
    findings: list[dict[str, object]],
    *,
    check: str,
    severity: str,
    issue: str,
    why: str,
    hint: str,
    location: str = "",
    measured: dict[str, object] | None = None,
) -> None:
    item: dict[str, object] = {
        "check": check,
        "severity": severity,
        "issue": issue,
        "why": why,
        "hint": hint,
    }
    if location:
        item["location"] = location
    if measured:
        item["measured"] = measured
    findings.append(item)


def _final_status(findings: list[dict[str, object]]) -> str:
    severities = {str(item.get("severity", "")) for item in findings}
    if "flag" in severities:
        return "review"
    if severities:
        return "notes"
    return "clean"


def _final_summary(findings: list[dict[str, object]]) -> dict[str, int]:
    return {
        "flag": sum(1 for item in findings if item.get("severity") == "flag"),
        "nudge": sum(1 for item in findings if item.get("severity") == "nudge"),
        "info": sum(1 for item in findings if item.get("severity") == "info"),
    }


def _assignment_board(
    source_inventory_payload: dict[str, object],
    queue_snapshot: dict[str, object],
    *,
    date_str: str,
    edition_dir: Path,
) -> dict[str, object]:
    """Project current source material into a simple newsroom board.

    The staging queue remains the compatibility storage layer. The Assignment
    Board is the agent-facing editorial view over that storage.
    """
    lanes: dict[str, list[dict[str, object]]] = {
        "ready_to_edit": [],
        "needs_source_record": [],
        "needs_source_proof": [],
        "source_health": [],
        # Reserved for editor/producer handoffs; the CLI does not infer selection.
        "selected": [],
        "cut": [],
        "held": [],
        "printed": [],
    }
    items = queue_snapshot.get("items") if isinstance(queue_snapshot.get("items"), list) else []
    for item in items:
        if not isinstance(item, dict):
            continue
        item_id = str(item.get("slug") or item.get("title") or "item")
        board_item = {
            "id": item_id,
            "title": item.get("title") or item_id,
            "kind": item.get("kind") or "item",
            "source": item.get("source") or "",
            "est_pages": _int_or_zero(item.get("est_pages")),
            "words": _int_or_zero(item.get("words")),
            "route": "source material",
            "reason": "added through `morning-paper stage`",
            "compatibility": {"queue_slug": item.get("slug") or item_id},
        }
        proof_notes = [
            str(item.get(key) or "")
            for key in ("warning", "extractor_note")
            if str(item.get(key) or "").strip()
        ]
        source_status = str(item.get("source_status") or item.get("hydration_status") or "").strip().lower()
        social_like = str(item.get("kind") or "").strip().lower() in {"social", "tweet", "thread", "x-post"}
        if source_status in {"discovery", "snippet_only", "snippet-only", "needs_hydration", "partial", "incomplete"}:
            board_item["route"] = "needs source record"
            board_item["reason"] = (
                "; ".join(proof_notes)
                or "social item is discovery/partial; complete full text, author/date, metrics, media, and thread context"
            )
            lanes["needs_source_record"].append(board_item)
        elif social_like and item.get("truncated"):
            board_item["route"] = "needs source record"
            board_item["reason"] = (
                "; ".join(proof_notes)
                or "social post is truncated; do not print until the real source record is complete"
            )
            lanes["needs_source_record"].append(board_item)
        elif item.get("truncated") or proof_notes:
            board_item["route"] = "needs source proof"
            board_item["reason"] = "; ".join(proof_notes) or "source copy is incomplete"
            lanes["needs_source_proof"].append(board_item)
        else:
            lanes["ready_to_edit"].append(board_item)

    newsroom = source_inventory_payload.get("newsroom") if isinstance(source_inventory_payload.get("newsroom"), dict) else {}
    local_drop = newsroom.get("local_drop") if isinstance(newsroom.get("local_drop"), dict) else {}
    unsupported = _int_or_zero(local_drop.get("unsupported_count")) if isinstance(local_drop, dict) else 0
    if unsupported:
        lanes["source_health"].append(
            {
                "id": "local-drop-unsupported",
                "title": "Local drop has unsupported files",
                "kind": "source_health",
                "source": local_drop.get("path") or "",
                "est_pages": 0,
                "route": "source health",
                "reason": f"{unsupported} file(s) need a converter collector",
            }
        )
    sources = source_inventory_payload.get("sources") if isinstance(source_inventory_payload.get("sources"), list) else []
    for source in sources:
        if not isinstance(source, dict):
            continue
        if source.get("status") == "error":
            lanes["source_health"].append(
                {
                    "id": source.get("id") or source.get("name") or "source-error",
                    "title": source.get("name") or source.get("id") or "Source error",
                    "kind": "source_health",
                    "source": source.get("url") or source.get("type") or "",
                    "est_pages": 0,
                    "route": "source health",
                    "reason": source.get("error") or "source check failed",
                }
            )

    summary = {lane: len(values) for lane, values in lanes.items()}
    return {
        "status": "ready" if any(summary.values()) else "empty",
        "date": date_str,
        "edition_dir": str(edition_dir),
        "summary": summary,
        "page_budget": queue_snapshot.get("page_budget"),
        "est_pages_total": queue_snapshot.get("est_pages_total", 0),
        "budget_remaining": queue_snapshot.get("budget_remaining"),
        "lanes": lanes,
        "source": {
            "queue_snapshot": str(edition_dir / "queue-snapshot.json"),
            "source_inventory": str(edition_dir / "source-inventory.json"),
        },
        "updated_at": _utc_stamp(),
    }


def _render_assignment_board_markdown(board: dict[str, object]) -> str:
    lines = [
        f"# Assignment Board - {board.get('date', '')}",
        "",
        f"Status: {board.get('status', '')}",
        f"Estimated pages: {board.get('est_pages_total', 0)} / budget {board.get('page_budget', '')}",
        "",
    ]
    lanes = board.get("lanes") if isinstance(board.get("lanes"), dict) else {}
    for lane in (
        "ready_to_edit",
        "needs_source_record",
        "needs_source_proof",
        "source_health",
        "selected",
        "cut",
        "held",
        "printed",
    ):
        items = lanes.get(lane) if isinstance(lanes.get(lane), list) else []
        title = lane.replace("_", " ").title()
        lines.extend([f"## {title}", ""])
        if not items:
            lines.append("- None.")
        else:
            for item in items:
                if not isinstance(item, dict):
                    continue
                bits = [str(item.get("title") or item.get("id") or "Untitled")]
                if item.get("est_pages"):
                    bits.append(f"{item.get('est_pages')} page(s)")
                if item.get("reason"):
                    bits.append(str(item.get("reason")))
                lines.append("- " + " - ".join(bits))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _pending_run_ticket(root: Path, *, date_str: str) -> dict[str, object]:
    return {
        "status": "pending",
        "date": date_str,
        "command": f"morning-paper edition status {root} --date {date_str}",
        "roles": _role_artifacts(root / "editions" / date_str),
        "updated_at": _utc_stamp(),
    }


def _render_run_ticket_markdown(ticket: dict[str, object]) -> str:
    lines = [
        f"# Morning Run Ticket - {ticket.get('date', '')}",
        "",
        f"Status: {ticket.get('status', '')}",
        f"Next action: {ticket.get('next_action', '')}",
        "",
        "## Checks",
    ]
    checks = ticket.get("checks") if isinstance(ticket.get("checks"), list) else []
    if not checks:
        lines.append("- None.")
    for check in checks:
        if not isinstance(check, dict):
            continue
        state = str(check.get("state", "")).upper()
        lines.append(f"- {state} `{check.get('name', '')}` - {check.get('detail', '')}")
    roles = ticket.get("roles") if isinstance(ticket.get("roles"), dict) else {}
    role_files = roles.get("files") if isinstance(roles.get("files"), list) else []
    if roles:
        lines.extend(["", "## Desk Artifacts"])
        lines.append(f"- Count: {roles.get('count', 0)}")
        for filename in role_files:
            lines.append(f"- `{filename}`")
        invalid = roles.get("invalid") if isinstance(roles.get("invalid"), list) else []
        blocked = roles.get("blocked") if isinstance(roles.get("blocked"), list) else []
        missing = roles.get("missing") if isinstance(roles.get("missing"), list) else []
        phases = roles.get("phases") if isinstance(roles.get("phases"), dict) else {}
        for item in invalid:
            if isinstance(item, dict):
                lines.append(f"- Needs repair: `{item.get('file', '')}` - {item.get('issue', '')}")
        for item in blocked:
            if isinstance(item, dict):
                lines.append(f"- Blocked: `{item.get('file', '')}` - role reported blocked")
        if phases:
            lines.append("- Phases: " + ", ".join(sorted(str(phase) for phase in phases)))
        for phase in missing:
            lines.append(f"- Missing quality gate: `{phase}`")
    return "\n".join(lines).rstrip() + "\n"


def _run_ticket_status(checks: list[dict[str, object]]) -> str:
    states = {str(check.get("state", "")) for check in checks}
    if "block" in states:
        return "blocked"
    if "note" in states:
        return "complete_with_notes"
    return "complete"


def _add_ticket_check(checks: list[dict[str, object]], *, name: str, state: str, detail: str) -> None:
    checks.append({"name": name, "state": state, "detail": detail})


def _role_artifacts(edition_dir: Path) -> dict[str, object]:
    desks_dir = edition_dir / "desks"
    if not desks_dir.is_dir():
        return {"dir": str(desks_dir), "count": 0, "files": [], "invalid": [], "blocked": [], "phases": {}}
    paths = sorted(
        path
        for path in desks_dir.glob("*.md")
        if path.is_file() and path.name.lower() != "readme.md"
    )
    invalid: list[dict[str, str]] = []
    blocked: list[dict[str, str]] = []
    phases: dict[str, dict[str, str]] = {}
    required = {"role", "phase", "status"}
    allowed_statuses = {"ready", "notes", "blocked"}
    for path in paths:
        text = path.read_text(encoding="utf-8", errors="replace")
        if not text.startswith("---\n"):
            invalid.append({"file": path.name, "issue": "missing YAML frontmatter"})
            continue
        marker = text.find("\n---", 4)
        if marker == -1:
            invalid.append({"file": path.name, "issue": "unclosed YAML frontmatter"})
            continue
        try:
            frontmatter = yaml.safe_load(text[4:marker]) or {}
        except yaml.YAMLError:
            invalid.append({"file": path.name, "issue": "invalid YAML frontmatter"})
            continue
        if not isinstance(frontmatter, dict):
            invalid.append({"file": path.name, "issue": "frontmatter must be a mapping"})
            continue
        missing = sorted(required - set(str(key) for key in frontmatter))
        if missing:
            invalid.append({"file": path.name, "issue": "missing " + ", ".join(missing)})
            continue
        status = str(frontmatter.get("status", "")).strip().lower()
        if status not in allowed_statuses:
            invalid.append({"file": path.name, "issue": "status must be ready, notes, or blocked"})
            continue
        phase = str(frontmatter.get("phase", "")).strip()
        role = str(frontmatter.get("role", "")).strip()
        phases[phase] = {"file": path.name, "role": role, "status": status}
        if status == "blocked":
            blocked.append({"file": path.name, "role": role})
    return {
        "dir": str(desks_dir),
        "count": len(paths),
        "files": [path.name for path in paths],
        "invalid": invalid,
        "blocked": blocked,
        "phases": phases,
    }


def _substantial_page_count(estimate: dict[str, object], render: dict[str, object]) -> int:
    return max(_int_or_zero(estimate.get("est_pages")), _int_or_zero(render.get("pages")))


def _missing_substantial_phases(roles: dict[str, object]) -> list[str]:
    phases = roles.get("phases") if isinstance(roles.get("phases"), dict) else {}
    missing: list[str] = []
    for phase, role_name in REQUIRED_SUBSTANTIAL_PHASES.items():
        if phase not in phases:
            missing.append(f"{phase}-{role_name}")
    return missing


def _build_run_ticket(root: Path, config: MorningPaperConfig, *, date_str: str) -> dict[str, object]:
    edition_dir = root / "editions" / date_str
    if not edition_dir.is_dir():
        raise FileNotFoundError(f"missing edition directory: {edition_dir}")
    budget_policy = _page_budget_policy(root)
    checks: list[dict[str, object]] = []

    def require_file(name: str, label: str, *, block: bool = True) -> bool:
        path = edition_dir / name
        if path.is_file():
            _add_ticket_check(checks, name=label, state="pass", detail=f"`{name}` exists")
            return True
        _add_ticket_check(checks, name=label, state="block" if block else "note", detail=f"`{name}` is missing")
        return False

    require_file("source-inventory.json", "sources")
    require_file("collector-report.md", "collector report", block=False)
    require_file("assignment-board.json", "assignment board", block=False)
    require_file("desks/README.md", "desk artifact guide", block=False)
    require_file("draft.md", "draft")
    require_file("feedback-plan.md", "feedback route")
    require_file("operator-answers.md", "reader feedback sheet", block=False)
    if _desk_sheet_enabled(root):
        require_file("desk-sheet.md", "Desk Sheet", block=False)

    roles = _role_artifacts(edition_dir)
    role_count = int(roles.get("count") or 0)
    role_invalid = roles.get("invalid") if isinstance(roles.get("invalid"), list) else []
    role_blocked = roles.get("blocked") if isinstance(roles.get("blocked"), list) else []
    if role_count:
        if role_blocked:
            _add_ticket_check(
                checks,
                name="desk artifacts",
                state="block",
                detail=f"{len(role_blocked)} role artifact(s) reported blocked",
            )
        elif role_invalid:
            _add_ticket_check(
                checks,
                name="desk artifacts",
                state="note",
                detail=f"{len(role_invalid)} role artifact(s) need frontmatter repair",
            )
        else:
            _add_ticket_check(
                checks,
                name="desk artifacts",
                state="pass",
                detail=f"{role_count} valid role artifact(s) in `desks/`",
            )
    else:
        _add_ticket_check(
            checks,
            name="desk artifacts",
            state="pass",
            detail="no role artifacts yet; simple run path is allowed",
        )

    estimate = _load_json_object(edition_dir / "estimate-result.json")
    if estimate.get("status") == "estimated":
        _add_ticket_check(checks, name="estimate", state="pass", detail=f"{estimate.get('est_pages')} estimated page(s)")
    else:
        _add_ticket_check(checks, name="estimate", state="block", detail=f"estimate status is `{estimate.get('status') or 'missing'}`")

    render = _load_json_object(edition_dir / "render-result.json")
    outputs = render.get("outputs") if isinstance(render.get("outputs"), dict) else {}
    pdf_path = Path(str(outputs.get("pdf", ""))).expanduser() if outputs else Path()
    if render.get("status") == "rendered" and pdf_path.is_file():
        proof = pdf_basic_proof(pdf_path)
        if proof.get("ok"):
            _add_ticket_check(checks, name="rendered PDF", state="pass", detail=f"{proof.get('pages')} page PDF")
        else:
            _add_ticket_check(checks, name="rendered PDF", state="block", detail="PDF exists but is not readable")
    else:
        _add_ticket_check(checks, name="rendered PDF", state="block", detail=f"render status is `{render.get('status') or 'missing'}`")

    review = _load_json_object(edition_dir / "review.json")
    review_status = str(review.get("status") or "missing")
    if review_status == "clean":
        _add_ticket_check(checks, name="review", state="pass", detail="clean")
    elif review_status == "notes":
        _add_ticket_check(checks, name="review", state="note", detail="review has notes")
    elif review_status == "review":
        _add_ticket_check(checks, name="review", state="block", detail="review requested revision")
    else:
        _add_ticket_check(checks, name="review", state="block", detail=f"review status is `{review_status}`")

    visual_qa = _load_json_object(edition_dir / "visual-qa.json")
    visual_status = str(visual_qa.get("status") or "missing")
    if visual_status == "clean":
        _add_ticket_check(checks, name="visual QA", state="pass", detail="clean")
    elif visual_status == "notes":
        _add_ticket_check(checks, name="visual QA", state="note", detail="visual QA has notes")
    else:
        _add_ticket_check(checks, name="visual QA", state="block", detail=f"visual QA status is `{visual_status}`")

    final_editor = _load_json_object(edition_dir / "final-editor.json")
    final_status = str(final_editor.get("status") or "missing")
    if final_status == "clean":
        _add_ticket_check(checks, name="final editor", state="pass", detail="clean")
    elif final_status == "notes":
        _add_ticket_check(checks, name="final editor", state="note", detail="deliver with note")
    else:
        _add_ticket_check(checks, name="final editor", state="block", detail=f"final-editor status is `{final_status}`")

    delivery = _load_json_object(edition_dir / "delivery-result.json")
    delivery_status = str(delivery.get("status") or "missing")
    if delivery_status in {"delivered", "not_configured", "skipped"}:
        _add_ticket_check(checks, name="delivery proof", state="pass", detail=delivery_status)
    elif delivery_status == "pending":
        _add_ticket_check(checks, name="delivery proof", state="note", detail="delivery result is pending")
    else:
        _add_ticket_check(checks, name="delivery proof", state="note", detail="delivery result is missing")

    substantial_pages = _substantial_page_count(estimate, render)
    if substantial_pages >= SUBSTANTIAL_PAGE_THRESHOLD:
        missing = _missing_substantial_phases(roles)
        if missing:
            roles["missing"] = missing
            _add_ticket_check(
                checks,
                name="desk quality gates",
                state="block",
                detail=f"substantial {substantial_pages}-page edition is missing " + ", ".join(missing),
            )
        else:
            _add_ticket_check(
                checks,
                name="desk quality gates",
                state="pass",
                detail="editor, copy desk, and art desk handoffs exist",
            )
        phases = roles.get("phases") if isinstance(roles.get("phases"), dict) else {}
        if final_status in {"clean", "notes"} and PRODUCER_PHASE not in phases:
            current_missing = roles.get("missing") if isinstance(roles.get("missing"), list) else []
            roles["missing"] = sorted({*current_missing, "07-producer"})
            _add_ticket_check(
                checks,
                name="producer",
                state="block",
                detail="substantial edition needs a producer handoff after final-editor and before delivery",
            )
        elif final_status in {"clean", "notes"}:
            _add_ticket_check(checks, name="producer", state="pass", detail="producer handoff exists")

    status = _run_ticket_status(checks)
    next_action = {
        "complete": "deliver or archive according to DELIVERY.md",
        "complete_with_notes": "deliver with the notes named in the handoff",
        "blocked": "repair blocked checks before delivery",
    }[status]
    return {
        "status": status,
        "date": date_str,
        "edition_dir": str(edition_dir),
        "checks": checks,
        "summary": {
            "pass": sum(1 for check in checks if check.get("state") == "pass"),
            "note": sum(1 for check in checks if check.get("state") == "note"),
            "block": sum(1 for check in checks if check.get("state") == "block"),
        },
        "roles": roles,
        "page_budget": budget_policy,
        "next_action": next_action,
        "artifacts": {
            "json": str(edition_dir / "run-ticket.json"),
            "markdown": str(edition_dir / "run-ticket.md"),
        },
        "updated_at": _utc_stamp(),
    }


def _render_final_editor_markdown(report: dict[str, object]) -> str:
    findings = report.get("findings") if isinstance(report.get("findings"), list) else []
    lines = [
        f"# Final Editor - {report.get('date', '')}",
        "",
        f"Status: {report.get('status', '')}",
        f"Ship rule: {report.get('ship_rule', '')}",
        "",
        "## Findings",
    ]
    if not findings:
        lines.append("- None.")
    else:
        for item in findings:
            if not isinstance(item, dict):
                continue
            severity = str(item.get("severity", "")).upper()
            check = item.get("check", "")
            issue = item.get("issue", "")
            hint = item.get("hint", "")
            lines.append(f"- {severity} `{check}` - {issue}")
            if hint:
                lines.append(f"  Fix: {hint}")
    lines.extend(
        [
            "",
            "## Files Read",
        ]
    )
    for path in report.get("files_read", []) if isinstance(report.get("files_read"), list) else []:
        lines.append(f"- `{path}`")
    return "\n".join(lines).rstrip() + "\n"


def final_editor_pass(
    newsroom: Path,
    config: MorningPaperConfig,
    *,
    date_str: str,
) -> dict[str, object]:
    """Independent pre-delivery proof over the prepared edition workspace.

    This is not a second copy editor. It is the editor-in-chief checklist that
    reads the durable newsroom contracts plus render/review artifacts and tells
    the agent whether it can ship, needs to note something, or must revise.
    """
    root = newsroom.expanduser().resolve()
    edition_dir = root / "editions" / date_str
    if not edition_dir.is_dir():
        raise FileNotFoundError(f"missing edition directory: {edition_dir}")
    budget_policy = _page_budget_policy(root)

    spec_files = sorted((root / "specs").glob("*.md")) if (root / "specs").is_dir() else []
    contract_files = [
        root / "EDITORIAL.md",
        root / "VISUALS.md",
        root / "SOURCES.md",
        root / "DELIVERY.md",
        root / "TASTELOG.md",
        root / "preferences" / "voice.md",
        root / "preferences" / "interests.yaml",
        root / "preferences" / "source-budgets.yaml",
        root / "preferences" / "checks.yaml",
        root / "preferences" / "desk-sheet.yaml",
        edition_dir / "source-inventory.json",
        edition_dir / "collector-report.md",
        edition_dir / "queue-snapshot.json",
        edition_dir / "assignment-board.json",
        edition_dir / "assignment-board.md",
        edition_dir / "run-ticket.json",
        edition_dir / "run-ticket.md",
        edition_dir / "estimate-result.json",
        edition_dir / "render-result.json",
        edition_dir / "review.json",
        edition_dir / "visual-qa.json",
        edition_dir / "operator-answers.md",
        edition_dir / "feedback-plan.md",
    ]
    contract_files[10:10] = spec_files
    if _desk_sheet_enabled(root):
        contract_files.append(edition_dir / "desk-sheet.md")
    findings: list[dict[str, object]] = []
    files_read: list[str] = []
    if not spec_files:
        _final_finding(
            findings,
            check="section-specs",
            severity="flag",
            location=str(root / "specs"),
            issue="No section specs were found.",
            why="The final editor needs the section contracts that govern the paper.",
            hint="Run setup or restore at least one `specs/*.md` file before delivery.",
        )
    for path in contract_files:
        if path.is_file():
            files_read.append(str(path))
        else:
            _final_finding(
                findings,
                check="required-artifact",
                severity="flag",
                location=str(path),
                issue=f"Missing required final-editor input `{path.name}`.",
                why="The final editor cannot prove the paper is ready without the full newsroom and edition contract.",
                hint="Run setup/edition prepare or restore the missing artifact before delivery.",
            )

    source_inventory = _load_json_object(edition_dir / "source-inventory.json")
    queue_snapshot = _load_json_object(edition_dir / "queue-snapshot.json")
    estimate_result = _load_json_object(edition_dir / "estimate-result.json")
    render_result = _load_json_object(edition_dir / "render-result.json")
    review = _load_json_object(edition_dir / "review.json")
    visual_qa = _load_json_object(edition_dir / "visual-qa.json")

    draft_path = edition_dir / "draft.md"
    if draft_path.is_file():
        files_read.append(str(draft_path))

    roles = _role_artifacts(edition_dir)
    phases = roles.get("phases") if isinstance(roles.get("phases"), dict) else {}
    desks_dir = edition_dir / "desks"
    role_files = roles.get("files") if isinstance(roles.get("files"), list) else []
    for filename in role_files:
        role_path = desks_dir / str(filename)
        if role_path.is_file():
            files_read.append(str(role_path))
    role_blocked = roles.get("blocked") if isinstance(roles.get("blocked"), list) else []
    role_invalid = roles.get("invalid") if isinstance(roles.get("invalid"), list) else []
    if role_blocked:
        _final_finding(
            findings,
            check="desk-quality-gates",
            severity="flag",
            issue=f"{len(role_blocked)} role handoff(s) reported blocked.",
            why="The final editor should not ship over a role that explicitly said its desk could not finish.",
            hint="Repair or replace the blocked handoff before delivery.",
            measured={"blocked_roles": role_blocked},
        )
    if role_invalid:
        _final_finding(
            findings,
            check="desk-quality-gates",
            severity="nudge",
            issue=f"{len(role_invalid)} role handoff(s) need frontmatter repair.",
            why="Role artifacts are the run's memory; malformed handoffs are hard for fresh agents to trust.",
            hint="Fix the YAML frontmatter so the production record can read the desk trail.",
            measured={"invalid_roles": role_invalid},
        )

    if not estimate_result:
        _final_finding(
            findings,
            check="estimate-complete",
            severity="flag",
            issue="Page estimate artifact is missing or unreadable.",
            why="The editor needs a pre-render budget expectation before judging the final page count.",
            hint="Run `morning-paper edition estimate <newsroom> --date <date>` and save `estimate-result.json`.",
        )
    elif estimate_result.get("status") == "pending":
        _final_finding(
            findings,
            check="estimate-complete",
            severity="flag",
            issue="Page estimate is still pending.",
            why="The editor needs a pre-render budget expectation before judging the final page count.",
            hint="Run `morning-paper edition estimate <newsroom> --date <date>` and save `estimate-result.json`.",
        )
    elif estimate_result.get("status") == "error":
        _final_finding(
            findings,
            check="estimate-complete",
            severity="flag",
            issue="Page estimate failed.",
            why="A failed estimate means the editor never got a useful pre-render budget signal.",
            hint="Fix the draft or print stack, rerun the estimate, then render again.",
            measured={"error": estimate_result.get("error", "")},
        )
    elif estimate_result:
        estimate_file = Path(str(estimate_result.get("file", ""))).expanduser()
        est_mtime = float(estimate_result.get("file_mtime") or 0)
        current_mtime = estimate_file.stat().st_mtime if estimate_file.is_file() else 0
        if not estimate_file.is_file() or estimate_file.resolve() != draft_path.resolve():
            _final_finding(
                findings,
                check="artifact-freshness",
                severity="flag",
                issue="Estimate was not run against this edition's draft.",
                why="A page estimate for another file cannot prove this paper's budget.",
                hint="Run `morning-paper edition estimate` from this newsroom/date.",
                measured={"estimate_file": str(estimate_file), "draft": str(draft_path)},
            )
        elif current_mtime > est_mtime + 0.001:
            _final_finding(
                findings,
                check="artifact-freshness",
                severity="flag",
                issue="Draft changed after the page estimate.",
                why="The estimate no longer describes the draft that was rendered.",
                hint="Rerun the estimate, render, review, and final-editor.",
            )

    if render_result.get("status") == "pending":
        _final_finding(
            findings,
            check="render-complete",
            severity="flag",
            issue="Render result is still pending.",
            why="The paper must be rendered before the final editor can judge page count, outputs, or delivery.",
            hint="Run `morning-paper render`, save `render-result.json`, then run final-editor again.",
        )
    pages = _int_or_zero(render_result.get("pages"))
    if pages <= 0:
        _final_finding(
            findings,
            check="render-complete",
            severity="flag",
            issue="Render result does not report a positive page count.",
            why="A paper with no proven pages is not ready to hand to the reader.",
            hint="Re-render and confirm the PDF exists.",
        )
    target_pages = int(budget_policy["target_pages"])
    max_pages = int(budget_policy["max_pages"])
    if pages > max_pages:
        _final_finding(
            findings,
            check="page-budget",
            severity="flag",
            issue=f"Rendered paper is {pages} pages against a {max_pages}-page max.",
            why="The reader asked for a finite paper; overshooting the max should be an explicit editorial decision.",
            hint="Cut or compress the weakest material, or record the intentional exception in DELIVERY.md or preferences/source-budgets.yaml.",
            measured={
                "pages": pages,
                "target_pages": target_pages,
                "max_pages": max_pages,
                "budget_source": budget_policy["source"],
            },
        )
    elif pages > target_pages:
        _final_finding(
            findings,
            check="page-budget",
            severity="nudge",
            issue=f"Rendered paper is {pages} pages against a {target_pages}-page target.",
            why="A small overage can ship, but the editor should name the tradeoff.",
            hint="Mention the overage in the handoff or cut a weak item.",
            measured={
                "pages": pages,
                "target_pages": target_pages,
                "max_pages": max_pages,
                "budget_source": budget_policy["source"],
            },
        )
    if pages >= SUBSTANTIAL_PAGE_THRESHOLD:
        missing = _missing_substantial_phases(roles)
        if missing:
            _final_finding(
                findings,
                check="desk-quality-gates",
                severity="flag",
                issue="Substantial edition is missing " + ", ".join(missing) + ".",
                why="A real edition needs separate selection, copy, and art judgment; reporter output alone is not enough.",
                hint="Run the editor, copy desk, and art desk passes and save their `desks/` handoffs before final-editor.",
                measured={"pages": pages, "missing": missing},
            )
        elif pages >= SUBSTANTIAL_PAGE_THRESHOLD and not phases:
            _final_finding(
                findings,
                check="desk-quality-gates",
                severity="flag",
                issue="Substantial edition has no readable role phases.",
                why="The final editor cannot prove who selected, copy-edited, or visually checked the paper.",
                hint="Save role handoffs in `editions/<date>/desks/` before delivery.",
                measured={"pages": pages},
            )

    outputs = render_result.get("outputs") if isinstance(render_result.get("outputs"), dict) else {}
    pdf_path = Path(str(outputs.get("pdf", ""))).expanduser() if outputs else Path()
    if not outputs or not pdf_path.is_file():
        _final_finding(
            findings,
            check="delivery-proof",
            severity="flag",
            issue="Rendered PDF path is missing or does not exist.",
            why="Delivery starts with a real PDF, not a successful command transcript.",
            hint="Re-render the edition and verify the `outputs.pdf` path.",
        )
    elif pdf_path.is_file():
        pdf_proof = pdf_basic_proof(pdf_path)
        if not pdf_proof.get("ok"):
            _final_finding(
                findings,
                check="delivery-proof",
                severity="flag",
                issue="Rendered PDF exists but is not a readable positive-page PDF.",
                why="A path on disk is not enough proof that the reader can receive a real paper.",
                hint="Re-render the edition, then run visual QA again.",
                measured={"pdf": pdf_proof},
            )
        else:
            proven_pages = _int_or_zero(pdf_proof.get("pages"))
            if pages > 0 and proven_pages > 0 and proven_pages != pages:
                _final_finding(
                    findings,
                    check="delivery-proof",
                    severity="flag",
                    issue=f"Render result reports {pages} page(s), but the PDF proof found {proven_pages}.",
                    why="The render artifact and the file on disk must describe the same paper.",
                    hint="Re-render the edition and rerun review, visual QA, and final-editor.",
                    measured={"render_pages": pages, "pdf_pages": proven_pages, "pdf": str(pdf_path)},
                )

    rendered_markdown = Path(str(outputs.get("markdown", ""))).expanduser() if outputs and outputs.get("markdown") else Path()
    if rendered_markdown and not rendered_markdown.is_file():
        _final_finding(
            findings,
            check="artifact-freshness",
            severity="flag",
            issue="Render result points to a missing rendered markdown artifact.",
            why="Review and final-editor need to know exactly which composed artifact was delivered.",
            hint="Re-render the edition and save the fresh render result.",
            measured={"markdown": str(rendered_markdown)},
        )
    elif rendered_markdown.is_file() and draft_path.is_file() and rendered_markdown.stat().st_mtime + 0.001 < draft_path.stat().st_mtime:
        _final_finding(
            findings,
            check="artifact-freshness",
            severity="flag",
            issue="Rendered markdown is older than draft.md.",
            why="The delivered paper may not include the latest draft changes.",
            hint="Re-render, re-review, then run final-editor again.",
        )

    if estimate_result.get("status") == "estimated" and pages > 0:
        est_pages = _int_or_zero(estimate_result.get("est_pages"))
        drift = abs(est_pages - pages)
        if drift > 2:
            _final_finding(
                findings,
                check="estimate-drift",
                severity="flag",
                issue=f"Estimate was {est_pages} page(s), render was {pages}.",
                why="Large estimate/render drift means the page budget proof is not trustworthy.",
                hint="Inspect custom CSS, images, or style choices, then rerun estimate/render.",
                measured={"est_pages": est_pages, "render_pages": pages, "drift": drift},
            )

    if review.get("status") == "pending":
        _final_finding(
            findings,
            check="review-complete",
            severity="flag",
            issue="Editorial review is still pending.",
            why="The copy/art desk must run before the final editor decides to ship.",
            hint="Run `morning-paper review <edition-dir> --json` and save `review.json`.",
        )
    elif review.get("status") == "review":
        _final_finding(
            findings,
            check="review-status",
            severity="flag",
            issue="Editorial review requested revision.",
            why="A review flag means the agent should revise or record an explicit rationale before delivery.",
            hint="Address the flagged review findings, re-render, re-review, then run final-editor again.",
            measured={"review_summary": review.get("summary", {})},
        )
    elif review.get("status") == "notes":
        _final_finding(
            findings,
            check="review-status",
            severity="nudge",
            issue="Editorial review has notes.",
            why="Notes can ship, but the handoff should summarize what the editor noticed.",
            hint="Include a one-line review-note summary when delivering the PDF.",
            measured={"review_summary": review.get("summary", {})},
        )
    review_artifacts = review.get("edition", {}).get("artifacts", {}) if isinstance(review.get("edition"), dict) else {}
    reviewed_markdown: Path | None = None
    if isinstance(review_artifacts, dict) and review_artifacts.get("markdown"):
        reviewed_markdown = Path(str(review_artifacts.get("markdown", ""))).expanduser()
    if rendered_markdown.is_file() and reviewed_markdown is None and review.get("status") not in {"pending", None}:
        _final_finding(
            findings,
            check="artifact-freshness",
            severity="flag",
            issue="Review artifact does not name the rendered markdown it inspected.",
            why="A review without an artifact path cannot prove it inspected the delivered paper.",
            hint="Run `morning-paper review <render-output-dir> --json` and save `review.json`.",
        )
    elif (
        rendered_markdown.is_file()
        and reviewed_markdown is not None
        and reviewed_markdown.expanduser().resolve() != rendered_markdown.expanduser().resolve()
    ):
        _final_finding(
            findings,
            check="artifact-freshness",
            severity="flag",
            issue="Review did not inspect the rendered markdown from render-result.json.",
            why="A clean review only proves readiness if it reviewed the artifact being delivered.",
            hint="Run `morning-paper review <render-output-dir> --json` and save `review.json`.",
            measured={"rendered_markdown": str(rendered_markdown), "reviewed_markdown": str(reviewed_markdown)},
        )
    review_json_path = edition_dir / "review.json"
    render_json_path = edition_dir / "render-result.json"
    if review_json_path.is_file() and render_json_path.is_file() and review_json_path.stat().st_mtime + 0.001 < render_json_path.stat().st_mtime:
        _final_finding(
            findings,
            check="artifact-freshness",
            severity="flag",
            issue="Review artifact is older than render-result.json.",
            why="The review may not describe the latest render.",
            hint="Rerun review after rendering, then run final-editor.",
        )

    if not visual_qa:
        _final_finding(
            findings,
            check="visual-qa",
            severity="flag",
            issue="Visual QA artifact is missing or unreadable.",
            why="The final editor should inspect the rendered PDF surface, not only markdown metadata.",
            hint="Run `morning-paper edition visual-qa <newsroom> --date <date>` after render.",
        )
    elif visual_qa.get("status") == "pending":
        _final_finding(
            findings,
            check="visual-qa",
            severity="flag",
            issue="Visual QA is still pending.",
            why="The final editor should inspect the rendered PDF surface, not only markdown metadata.",
            hint="Run `morning-paper edition visual-qa <newsroom> --date <date>` after render.",
        )
    elif visual_qa.get("status") == "fail":
        _final_finding(
            findings,
            check="visual-qa",
            severity="flag",
            issue="Visual QA failed.",
            why="A failed raster/PDF check means the paper on screen may be blank or broken.",
            hint="Fix the render output, rerun visual QA, then run final-editor.",
            measured={"visual_qa_summary": visual_qa.get("findings", [])},
        )
    elif visual_qa.get("status") == "notes":
        _final_finding(
            findings,
            check="visual-qa",
            severity="nudge",
            issue="Visual QA completed with notes.",
            why="The paper can ship, but the handoff should mention the visual proof limitation.",
            hint="Name the visual QA note in the final handoff.",
            measured={"visual_qa_summary": visual_qa.get("findings", [])},
        )
    elif visual_qa:
        qa_pdf = visual_qa.get("pdf") if isinstance(visual_qa.get("pdf"), dict) else {}
        qa_pdf_path = Path(str(qa_pdf.get("path", ""))).expanduser() if qa_pdf else Path()
        if qa_pdf and qa_pdf_path.resolve() != pdf_path.resolve():
            _final_finding(
                findings,
                check="artifact-freshness",
                severity="flag",
                issue="Visual QA inspected a different PDF than render-result.json.",
                why="Visual QA only proves delivery if it inspected the PDF being handed to the reader.",
                hint="Rerun visual QA against the current render result.",
                measured={"visual_qa_pdf": qa_pdf.get("path", ""), "render_pdf": str(pdf_path)},
            )
    visual_findings = [
        item
        for item in review.get("findings", [])
        if isinstance(item, dict) and item.get("check") == "visual-provenance"
    ] if isinstance(review.get("findings"), list) else []
    if visual_findings:
        _final_finding(
            findings,
            check="visual-fit",
            severity="flag" if any(item.get("severity") == "flag" for item in visual_findings) else "nudge",
            issue=f"Review found {len(visual_findings)} visual provenance/layout issue(s).",
            why="The final editor exists partly to catch visuals that waste measure, lack provenance, or break print trust.",
            hint="Fix captions/source notes/widths or record why the visual still earns space.",
            measured={"visual_findings": len(visual_findings)},
        )

    newsroom_info = source_inventory.get("newsroom") if isinstance(source_inventory.get("newsroom"), dict) else {}
    local_drop = newsroom_info.get("local_drop") if isinstance(newsroom_info.get("local_drop"), dict) else {}
    unsupported = _int_or_zero(local_drop.get("unsupported_count")) if isinstance(local_drop, dict) else 0
    if unsupported > 0:
            _final_finding(
                findings,
                check="source-honesty",
                severity="nudge",
                issue=f"{unsupported} local-drop file(s) need a converter collector.",
                why="The paper can ship, but the reader should know some owned sources were visible and not assigned to the edition.",
                hint="Name the skipped files and propose a converter collector for tomorrow.",
                measured={"unsupported_local_drop": unsupported},
            )
    if isinstance(queue_snapshot.get("items"), list):
        flagged_items = [
            item for item in queue_snapshot["items"]
            if isinstance(item, dict) and (item.get("truncated") or item.get("warning") or item.get("extractor_note"))
        ]
        if flagged_items:
            _final_finding(
                findings,
                check="source-honesty",
                severity="nudge",
                issue=f"{len(flagged_items)} Assignment Board item(s) carry truncation or remote-extraction notes.",
                why="The final handoff should not let clipped or remote-fetched material masquerade as complete/local.",
                hint="Surface the warning in the paper or cut the item.",
                measured={"flagged_staged_items": len(flagged_items)},
            )

    feedback_plan = edition_dir / "feedback-plan.md"
    operator_answers = edition_dir / "operator-answers.md"
    if feedback_plan.is_file() and "Applied Feedback" not in feedback_plan.read_text(encoding="utf-8"):
        _final_finding(
            findings,
            check="feedback-route",
            severity="flag",
            issue="Feedback plan does not expose an Applied Feedback section.",
            why="The reader's notes need a durable route back into newsroom taste after delivery.",
            hint="Regenerate or repair `feedback-plan.md` before handoff.",
        )
    if operator_answers.is_file() and "## Visuals" not in operator_answers.read_text(encoding="utf-8"):
        _final_finding(
            findings,
            check="feedback-route",
            severity="nudge",
            issue="Operator answers sheet is missing the Visuals prompt.",
            why="The desk-sheet should ask about content, layout, sources, delivery, and taste.",
            hint="Refresh `operator-answers.md` with `morning-paper edition prepare --force` or repair it manually.",
        )

    status = _final_status(findings)
    ship_rule = {
        "clean": "deliver",
        "notes": "deliver with a short final-editor note",
        "review": "revise or record an explicit rationale before delivery",
    }[status]
    report: dict[str, object] = {
        "status": status,
        "date": date_str,
        "edition_dir": str(edition_dir),
        "ship_rule": ship_rule,
        "summary": _final_summary(findings),
        "findings": findings,
        "files_read": files_read,
        "artifacts": {
            "json": str(edition_dir / "final-editor.json"),
            "markdown": str(edition_dir / "final-editor.md"),
        },
        "updated_at": _utc_stamp(),
    }
    (edition_dir / "final-editor.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (edition_dir / "final-editor.md").write_text(_render_final_editor_markdown(report), encoding="utf-8")
    return report


def operator_answers_template(date_str: str) -> str:
    return f"""# Operator Answers - {date_str}

Read the paper with a pen. Reply in chat or mark this file up.

## Keep
- What should continue?

## Cut
- What felt low-signal, too long, too repetitive, or not yours?

## More
- What should get more pages, deeper reporting, or a recurring section?

## Visuals
- What chart, image, diagram, illustration, or layout choice helped or hurt?

## Sources To Add
- Feeds, folders, newsletters, repos, people, searches, exports, or tools.

## Delivery
- Did the PDF, printout, or email/article format land the way it should?

## Taste To Save
- Which note should become a durable rule in EDITORIAL.md, VISUALS.md,
  SOURCES.md, DELIVERY.md, specs/, preferences/, or TASTELOG.md?

## Tomorrow's Assignment Board
- URLs or files to add to tomorrow's Assignment Board.
"""


def desk_sheet_template(date_str: str, paper_name: str, prefs: dict[str, object] | None = None) -> str:
    prefs = prefs or dict(DEFAULT_DESK_SHEET_PREFS)
    notes_lines = max(8, min(16, int(prefs.get("notes_lines") or 14)))
    ask_count = max(1, min(4, int(prefs.get("ask_count") or 4)))
    tomorrow_choices = max(1, min(8, int(prefs.get("tomorrow_choices") or 5)))
    ask_rows = [
        (
            "Q1",
            "What should the paper keep, cut, or make clearer tomorrow?",
            ("keep", "change"),
        ),
        (
            "Q2",
            "Did the visual pass help you understand the day faster?",
            ("yes", "tune"),
        ),
        (
            "Q3",
            "Which source, section, or thread should get more space next time?",
            ("more", "less"),
        ),
        (
            "Q4",
            "Should any note become durable taste?",
            ("save", "one-off"),
        ),
    ][:ask_count]
    ask_html = "\n".join(
        '<div class="old-ask"><div class="old-code">{code}</div><div class="old-q">{question}</div>'
        '<div class="old-opts">{options}</div></div>'.format(
            code=code,
            question=question,
            options="".join(f'<span><span class="old-box"></span>{option}</span>' for option in options),
        )
        for code, question, options in ask_rows
    )
    menu_html = "".join(
        f'<span><span class="old-box"></span>M{number}</span>' for number in range(1, tomorrow_choices + 1)
    )
    return f"""---
title: The Desk Sheet - {date_str}
style: broadsheet
palette: mono
---

<style>
@page {{
  size: Letter;
  margin: 0.45in;
  @top-left {{ content: none; }}
  @top-right {{ content: none; }}
  @bottom-left {{ content: none; }}
  @bottom-center {{ content: none; }}
  @bottom-right {{ content: none; }}
}}
@page :first {{
  size: Letter;
  margin: 0.45in;
  @top-left {{ content: none; }}
  @top-right {{ content: none; }}
  @bottom-left {{ content: none; }}
  @bottom-center {{ content: none; }}
  @bottom-right {{ content: none; }}
}}
@page :left {{
  size: Letter;
  margin: 0.45in;
  @top-left {{ content: none; }}
  @top-right {{ content: none; }}
  @bottom-left {{ content: none; }}
  @bottom-center {{ content: none; }}
  @bottom-right {{ content: none; }}
}}
@page :right {{
  size: Letter;
  margin: 0.45in;
  @top-left {{ content: none; }}
  @top-right {{ content: none; }}
  @bottom-left {{ content: none; }}
  @bottom-center {{ content: none; }}
  @bottom-right {{ content: none; }}
}}
body {{ color: #1f1d1b; }}
.old-desk {{ position: relative; width: 7.6in; height: 10.1in; margin: 0 auto; font-family: Georgia, serif; }}
.old-corner {{ position: absolute; width: 0.18in; height: 0.18in; border-color: #1f1d1b; }}
.old-tl {{ top: 0; left: 0; border-left: 2px solid; border-top: 2px solid; }}
.old-tr {{ top: 0; right: 0; border-right: 2px solid; border-top: 2px solid; }}
.old-bl {{ bottom: 0; left: 0; border-left: 2px solid; border-bottom: 2px solid; }}
.old-br {{ bottom: 0; right: 0; width: 0.08in; height: 0.08in; background: #1f1d1b; }}
.old-head {{ text-align: center; padding-top: 0.05in; }}
.old-title {{ font-size: 20pt; line-height: 1; }}
.old-meta {{ margin-top: 0.05in; font: 700 8.5pt/1.2 Arial, sans-serif; letter-spacing: 0.12em; text-transform: uppercase; }}
.old-sub {{ margin-top: 0.03in; font: 700 7.2pt/1.2 Arial, sans-serif; color: #777; letter-spacing: 0.08em; text-transform: uppercase; }}
.old-codes {{ margin-top: 0.08in; padding-bottom: 0.04in; border-bottom: 1px solid #777; font: 7.8pt/1.2 Arial, sans-serif; color: #666; letter-spacing: 0.06em; text-transform: uppercase; }}
.old-band {{ display: flex; align-items: baseline; justify-content: space-between; margin-top: 0.09in; font: 700 9pt/1.2 Arial, sans-serif; letter-spacing: 0.16em; text-transform: uppercase; }}
.old-count {{ color: #666; letter-spacing: 0.03em; }}
.old-lines {{ height: 4.9in; margin-top: 0.22in; border-bottom: 1px solid #777; background-image: repeating-linear-gradient(to bottom, transparent 0, transparent 0.34in, #e9dfd4 0.35in); }}
.old-asks {{ padding-top: 0.08in; border-bottom: 1px solid #777; }}
.old-ask {{ display: grid; grid-template-columns: 0.5in 1fr 2.25in; column-gap: 0.1in; align-items: center; min-height: 0.43in; border-bottom: 1px dotted #eadfd4; }}
.old-ask:last-child {{ border-bottom: none; }}
.old-code {{ font: 700 13pt/1 Georgia, serif; }}
.old-q {{ font-size: 10.2pt; line-height: 1.18; }}
.old-opts {{ display: flex; gap: 0.22in; justify-content: flex-end; align-items: center; font: 700 7pt/1 Arial, sans-serif; color: #666; text-transform: uppercase; }}
.old-box {{ display: inline-block; width: 0.13in; height: 0.13in; border: 1.5px solid #222; vertical-align: -0.03in; margin-right: 0.04in; }}
.old-tomorrow {{ margin-top: 0.08in; padding-top: 0.08in; }}
.old-read-row {{ display: flex; align-items: center; gap: 0.14in; margin-top: 0.14in; font: 700 8pt/1 Arial, sans-serif; text-transform: uppercase; }}
.old-menu {{ margin-left: 0.2in; display: flex; gap: 0.16in; font: 8pt/1 Arial, sans-serif; }}
.old-hint {{ margin-left: auto; font-style: italic; font-size: 8.5pt; color: #777; text-transform: none; }}
.old-url {{ margin-top: 0.15in; display: grid; grid-template-columns: 1.1in 1fr; column-gap: 0.1in; align-items: end; font: 700 7pt/1 Arial, sans-serif; color: #666; letter-spacing: 0.07em; text-transform: uppercase; }}
.old-write {{ height: 0.32in; border-bottom: 1px dotted #eadfd4; }}
.old-write.second {{ margin-left: 0.52in; margin-top: 0.12in; width: calc(100% - 1in); }}
</style>

<div class="old-desk">
  <div class="old-corner old-tl"></div>
  <div class="old-corner old-tr"></div>
  <div class="old-corner old-bl"></div>
  <div class="old-corner old-br"></div>

  <div class="old-head">
    <div class="old-title">The Desk Sheet</div>
    <div class="old-meta">{date_str} - {paper_name}</div>
    <div class="old-sub">Photograph or dictate when done</div>
    <div class="old-codes">Codes in this paper: A analysis - S sources - B bets - T telemetry - R reads - M menu - Z back page</div>
  </div>

  <div class="old-band"><div>Notes - add a code (Q1, A, R2, P7) when it helps</div><div class="old-count">Notes - {notes_lines}</div></div>
  <div class="old-lines"></div>

  <div class="old-band"><div>The paper asks - tick or scribble</div><div class="old-count">Asks - {ask_count}</div></div>
  <div class="old-asks">
    {ask_html}
  </div>

  <div class="old-band"><div>Tomorrow - pick, paste, or steer</div><div class="old-count">TMRW - {tomorrow_choices}</div></div>
  <div class="old-tomorrow">
    <div class="old-read-row"><div>Tomorrow's deep read</div><div class="old-menu">{menu_html}</div><div class="old-hint">menu's in the Reading section - or write your own below</div></div>
    <div class="old-url"><div>A URL or a title</div><div class="old-write"></div></div>
    <div class="old-write second"></div>
  </div>
</div>
"""


def feedback_plan_template(date_str: str) -> str:
    route_rows = "\n".join(
        f"| {label} | `{target}` (`--route {route}`) |"
        for label, route, target in FEEDBACK_ROUTE_GUIDANCE
    )
    return f"""# Feedback Plan - {date_str}

Use this after the reader marks up `operator-answers.md` or replies in chat.
The goal is not to preserve every reaction. The goal is to turn stable feedback
into the smallest durable newsroom change that makes tomorrow's paper better.

## Process

1. Read `operator-answers.md` and the reader's chat/photo notes.
2. Group each note by route below.
3. Update the smallest durable file that can carry the rule.
4. Append one line to `TASTELOG.md` for every accepted or rejected durable
   taste change.
5. Add anything under "Tomorrow's Assignment Board" with `morning-paper stage <url-or-file>`.
6. Leave a short "Applied Feedback" note in this file with paths changed.

## Routes

| Reader note | Durable target |
|---|---|
{route_rows}
| One-off URL or file to read tomorrow | `morning-paper stage <url-or-file>` adds it to the Assignment Board |

## Guardrails

- Do not overfit one annoyed note into a permanent rule. Save as durable taste
  only when the reader asks, repeats it, or the paper clearly benefits.
- Do not store private source content in the public engine repo.
- Do not erase a source because it was empty once. Record failure and next
  action in `SOURCES.md`.
- If feedback conflicts with an existing rule, update `TASTELOG.md` with the
  decision and why the older rule changed.
- YAML targets (`preferences/interests.yaml`,
  `preferences/source-budgets.yaml`, `preferences/checks.yaml`) receive feedback
  as comments so the file stays parseable. Promote the note into real YAML only
  when the exact setting is clear.

## Applied Feedback

No feedback applied yet.
"""


def desks_readme_template(date_str: str) -> str:
    return f"""# Desk Artifacts - {date_str}

This folder is the newsroom handoff trail for today's edition. Use it when the
host supports subagents, profiles, or separate context windows. A tiny/simple
run can ship without role artifacts. A substantial edition (8+ pages, or
any run with broad source coverage) must leave enough here for a fresh agent to
understand who reported, selected, copy-edited, designed, and produced the
paper.

## File Pattern

- `01-orchestrator.md`
- `02-assignment-editor.md`
- `03.1-x-reporter.md`
- `03.2-articles-reporter.md`
- `03.3-email-reporter.md`
- `04-editor.md`
- `05-copy-desk.md`
- `06-art-desk.md`
- `07-producer.md`
- `08-taste-editor.md`

Use `03.1`, `03.2`, `03.3`, and so on for beat reporters that run in parallel.
Rename the beat, not the role: `03.1-shopify-reporter.md`,
`03.2-frontier-agents-reporter.md`, `03.3-work-reporter.md`.

## Substantial Edition Gates

For a substantial edition, these late desks are required:

- `04-editor.md` - selection, cuts, page/source budgets, repeat checks.
- `05-copy-desk.md` - language, labels, headlines, source clarity, voice.
- `06-art-desk.md` - visual choices, page shape, PDF readability.
- `07-producer.md` - after final-editor/status, proves the run can ship.

Page budgets are ceilings and appetite signals, not quotas. If the source
material is thin, ship the thinner honest paper with a source-health note.
Never add filler or extra process pages to hit a target.

## Artifact Contract

Each role leaves one markdown file with YAML frontmatter and a short body.
Do not split the handoff into separate JSON and markdown files.

```markdown
---
role: x-reporter
phase: "03.1"
status: ready
date: {date_str}
inputs:
  - source-inventory.json
  - assignment-board.json
handoff:
  candidates: 8
  repeats_cut: 2
  needs_followup: false
---

## What I Checked
- Source or search surface, date range, commands, and limits.

## Findings
- Source-backed findings, with URLs or local paths.

## Candidates
- Items that might earn ink, with why they matter and repeat risk.

## Cuts
- Interesting material that should not print today.

## Handoff
- What the next role should know.
```

## Role References

Start at the public repo's `ROLES.md`, then use `docs/roles/` for the specific
role you are running. The orchestrator owns the loop; roles own their handoff.
"""


def draft_template(date_str: str, paper_name: str) -> str:
    return f"""# {paper_name} - {date_str}

<!-- Draft starts here. Compose against EDITORIAL.md, VISUALS.md, SOURCES.md,
DELIVERY.md, specs/, preferences/, source-inventory.json, collector-report.md,
and assignment-board.json. Replace this placeholder before rendering. -->

## The Read

Not composed yet.
"""


def _write(path: Path, text: str, *, force: bool = False) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not force:
        return "skipped"
    path.write_text(text.rstrip() + "\n", encoding="utf-8")
    return "written"


def _write_json(path: Path, payload: dict, *, force: bool = False) -> str:
    return _write(path, json.dumps(payload, indent=2), force=force)


def _append_section_note(path: Path, *, heading: str, note: str) -> None:
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    if heading not in text:
        text = text.rstrip() + f"\n\n{heading}\n"
    text = text.rstrip() + f"\n- {note}\n"
    path.write_text(text, encoding="utf-8")


def _append_feedback_note(path: Path, *, note: str) -> None:
    if path.suffix.lower() in {".yaml", ".yml"}:
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        if "# Feedback Notes" not in text:
            text = text.rstrip() + "\n\n# Feedback Notes\n"
        text = text.rstrip() + f"\n# - {note}\n"
        path.write_text(text, encoding="utf-8")
        return
    _append_section_note(path, heading="## Feedback Notes", note=note)


def _append_applied_feedback(feedback_plan: Path, line: str, *, date_str: str) -> None:
    if not feedback_plan.exists():
        feedback_plan.write_text(feedback_plan_template(date_str).rstrip() + "\n", encoding="utf-8")
    text = feedback_plan.read_text(encoding="utf-8")
    text = text.replace("No feedback applied yet.", "").rstrip()
    text = text + f"\n- {line}\n"
    feedback_plan.write_text(text, encoding="utf-8")


def apply_feedback(
    newsroom: Path,
    *,
    date_str: str,
    route: str,
    note: str,
    decision: str = "accepted",
    why: str = "",
) -> dict[str, object]:
    root = newsroom.expanduser().resolve()
    route_key = route.strip().lower()
    if route_key not in FEEDBACK_ROUTES:
        raise ValueError(f"route must be one of: {', '.join(sorted(FEEDBACK_ROUTES))}")
    decision_key = decision.strip().lower()
    if decision_key not in {"accepted", "rejected"}:
        raise ValueError("decision must be accepted or rejected")
    clean_note = " ".join(note.split())
    if not clean_note:
        raise ValueError("note is required")
    clean_why = " ".join(why.split()) or "recorded from reader feedback"

    target_relative = FEEDBACK_ROUTES[route_key]
    target = root / target_relative
    if not target.exists():
        raise FileNotFoundError(f"missing newsroom file: {target}")

    stamp = datetime.now(timezone.utc).date().isoformat()
    target_line = f"{stamp} - {decision_key} - {clean_note} ({clean_why})"
    changed_paths: list[str] = []
    if target.name != "TASTELOG.md":
        _append_feedback_note(target, note=target_line)
        changed_paths.append(str(target))

    taste_log = root / "TASTELOG.md"
    if not taste_log.exists():
        raise FileNotFoundError(f"missing newsroom file: {taste_log}")
    taste_line = f"{stamp} - {decision_key} - {clean_note} - {target_relative} - {clean_why}"
    _append_section_note(taste_log, heading="## Entries", note=taste_line)
    changed_paths.append(str(taste_log))

    feedback_plan = root / "editions" / date_str / "feedback-plan.md"
    applied_line = f"{decision_key} `{route_key}` feedback -> `{target_relative}`; paths changed: {', '.join(changed_paths)}"
    _append_applied_feedback(feedback_plan, applied_line, date_str=date_str)
    changed_paths.append(str(feedback_plan))

    return {
        "status": "applied",
        "date": date_str,
        "route": route_key,
        "decision": decision_key,
        "target": str(target),
        "target_relative": target_relative,
        "taste_log": str(taste_log),
        "feedback_plan": str(feedback_plan),
        "paths_changed": changed_paths,
        "note": clean_note,
    }


def assignment_board_edition_workspace(
    newsroom: Path,
    config: MorningPaperConfig,
    *,
    date_str: str,
) -> dict[str, object]:
    root = newsroom.expanduser().resolve()
    edition_dir = root / "editions" / date_str
    if not edition_dir.is_dir():
        raise FileNotFoundError(f"missing edition directory: {edition_dir}")
    source_payload = _load_json_object(edition_dir / "source-inventory.json")
    if not source_payload:
        source_payload = source_inventory(config, check=False, newsroom=root)
        write_json(edition_dir / "source-inventory.json", source_payload)
    queue_snapshot = _load_json_object(edition_dir / "queue-snapshot.json")
    if not queue_snapshot:
        budget_policy = _page_budget_policy(root)
        queue_snapshot = queue_status(
            config,
            date_str,
            page_budget=int(budget_policy["target_pages"]),
            max_pages=int(budget_policy["max_pages"]),
        )
        write_json(edition_dir / "queue-snapshot.json", queue_snapshot)
    board = _assignment_board(source_payload, queue_snapshot, date_str=date_str, edition_dir=edition_dir)
    write_json(edition_dir / "assignment-board.json", board)
    (edition_dir / "assignment-board.md").write_text(_render_assignment_board_markdown(board), encoding="utf-8")
    return board


def run_ticket_edition_workspace(
    newsroom: Path,
    config: MorningPaperConfig,
    *,
    date_str: str,
) -> dict[str, object]:
    root = newsroom.expanduser().resolve()
    ticket = _build_run_ticket(root, config, date_str=date_str)
    edition_dir = root / "editions" / date_str
    write_json(edition_dir / "run-ticket.json", ticket)
    (edition_dir / "run-ticket.md").write_text(_render_run_ticket_markdown(ticket), encoding="utf-8")
    return ticket


def prepare_edition_workspace(
    newsroom: Path,
    config: MorningPaperConfig,
    *,
    date_str: str,
    check_sources: bool = False,
    force: bool = False,
) -> dict[str, object]:
    root = newsroom.expanduser().resolve()
    edition_dir = root / "editions" / date_str
    edition_dir.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    skipped: list[str] = []

    def record(relative: str, status: str) -> None:
        (written if status == "written" else skipped).append(relative)

    source_payload = source_inventory(config, check=check_sources, newsroom=root)
    record("source-inventory.json", _write_json(edition_dir / "source-inventory.json", source_payload, force=force))

    collector_report = f"""# Collector Report - {date_str}

Status: not run by `morning-paper edition prepare`.

Run from the newsroom root:

```bash
collectors/run_all.sh {date_str}
morning-paper queue list --date {date_str}
```

Paste or summarize collector output here before composing. Missing collectors
must be reported as "not configured"; never invent source data.
"""
    record("collector-report.md", _write(edition_dir / "collector-report.md", collector_report, force=force))

    budget_policy = _page_budget_policy(root)
    queue_payload = queue_status(
        config,
        date_str,
        page_budget=int(budget_policy["target_pages"]),
        max_pages=int(budget_policy["max_pages"]),
    )
    record("queue-snapshot.json", _write_json(edition_dir / "queue-snapshot.json", queue_payload, force=force))
    board = _assignment_board(source_payload, queue_payload, date_str=date_str, edition_dir=edition_dir)
    record("assignment-board.json", _write_json(edition_dir / "assignment-board.json", board, force=force))
    record("assignment-board.md", _write(edition_dir / "assignment-board.md", _render_assignment_board_markdown(board), force=force))
    record("desks/README.md", _write(edition_dir / "desks" / "README.md", desks_readme_template(date_str), force=force))
    record("draft.md", _write(edition_dir / "draft.md", draft_template(date_str, config.name), force=force))

    render_pending = {
        "status": "pending",
        "date": date_str,
        "command": f"morning-paper render {edition_dir / 'draft.md'} --date {date_str} --id edition",
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    estimate_pending = {
        "status": "pending",
        "date": date_str,
        "command": f"morning-paper edition estimate {root} --date {date_str}",
        "updated_at": _utc_stamp(),
    }
    record("estimate-result.json", _write_json(edition_dir / "estimate-result.json", estimate_pending, force=force))
    record("render-result.json", _write_json(edition_dir / "render-result.json", render_pending, force=force))

    review_pending = {
        "status": "pending",
        "date": date_str,
        "command": f"morning-paper review {edition_dir} --json",
        "updated_at": _utc_stamp(),
    }
    record("review.json", _write_json(edition_dir / "review.json", review_pending, force=force))

    visual_qa_pending = {
        "status": "pending",
        "date": date_str,
        "command": f"morning-paper edition visual-qa {root} --date {date_str}",
        "updated_at": _utc_stamp(),
    }
    record("visual-qa.json", _write_json(edition_dir / "visual-qa.json", visual_qa_pending, force=force))

    final_editor_pending = {
        "status": "pending",
        "date": date_str,
        "command": f"morning-paper edition final-editor {root} --date {date_str}",
        "updated_at": _utc_stamp(),
    }
    record("final-editor.json", _write_json(edition_dir / "final-editor.json", final_editor_pending, force=force))
    final_editor_markdown = f"""# Final Editor - {date_str}

Status: pending

Run after render and review:

```bash
morning-paper edition final-editor {root} --date {date_str}
```
"""
    record("final-editor.md", _write(edition_dir / "final-editor.md", final_editor_markdown, force=force))
    delivery_pending = {
        "status": "pending",
        "date": date_str,
        "updated_at": _utc_stamp(),
        "note": "Write delivery proof here after print, Telegram, email, or other private delivery. Use status delivered, skipped, or not_configured.",
    }
    record("delivery-result.json", _write_json(edition_dir / "delivery-result.json", delivery_pending, force=force))
    run_ticket_pending = _pending_run_ticket(root, date_str=date_str)
    record("run-ticket.json", _write_json(edition_dir / "run-ticket.json", run_ticket_pending, force=force))
    record("run-ticket.md", _write(edition_dir / "run-ticket.md", _render_run_ticket_markdown(run_ticket_pending), force=force))

    record("operator-answers.md", _write(edition_dir / "operator-answers.md", operator_answers_template(date_str), force=force))
    desk_sheet_prefs = _load_desk_sheet_preferences(root)
    desk_sheet_path = edition_dir / "desk-sheet.md"
    if desk_sheet_prefs.get("enabled"):
        record("desk-sheet.md", _write(desk_sheet_path, desk_sheet_template(date_str, config.name, desk_sheet_prefs), force=force))
    record("feedback-plan.md", _write(edition_dir / "feedback-plan.md", feedback_plan_template(date_str), force=force))

    payload = {
        "edition_dir": str(edition_dir),
        "date": date_str,
        "written": written,
        "skipped": skipped,
        "artifacts": {
            "source_inventory": str(edition_dir / "source-inventory.json"),
            "collector_report": str(edition_dir / "collector-report.md"),
            "queue_snapshot": str(edition_dir / "queue-snapshot.json"),
            "assignment_board": str(edition_dir / "assignment-board.json"),
            "assignment_board_markdown": str(edition_dir / "assignment-board.md"),
            "desks_readme": str(edition_dir / "desks" / "README.md"),
            "estimate_result": str(edition_dir / "estimate-result.json"),
            "draft": str(edition_dir / "draft.md"),
            "render_result": str(edition_dir / "render-result.json"),
            "review": str(edition_dir / "review.json"),
            "visual_qa": str(edition_dir / "visual-qa.json"),
            "final_editor": str(edition_dir / "final-editor.json"),
            "final_editor_markdown": str(edition_dir / "final-editor.md"),
            "delivery_result": str(edition_dir / "delivery-result.json"),
            "run_ticket": str(edition_dir / "run-ticket.json"),
            "run_ticket_markdown": str(edition_dir / "run-ticket.md"),
            "operator_answers": str(edition_dir / "operator-answers.md"),
            "feedback_plan": str(edition_dir / "feedback-plan.md"),
        },
        "next_action": "run collectors, refresh queue-snapshot.json and assignment-board.json, compose draft.md, render desk-sheet.md if enabled, estimate, render, review, visual-qa, final-editor, run edition status, then ask for feedback and route it through feedback-plan.md",
    }
    if desk_sheet_prefs.get("enabled"):
        payload["artifacts"]["desk_sheet"] = str(desk_sheet_path)
    return payload


def estimate_edition_workspace(
    newsroom: Path,
    config: MorningPaperConfig,
    *,
    date_str: str,
) -> dict[str, object]:
    root = newsroom.expanduser().resolve()
    edition_dir = root / "editions" / date_str
    if not edition_dir.is_dir():
        raise FileNotFoundError(f"missing edition directory: {edition_dir}")
    payload = estimate_markdown(edition_dir / "draft.md", config, date_str=date_str)
    payload["page_budget"] = _page_budget_policy(root)
    write_json(edition_dir / "estimate-result.json", payload)
    return payload


def visual_qa_edition_workspace(
    newsroom: Path,
    *,
    date_str: str,
) -> dict[str, object]:
    root = newsroom.expanduser().resolve()
    edition_dir = root / "editions" / date_str
    if not edition_dir.is_dir():
        raise FileNotFoundError(f"missing edition directory: {edition_dir}")
    render_result = _load_json_object(edition_dir / "render-result.json")
    payload = visual_qa_from_render(render_result=render_result, edition_dir=edition_dir)
    write_json(edition_dir / "visual-qa.json", payload)
    return payload
