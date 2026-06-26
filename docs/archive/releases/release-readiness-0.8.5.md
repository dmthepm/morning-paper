# Morning Paper 0.8.5 Release Readiness

Status: published and verified.

Date: 2026-06-23

## Release Line

- Package version: `0.8.5`
- Published tag: `v0.8.5`

0.8.5 is a patch release for edition-agent discipline. It ships the dogfood
learning from interrupted personal editions without adding a new runtime
primitive: the edition folder remains the paper trail.

## What Changed

- The edition skill now says `editions/YYYY-MM-DD/` is the durable run state.
- Agents are told not to invent a separate `RUN_STATE` file.
- Pending JSON artifacts now mean unfinished work to inspect and complete.
- Interrupted `data/*.tmp` collector files now mean rerun the collector cleanly,
  not hand-edit the temp artifact.
- A clean `edition final-editor` result is the stop line unless the reader
  explicitly asks for tomorrow's edition.

## Verification Run

The local candidate was checked with:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=src python3 -m pytest tests/ -q
python3 scripts/validate_codex_plugin.py
PYTHONPATH=src python3 scripts/host_plugin_smoke.py
python3 scripts/release_candidate_check.py --outdir /tmp/morning-paper-rc-final-local --install-check
python3 scripts/release_candidate_check.py --outdir /tmp/morning-paper-dist-0.8.5 --install-check
```

Latest full local verification: 2026-06-23 on current `main` HEAD, with the
full test suite (`221 passed`), Codex plugin validation, host plugin smoke, and
clean wheel/sdist install checks all passing.

Published artifact verification:

- PyPI JSON reports `0.8.5`.
- Clean Python 3.13 venv installed `morning-paper[pretty]==0.8.5` from PyPI.
- Installed binary prints `0.8.5`.
- `morning-paper doctor --strict --json` reports `status: ok`.
- `morning-paper demo --output <tmp>/demo.pdf` renders a real PDF.
