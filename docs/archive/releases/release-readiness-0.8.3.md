# Morning Paper 0.8.3 Release Readiness

Status: published and verified.

Date: 2026-06-23

## Release Line

- Package version: `0.8.3`
- Public PyPI version verified on 2026-06-23: `0.8.3`
- Published tag: `v0.8.3`
- Publish workflow: GitHub Actions run `28039041269`, passed.
- CI workflow on `main`: GitHub Actions run `28039036943`, passed.

0.8.3 ships the final-editor/source-conversion/feedback/dogfood foundation on
top of 0.8.2. The release proof is the same discipline as 0.8.2: clean local
verification first, then tag-driven clean artifact build, PyPI publish, clean
PyPI install, strict doctor, demo render, and plugin surface checks.

## What Changed

- `morning-paper edition final-editor` now writes `final-editor.json` and
  `final-editor.md`, giving agents a deterministic pre-delivery ship rule after
  render and review.
- Source conversion guidance now lives in the public docs and in each
  scaffolded newsroom's `collectors/CONVERTERS.md`, keeping unsupported local
  files on a private converter path instead of turning the engine into a
  scraper registry.
- `docs/feedback-loop.md` documents how natural-language and desk-sheet
  feedback should become the smallest durable newsroom change.
- `scripts/dogfood_newsroom_smoke.py` exercises a synthetic private-newsroom
  path with work pulse, saved reading, local note, CSV/JSON exports, converter
  digest, render, review, final-editor, feedback routing, and private-term
  scan.
- Page-count worker subprocesses preserve source-checkout `PYTHONPATH`, so
  helper subprocesses can find `morning_paper.page_count_worker` in local
  verification.
- Current-facing docs/examples no longer put Hacker News or the CLI fallback
  scheduler in the default mental model. Sources start from the reader's own
  stack; recurrence starts from the host's native primitive.

## Verification Run

The current local candidate has been checked with:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=src python3 -m pytest -q
PYTHONPATH=src python3 scripts/setup_scaffold_smoke.py --isolated
PYTHONPATH=src python3 scripts/fresh_friend_smoke.py
PYTHONPATH=src python3 scripts/dogfood_newsroom_smoke.py
python3 scripts/install_smoke.py
python3 scripts/host_plugin_smoke.py
python3 scripts/validate_codex_plugin.py
claude plugin validate ./ --strict
python3 scripts/release_candidate_check.py --outdir /tmp/morning-paper-rc-final-local --install-check
```

Latest full local verification: 2026-06-23 on current `main` HEAD, with unit
tests, setup scaffold smoke, five fresh-friend personas, dogfood newsroom
smoke, install smoke, host plugin smoke, Codex plugin validation, Claude strict
plugin validation, and clean wheel/sdist install checks all passing.

Published artifact verification on 2026-06-23:

- PyPI JSON reported `0.8.3`.
- Clean Python 3.13 venv installed `morning-paper[pretty]==0.8.3` from PyPI.
- Installed binary printed `0.8.3`.
- `morning-paper doctor --strict --json` returned `status: ok`.
- `morning-paper demo --output <tmp>/demo.pdf` rendered a real PDF.
- A fresh checkout of `v0.8.3` passed plugin validation and install smoke.

The release-candidate artifact check builds a clean wheel and sdist, installs
both with `[pretty]`, verifies the reported core dependency and print-stack
versions, runs `doctor --strict`, and renders a demo PDF.

## Completion Gate Map

| Gate | Evidence |
| --- | --- |
| Docs and skills agree | README, `AGENTS.md`, setup/edition skills, changelog, and friend-ready newsroom docs use the same setup/source/feedback model. |
| README stays concise and true | README keeps details to setup, sources, daily routine, styles, agents, and development. |
| No stale source identity | Current-facing docs and examples describe the whole source stack; legacy built-ins are off by default. |
| No stale scraper assumption | Local extraction is default; remote fallback is explicit; scraper/parser packages are treated as implementation details. |
| Native recurrence prompts | README/setup guidance uses Claude Code routines, Codex automations, and ChatGPT scheduled tasks without inventing a competing default. |
| Source onboarding durable path | `sources check --newsroom`, scaffolded-newsroom auto-detection, collector recipes, staging, queue inspection, and fresh-friend smoke all exercise reader-owned sources. |
| Compaction-safe edition loop | `edition prepare`, `edition final-editor`, and `edition apply-feedback` write durable artifacts and route accepted feedback to the smallest supported newsroom file. |
| Plugin surfaces | Codex and Claude plugin validation plus install/host plugin smoke pass from the shared skill tree, locked to exactly `setup`, `edition`, and `writing` for 0.8.x. |

## Release Checklist

Completed:

1. Confirmed worktree clean before release prep.
2. Re-ran the full local verification block.
3. Pushed batched commits to `main`.
4. Tagged `v0.8.3` on the release commit.
5. Built and published clean artifacts through GitHub Actions.
6. Verified PyPI reports `0.8.3`.
7. Clean-installed `morning-paper[pretty]==0.8.3` from PyPI.
8. Ran `morning-paper doctor --strict`.
9. Ran `morning-paper demo --output <tmp>/demo.pdf`.
10. Validated Claude Code and Codex plugin installs from the published tag.
