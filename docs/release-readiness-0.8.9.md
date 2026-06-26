# Morning Paper 0.8.9 Release Readiness

Status: candidate, ready to tag.

Date: 2026-06-26

## Release Line

- Package version: `0.8.9`
- Planned tag: `v0.8.9`

0.8.9 is the newsroom role workflow release. It keeps the public skill surface
small (`setup`, `edition`, `writing`) while making the edition workflow
agent-readable through role references, desk artifacts, and run-ticket checks.

## What Shipped

- `ROLES.md` is the front door for the newsroom role model.
- `docs/roles/` defines orchestrator, assignment editor, beat reporter, editor,
  copy desk, art desk, producer, and taste editor responsibilities.
- `edition prepare` writes `editions/<date>/desks/README.md` so a fresh agent
  knows where role handoffs belong.
- `edition status` indexes role artifacts and validates their required
  frontmatter.
- Blocked role artifacts block the run ticket; malformed role artifacts produce
  repair notes.
- Product/design context remains in root `PRODUCT.md` and `DESIGN.md`; runtime
  operating contracts live in `docs/friend-ready-newsroom.md` and `ROLES.md`.

## Verification Run

The local candidate was checked with:

```bash
PYTHONFAULTHANDLER=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=src python3 -m pytest tests/ -q
python3 scripts/validate_codex_plugin.py
PYTHONPATH=src python3 scripts/install_smoke.py
python3 scripts/release_candidate_check.py --outdir /tmp/morning-paper-dist-0.8.9 --install-check
```

Latest full local verification on 2026-06-26 on current `main` HEAD:

- Full suite passed: `233 passed`.
- Codex plugin validation passed.
- Install smoke passed: both hosts expose exactly `setup`, `edition`, and
  `writing`.
- Clean Python 3.13 venv installed both wheel and sdist artifacts.
- Installed binaries printed `0.8.9`.
- `morning-paper doctor --strict --json` reported `status: ok`.
- Render self-test passed and demo PDFs rendered from both artifacts.

After tag/publish, verify:

- PyPI JSON reports `0.8.9`.
- Clean Python 3.13 venv installs `morning-paper[pretty]==0.8.9` from PyPI.
- Installed binary prints `0.8.9`.
- `morning-paper doctor --strict --json` reports `status: ok`.
- `morning-paper demo --output <tmp>/demo.pdf` renders a real PDF.
