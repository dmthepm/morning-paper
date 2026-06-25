# Morning Paper 0.8.6 Release Readiness

Status: published and verified.

Date: 2026-06-25

## Release Line

- Package version: `0.8.6`
- Published tag: `v0.8.6`

0.8.6 is the dogfood release for the private-newsroom operating model. It
ships the desk-sheet fixes, richer first-run visual/source guidance, stronger
review checks, and the documented multi-desk routine model without changing the
core division of labor: agents compose; the CLI renders and proves.

## What Changed

- Scaffolded newsrooms now include a reader-owned `preferences/desk-sheet.yaml`
  and `edition prepare` writes a No. 10-style desk sheet only when enabled.
- First-run `VISUALS.md` now teaches richer reading furniture: one-line
  full-read metadata, pill-style tags, coded reading menus, and no raw URL
  dumps unless the URL itself matters.
- `docs/private-newsroom-operating-model.md` captures the owned-algorithm
  routine: source experiments, multi-agent newsroom desks, budgets, memory,
  feedback, and delivery surfaces.
- Setup and source/delivery scaffolds now steer agents toward beat experiments
  and optional delivery surfaces such as Telegram, GitHub artifacts, mobile
  reading, and read-later staging.
- Review and visual QA catch more paper-breaking artifacts: text-only long
  editions with no major visual, long raw URLs in decks, stacked imported
  subheads, Markdown tables rendered literally, and missing-glyph boxes.

## Verification Run

The local candidate was checked with:

```bash
PYTHONPATH=src PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q
python3 scripts/validate_codex_plugin.py
PYTHONPATH=src python3 scripts/host_plugin_smoke.py
PYTHONPATH=src python3 scripts/install_smoke.py
python3 scripts/release_candidate_check.py --outdir /tmp/morning-paper-rc-final-local --install-check
python3 scripts/release_candidate_check.py --outdir /tmp/morning-paper-dist-0.8.6 --install-check
```

Latest full local verification on 2026-06-25 on current `main` HEAD:

- Full suite: `229 passed`.
- Codex plugin validation passed.
- Host plugin smoke passed for Claude Code and Codex with version `0.8.6`.
- Install smoke passed: both hosts expose exactly `setup`, `edition`, and
  `writing`.
- Release-candidate artifact check built clean wheel and sdist artifacts:
  `morning_paper-0.8.6-py3-none-any.whl` and
  `morning_paper-0.8.6.tar.gz`.
- Clean Python 3.13 venv installed both artifacts.
- Installed binaries printed `0.8.6`.
- `morning-paper doctor --strict --json` reported `status: ok`.
- Render self-test passed and demo PDFs rendered from both artifacts.

Published artifact verification:

- PyPI JSON reports `0.8.6`.
- Clean Python 3.13 venv installed `morning-paper[pretty]==0.8.6` from PyPI.
- Installed binary prints `0.8.6`.
- `morning-paper doctor --strict --json` reports `status: ok`.
- `morning-paper demo --output <tmp>/demo.pdf` renders a real PDF.
