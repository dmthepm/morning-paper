#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def extract(pattern: str, text: str, default: str = "unknown") -> str:
    m = re.search(pattern, text, flags=re.MULTILINE)
    return m.group(1).strip() if m else default


def add_or_none(items: list[str], fallback: str) -> list[str]:
    return items if items else [fallback]


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize latest runtime maintenance findings for Morning Brief")
    parser.add_argument("--input", default=str(Path.home() / ".hermes" / "logs" / "runtime-maintenance" / "current.log"))
    parser.add_argument("--proposal-json", default=str(Path.home() / ".hermes" / "logs" / "runtime-maintenance" / "update-proposal.json"))
    parser.add_argument("--output")
    args = parser.parse_args()

    p = Path(args.input)
    if not p.exists():
        output = "<!-- Maintenance log unavailable -->"
    else:
        text = p.read_text(encoding="utf-8")
        thoth_backend = extract(r"tailscale_backend_state:\s*(.+)", text)
        thoth_online = extract(r"tailscale_online:\s*(.+)", text)
        hermes_dirty = "dirty" if "## Hermes repo" in text and "working_tree: dirty" in text else "clean"
        hermes_ahead = extract(r"(?s)## Hermes repo.*?ahead:\s*(\d+)", text, "?")
        hermes_behind = extract(r"(?s)## Hermes repo.*?behind:\s*(\d+)", text, "?")
        paperclip_ahead = extract(r"(?s)## Paperclip repo.*?ahead:\s*(\d+)", text, "?")
        paperclip_behind = extract(r"(?s)## Paperclip repo.*?behind:\s*(\d+)", text, "?")
        mini_pc = extract(r"MiniPC (.+)", text, "unknown")
        homebridge = "reachable" if "homebridge_ui_8581: reachable" in text else extract(r"homebridge_ui_8581:\s*(.+)", text, "unknown")
        browser_vulns = extract(r"Browser tools \(agent-browser\) deps \((.+?)\)", text, "")
        whatsapp_vulns = extract(r"WhatsApp bridge deps \((.+?)\)", text, "")
        submodule_missing = "tinker-atropos not found" in text
        paperclip_port = extract(r"paperclip_port_3100:\s*(.+)", text, "unknown")
        proposal = {}
        proposal_path = Path(args.proposal_json)
        if proposal_path.exists():
            try:
                proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                proposal = {}

        reliability = [
            f"Thoth Tailscale: {thoth_backend} / {thoth_online}",
            f"Hermes repo: {hermes_dirty}, ahead {hermes_ahead}, behind {hermes_behind}",
            f"Paperclip repo: ahead {paperclip_ahead}, behind {paperclip_behind}",
            f"Mini PC: {mini_pc}",
            f"Homebridge UI: {homebridge}",
        ]

        auto_fixed: list[str] = []
        if paperclip_port == "listening":
            auto_fixed.append("Paperclip is on loopback port 3100 and responding normally.")
        auto_fixed = add_or_none(auto_fixed, "No new auto-fixes recorded in this maintenance snapshot.")

        needs_devon: list[str] = []
        if thoth_online.lower() != "true":
            needs_devon.append(f"Thoth Tailscale is not fully online ({thoth_backend} / {thoth_online}).")
        if homebridge != "reachable":
            needs_devon.append(f"Homebridge UI needs attention ({homebridge}).")
        if not mini_pc.lower().startswith("ok"):
            needs_devon.append(f"Mini PC helper reported: {mini_pc}")
        for item in proposal.get("items", []):
            if item.get("status") in {"approval_required", "blocked"}:
                needs_devon.append(f"{item.get('repo')}: {item.get('reason')} {item.get('recommended_path')}")
        needs_devon = add_or_none(needs_devon, "None right now.")

        security_attention: list[str] = []
        if browser_vulns:
            security_attention.append(f"Browser tools dependency vulnerabilities: {browser_vulns}.")
        if whatsapp_vulns:
            security_attention.append(f"WhatsApp bridge dependency vulnerabilities: {whatsapp_vulns}.")
        security_attention = add_or_none(security_attention, "No new security attention items surfaced in this snapshot.")

        upgrade_watch: list[str] = []
        if hermes_behind != "0":
            upgrade_watch.append(f"Hermes is behind upstream by {hermes_behind} commits.")
        if paperclip_behind != "0":
            upgrade_watch.append(f"Paperclip is behind upstream by {paperclip_behind} commits.")
        if submodule_missing:
            upgrade_watch.append("Hermes submodule tinker-atropos is missing and should be reviewed before deeper updates.")
        for item in proposal.get("items", []):
            if item.get("status") == "approval_required":
                upgrade_watch.append(f"{item.get('repo')} approval path: {item.get('approval_path')}")
        upgrade_watch = add_or_none(upgrade_watch, "No upgrade watch items right now.")

        drift: list[str] = []
        if hermes_ahead != "0" or hermes_behind != "0" or hermes_dirty != "clean":
            drift.append(f"Hermes drift: {hermes_dirty}, ahead {hermes_ahead}, behind {hermes_behind}.")
        if paperclip_ahead != "0" or paperclip_behind != "0":
            drift.append(f"Paperclip drift: ahead {paperclip_ahead}, behind {paperclip_behind}.")
        drift = add_or_none(drift, "No meaningful repo drift in this snapshot.")

        sections = [
            ("Platform Reliability", reliability),
            ("Auto-fixed", auto_fixed),
            ("Needs Devon", needs_devon),
            ("Security attention", security_attention),
            ("Upgrade watch", upgrade_watch),
            ("Drift", drift),
        ]
        output = "\n\n".join(
            [f"**{heading}**\n" + "\n".join(f"- {item}" for item in bullets) for heading, bullets in sections]
        )

    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
