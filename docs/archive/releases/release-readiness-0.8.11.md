# Morning Paper 0.8.11 Release Readiness

Status: candidate, ready to tag.

Date: 2026-06-27

## Release Line

- Package version: `0.8.11`
- Candidate tag: `v0.8.11`

0.8.11 is the social source-record and newsroom-language release. It keeps the
public skill surface small (`setup`, `edition`, `writing`) while giving agents a
printer-friendly path for actual posts, threads, and source evidence instead of
generic social summaries.

## What Changed

- Added `morning-paper stage-social` for complete social source records.
- Added print-native social cards with author, date, metrics, source status,
  thread context, full text, and optional print-approved media.
- Renamed the social completion lane to `needs_source_record`.
- Render output now includes an explicit `rendered` status.
- Visual QA samples more pages on longer papers.
- Delivery proof placeholders are created with new edition workspaces.
- Current docs and skills use newsroom-facing language for collectors,
  Assignment Board state, and social source records.

## Verification Run

The local candidate was checked with:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=src python3 -m pytest tests/ -q
git diff --check
python3 scripts/release_candidate_check.py --outdir /tmp/morning-paper-dist-0.8.11 --install-check
```

Latest full local verification on 2026-06-27 on current `main` HEAD:

- Full suite passed: `237 passed`.
- Clean Python 3.13 venv installed both wheel and sdist artifacts.
- Installed binaries printed `0.8.11`.
- `morning-paper doctor --strict --json` reported `status: ok`.
- Render self-test passed and demo PDFs rendered from both artifacts.
