from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .config import MorningPaperConfig
from .sources import source_inventory
from .staging import queue_status


FEEDBACK_ROUTES = {
    "editorial": "EDITORIAL.md",
    "visuals": "VISUALS.md",
    "sources": "SOURCES.md",
    "delivery": "DELIVERY.md",
    "taste": "TASTELOG.md",
    "voice": "preferences/voice.md",
    "prior": "preferences/algorithm-prior.yaml",
    "checks": "preferences/checks.yaml",
    "the-read": "specs/the-read.md",
    "front-page": "specs/front-page.md",
    "reading": "specs/reading.md",
}


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

    contract_files = [
        root / "EDITORIAL.md",
        root / "VISUALS.md",
        root / "SOURCES.md",
        root / "DELIVERY.md",
        root / "TASTELOG.md",
        root / "specs" / "the-read.md",
        root / "specs" / "front-page.md",
        root / "specs" / "reading.md",
        edition_dir / "source-inventory.json",
        edition_dir / "collector-report.md",
        edition_dir / "queue-snapshot.json",
        edition_dir / "render-result.json",
        edition_dir / "review.json",
        edition_dir / "operator-answers.md",
        edition_dir / "feedback-plan.md",
    ]
    findings: list[dict[str, object]] = []
    files_read: list[str] = []
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
    render_result = _load_json_object(edition_dir / "render-result.json")
    review = _load_json_object(edition_dir / "review.json")

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
    elif pages > config.page_budget + 2:
        _final_finding(
            findings,
            check="page-budget",
            severity="flag",
            issue=f"Rendered paper is {pages} pages against a {config.page_budget}-page budget.",
            why="The reader asked for a finite paper; overshooting by more than two pages should be an explicit editorial decision.",
            hint="Cut or compress the weakest material, or record the intentional exception in DELIVERY.md.",
            measured={"pages": pages, "page_budget": config.page_budget},
        )
    elif pages > config.page_budget:
        _final_finding(
            findings,
            check="page-budget",
            severity="nudge",
            issue=f"Rendered paper is {pages} pages against a {config.page_budget}-page budget.",
            why="A small overage can ship, but the editor should name the tradeoff.",
            hint="Mention the overage in the handoff or cut a weak item.",
            measured={"pages": pages, "page_budget": config.page_budget},
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
            why="The paper can ship, but the reader should know some owned sources were visible and not staged.",
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
                issue=f"{len(flagged_items)} staged item(s) carry truncation or remote-extraction notes.",
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

## Print Tomorrow
- URLs or files to stage for tomorrow's paper.
"""


def feedback_plan_template(date_str: str) -> str:
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
5. Stage anything under "Print Tomorrow" with `morning-paper stage <url-or-file>`.
6. Leave a short "Applied Feedback" note in this file with paths changed.

## Routes

| Reader note | Durable target |
|---|---|
| Keep / cut / more / less / page budget / what earns ink | `EDITORIAL.md` (`--route editorial`) |
| Voice, density, register, tone, AI tells | `preferences/voice.md` (`--route voice`) |
| Section-specific taste | `specs/the-read.md`, `specs/front-page.md`, or `specs/reading.md` (`--route the-read|front-page|reading`) |
| Visuals, charts, illustrations, layout, print readability | `VISUALS.md` |
| Add, demote, remove, distrust, or change cadence of a source | `SOURCES.md` (`--route sources`) |
| Standing interests, source weighting, dampeners | `preferences/algorithm-prior.yaml` (`--route prior`) |
| Review thresholds or muted copy-desk findings | `preferences/checks.yaml` (`--route checks`) |
| PDF, print, email/article view, archive, routine/automation behavior | `DELIVERY.md` |
| One-off URL or file to read tomorrow | `morning-paper stage <url-or-file>` |
| Stable accepted/rejected taste decision | `TASTELOG.md` |

## Guardrails

- Do not overfit one annoyed note into a permanent rule. Save as durable taste
  only when the reader asks, repeats it, or the paper clearly benefits.
- Do not store private source content in the public engine repo.
- Do not erase a source because it was empty once. Record failure and next
  action in `SOURCES.md`.
- If feedback conflicts with an existing rule, update `TASTELOG.md` with the
  decision and why the older rule changed.
- YAML targets (`preferences/algorithm-prior.yaml`, `preferences/checks.yaml`)
  receive feedback as comments so the file stays parseable. Promote the note
  into real YAML only when the exact setting is clear.

## Applied Feedback

No feedback applied yet.
"""


def draft_template(date_str: str, paper_name: str) -> str:
    return f"""# {paper_name} - {date_str}

<!-- Draft starts here. Compose against EDITORIAL.md, VISUALS.md, SOURCES.md,
DELIVERY.md, specs/, preferences/, source-inventory.json, collector-report.md,
and queue-snapshot.json. Replace this placeholder before rendering. -->

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
    _append_section_note(taste_log, heading="## Log", note=taste_line)
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

    record("queue-snapshot.json", _write_json(edition_dir / "queue-snapshot.json", queue_status(config, date_str), force=force))
    record("draft.md", _write(edition_dir / "draft.md", draft_template(date_str, config.name), force=force))

    render_pending = {
        "status": "pending",
        "date": date_str,
        "command": f"morning-paper render {edition_dir / 'draft.md'} --date {date_str} --slug edition",
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    record("render-result.json", _write_json(edition_dir / "render-result.json", render_pending, force=force))

    review_pending = {
        "status": "pending",
        "date": date_str,
        "command": f"morning-paper review {edition_dir} --json",
        "updated_at": _utc_stamp(),
    }
    record("review.json", _write_json(edition_dir / "review.json", review_pending, force=force))

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

    record("operator-answers.md", _write(edition_dir / "operator-answers.md", operator_answers_template(date_str), force=force))
    record("feedback-plan.md", _write(edition_dir / "feedback-plan.md", feedback_plan_template(date_str), force=force))

    return {
        "edition_dir": str(edition_dir),
        "date": date_str,
        "written": written,
        "skipped": skipped,
        "artifacts": {
            "source_inventory": str(edition_dir / "source-inventory.json"),
            "collector_report": str(edition_dir / "collector-report.md"),
            "queue_snapshot": str(edition_dir / "queue-snapshot.json"),
            "draft": str(edition_dir / "draft.md"),
            "render_result": str(edition_dir / "render-result.json"),
            "review": str(edition_dir / "review.json"),
            "final_editor": str(edition_dir / "final-editor.json"),
            "final_editor_markdown": str(edition_dir / "final-editor.md"),
            "operator_answers": str(edition_dir / "operator-answers.md"),
            "feedback_plan": str(edition_dir / "feedback-plan.md"),
        },
        "next_action": "run collectors, refresh queue-snapshot.json, compose draft.md, render, review, final-editor, then ask for feedback and route it through feedback-plan.md",
    }
