# Morning Paper 0.8.4 Release Readiness

Status: published and verified.

Date: 2026-06-23

## Release Line

- Package version: `0.8.4`
- Public PyPI version verified on 2026-06-23: `0.8.4`
- Published tag: `v0.8.4`

0.8.4 ships the proofed source-intake loop release. It keeps the engine small:
edition artifacts now prove freshness and visual sanity, and source intake is
shape-aware without adding hosted connectors, scraper registries, or
source-specific product identity.

## What Changed

- Edition workspaces now carry `estimate-result.json` and `visual-qa.json`.
- `final-editor` now flags missing or stale estimates, large estimate/render
  drift, stale render/review artifacts, unreadable PDFs, page-count mismatch
  between render metadata and the file on disk, and missing visual QA.
- `scripts/source_shape_intake_smoke.py` proves a source ledger over synthetic
  mbox/MIME email, Main Branch-style repos, YouTube exports, generic CSV/JSON
  exports, and local folders.
- Setup/source guidance now says: inspect source shape, write a ledger, ask the
  reader what should influence the paper, then build the smallest private
  converter or collector.

## Verification Run

The local candidate was checked with:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=src python3 -m pytest tests/ -q
PYTHONPATH=src python3 scripts/setup_scaffold_smoke.py --isolated
PYTHONPATH=src python3 scripts/fresh_friend_smoke.py
PYTHONPATH=src python3 scripts/dogfood_newsroom_smoke.py
PYTHONPATH=src python3 scripts/five_edition_loop_smoke.py
PYTHONPATH=src python3 scripts/source_shape_intake_smoke.py
PYTHONPATH=src python3 scripts/host_plugin_smoke.py
python3 scripts/release_candidate_check.py --outdir /tmp/morning-paper-rc-final-local --install-check
python3 scripts/release_candidate_check.py --outdir /tmp/morning-paper-dist-0.8.4 --install-check
```

Latest full local verification: 2026-06-23 on current `main` HEAD, with unit
tests, setup scaffold smoke, five fresh-friend personas, dogfood newsroom
smoke, five-edition loop smoke, source-shape intake smoke, host plugin smoke,
and clean wheel/sdist install checks all passing.

The release-candidate artifact check built clean wheel and sdist artifacts,
installed both with `[pretty]`, verified the same `0.8.4` semver across
`pyproject.toml`, `__version__`, and both host manifests, ran
`doctor --strict --json`, and rendered demo PDFs from both artifacts.

Published artifact verification on 2026-06-23:

- PyPI JSON reported `0.8.4`.
- Clean Python 3.13 venv installed `morning-paper[pretty]==0.8.4` from PyPI.
- Installed binary printed `0.8.4`.
- `morning-paper doctor --strict --json` returned `status: ok`.
- `morning-paper demo --output <tmp>/demo.pdf` rendered a real PDF.

## Completion Gate Map

| Gate | Evidence |
| --- | --- |
| Unit tests | `220 passed` locally after the 0.8.4 bump. |
| Setup scaffold smoke | `scripts/setup_scaffold_smoke.py --isolated` passed with clean final-editor status. |
| Fresh-friend smoke | Five personas produced PDFs; all quality errors empty. |
| Dogfood smoke | Passed with notes only for visible unsupported local-drop files. |
| Five-edition loop | Passed across five consecutive editions with durable feedback carried. |
| Source-shape intake | Passed for mbox, Main Branch-style repo, YouTube export, CSV/JSON exports, and local folder; zero engine integrations added. |
| Visual QA | Edition smokes wrote `visual-qa.json`; final-editor required it before delivery. |
| Release artifacts | Clean wheel and sdist installed, passed strict doctor, and rendered demo PDFs. |
| Plugin surfaces | Host plugin smoke passed for Claude Code and Codex from the shared skill tree at `0.8.4`. |
| No private data | Source-shape fixtures are synthetic; smokes use temp directories and public-safe content. |
