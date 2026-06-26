# Morning Paper 0.8.10 Release Readiness

Status: candidate, ready to tag.

Date: 2026-06-26

## Release Line

- Package version: `0.8.10`
- Candidate tag: `v0.8.10`

0.8.10 is the substantial-edition quality gate release. It keeps the public
skill surface small (`setup`, `edition`, `writing`) while making real daily
papers require the late newsroom desks when the run is broad enough to need
them.

## What Changed

- Substantial editions now require editor, copy desk, art desk, and producer
  handoffs.
- The Assignment Board has a `needs_hydration` lane for snippet-only social
  items.
- New newsroom scaffolds include `preferences/source-budgets.yaml`.
- Review includes a `process-density` nudge for papers that read too much like
  run logs.
- The accidental standalone setup/readiness contract file was retired; its
  useful content now lives in README, `docs/edition-run-contract.md`,
  `docs/private-newsroom-operating-model.md`, `docs/newsroom-skill-suite.md`,
  and `ROLES.md`.

## Verification Run

The local candidate was checked with:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=src python3 -m pytest tests/ -q
python3 scripts/release_candidate_check.py --outdir /tmp/morning-paper-dist-0.8.10 --install-check
```

Latest full local verification on 2026-06-26 on current `main` HEAD:

- Full suite passed: `235 passed`.
- Clean Python 3.13 venv installed both wheel and sdist artifacts.
- Installed binaries printed `0.8.10`.
- `morning-paper doctor --strict --json` reported `status: ok`.
- Render self-test passed and demo PDFs rendered from both artifacts.
