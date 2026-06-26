# Morning Paper 0.8.8 Release Readiness

Status: local candidate verified; not published from this repository.

Date: 2026-06-26

## Release Line

- Package version: `0.8.8`
- Candidate tag: `v0.8.8`

0.8.8 is the current friend-ready baseline before the Assignment Board and
run-ticket cleanup. It keeps the single-source skill contract and the
reader-owned newsroom scaffold intact.

## Verification Run

The local candidate was checked with:

```bash
PYTHONPATH=src PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q
python3 scripts/validate_codex_plugin.py
PYTHONPATH=src python3 scripts/host_plugin_smoke.py
PYTHONPATH=src python3 scripts/install_smoke.py
python3 scripts/release_candidate_check.py --outdir /tmp/morning-paper-rc-final-local --install-check
python3 scripts/release_candidate_check.py --outdir /tmp/morning-paper-dist-0.8.8 --install-check
```

Latest full local verification on 2026-06-26 on current `main` HEAD:

- Full suite passed before the current P0 newsroom-artifact cleanup.
- Codex plugin validation passed.
- Host plugin smoke passed for Claude Code and Codex with version `0.8.8`.
- Install smoke passed: both hosts expose exactly `setup`, `edition`, and
  `writing`.
- Clean Python 3.13 venv installed both artifacts.
- Installed binaries printed `0.8.8`.
- `morning-paper doctor --strict --json` reported `status: ok`.
- Render self-test passed and demo PDFs rendered from both artifacts.

External publish verification was not completed for this candidate:

- PyPI/tag verification is not claimed here.
- Use the next release-readiness file for the published line.
