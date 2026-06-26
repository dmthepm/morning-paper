# Morning Paper 0.8.2 Release Readiness

Status: published and verified.

Date: 2026-06-22

## Release Line

- Package version: `0.8.2`
- Public PyPI version verified on 2026-06-22: `0.8.2`
- Published tag: `v0.8.2` at
  `778db32611353e654554e0a7af68dd51f525edf0`
- Publish workflow: GitHub Actions run `27990559664`, passed.
- CI workflow on `main`: GitHub Actions run `27990556669`, passed.

0.8.2 has completed the publish sequence: commits were pushed, `v0.8.2` was
tagged, the publish workflow built clean artifacts and uploaded to PyPI, PyPI
reports `0.8.2`, a clean PyPI install passed `doctor --strict`, `demo --open`
opened a two-page PDF, and Claude Code/Codex plugin surfaces were verified from
a fresh clone of the published tag.

## What Changed

- The README is shorter and product-true: owned algorithm, personal newsroom,
  agent composes, CLI renders, first proof is a demo PDF open on screen.
- The README hero image now uses the supplied Morning Paper artwork, resized
  for a reasonable repository footprint.
- Source guidance now starts from the reader's actual source stack: work
  streams, messages, repos, tickets, saved tabs, newsletters, feeds, folders,
  exports, Obsidian vaults, local reports, APIs, local scrapes, and
  agent-produced files.
- `sources list` / `sources check` now auto-detect a scaffolded newsroom when
  run from its root, so a fresh agent sees the local drop folder and collector
  scripts even if it forgets `--newsroom .`.
- Local-drop inventory now distinguishes supported staging candidates from
  unsupported files, so PDFs/CSVs/exports prompt a converter collector instead
  of looking ready when the starter collector will skip them.
- The scaffolded local-drop collector now reports those unsupported files in
  its own output too, so `collectors/run_all.sh` gives an agent an honest
  transcript even when supported files were staged successfully.
- Legacy built-in source labels are no longer friend-facing identity claims.
  The reader-facing model is the whole personal source stack.
- Remote URL extraction is explicit. `article_extractor: local` stays local
  unless `remote_extractor_fallback: true` is set.
- Dependency visibility is part of the release proof. `doctor --json` reports
  the core source/parser dependencies as well as the print stack, and the clean
  release-candidate install fails if those versions are absent.
- Trafilatura is bounded to the current supported major line (`>=2.1,<3`) so
  local extraction does not silently absorb a future major parser change.
- Durable feedback is executable: `morning-paper edition apply-feedback`
  writes stable notes into the selected newsroom file, `TASTELOG.md`, and that
  edition's `feedback-plan.md`. It can now target the narrower scaffolded
  files for voice, standing interests, review preferences, and section specs
  instead of only the broad desk files. Feedback to YAML targets is recorded as
  comments so `preferences/algorithm-prior.yaml` and `preferences/checks.yaml`
  remain parseable.
- The shipped plugin surface is locked to exactly `setup`, `edition`, and
  `writing` for 0.8.x. Future newsroom desk skills are documented as design
  direction and cannot leak into the plugin without validation failures.
- Native recurrence is framed through the host's own primitive: Codex
  automations, Claude Code routines (`/schedule` from the CLI), or ChatGPT
  scheduled tasks. Codex and Claude paths run where the newsroom is visible;
  ChatGPT tasks are treated as reminders/check-ins unless an approved runner can
  access the newsroom, and they must not assume project-file access. The CLI
  `routine` command remains a local fallback.
- Visual integration guardrails now cover chart and illustration width,
  label-density, print suitability, captions/source notes, and review
  expectations; `morning-paper review` now nudges on unfurnished visual markup
  before the agent hands over the PDF.

## Verification Run

The current local candidate has been checked with:

```bash
python -m pytest
python scripts/setup_scaffold_smoke.py --isolated
python scripts/fresh_friend_smoke.py
python scripts/install_smoke.py
python scripts/host_plugin_smoke.py
python scripts/validate_codex_plugin.py
claude plugin validate --strict <repo>
python3 scripts/release_candidate_check.py --outdir /tmp/morning-paper-rc-final-local --install-check
```

Last full isolated local result: `216 passed`.
Latest full local verification: 2026-06-22 on current `main` HEAD, with setup
scaffold smoke, five fresh-friend personas, install smoke, Codex plugin
validation, host plugin smoke, Claude strict plugin validation, and clean
wheel/sdist install checks all passing.

Published artifact verification on 2026-06-22:

- PyPI JSON reported `0.8.2`.
- `pip index versions morning-paper` showed `0.8.2`.
- Clean Python 3.13 venv installed `morning-paper[pretty]==0.8.2` from PyPI.
- Installed binary printed `0.8.2`.
- `morning-paper doctor --strict --json` returned `status: ok`,
  WeasyPrint `69.0`, trafilatura `2.1.0`, and a one-page render self-test.
- `morning-paper demo --output <tmp>/demo.pdf --open` rendered a real two-page
  PDF and opened it with macOS `open`.
- A fresh clone of `v0.8.2` passed `scripts/install_smoke.py`,
  `scripts/validate_codex_plugin.py`, `scripts/host_plugin_smoke.py`, and
  `claude plugin validate --strict`.

The release-candidate artifact check builds a clean wheel and sdist, installs
both with `[pretty]`, verifies the reported core dependency and print-stack
versions, verifies WeasyPrint 69.0, runs `doctor --strict`, and renders a
two-page demo PDF.

Local machine note: the ambient system Python currently has stale WeasyPrint
68.1 and trafilatura 2.0.0, so strict setup smoke fails there by design.
`setup_scaffold_smoke.py --isolated` creates a temporary install of the current
project with `[dev,pretty]`, resolves WeasyPrint 69.0 and trafilatura 2.1.0,
and passes setup smoke without touching real user config.

## Completion Gate Map

| Gate | Evidence |
| --- | --- |
| Docs and skills agree | README, `AGENTS.md`, setup/edition skills, changelog, and friend-ready newsroom docs use the same setup/source/feedback model. |
| README stays concise and true | README now keeps details to setup, sources, daily routine, styles, agents, and development. |
| No stale source identity | Friend-facing docs describe the whole source stack; legacy built-ins stay internal and do not define the product surface. |
| No stale scraper assumption | Local extraction is default; remote fallback is explicit and tested. Jina/trafilatura are implementation details, not the product promise; dependency versions are visible in `doctor --json` and release checks. |
| Native recurrence prompts | README carries Claude Code routine, Codex automation, and ChatGPT scheduled-task prompts without claiming ChatGPT rendered a local PDF unless a runner is available. |
| Source onboarding durable path | `sources check --newsroom`, scaffolded-newsroom auto-detection, collector recipes, staging, queue inspection, and fresh-friend smoke all exercise reader-owned sources. |
| Compaction-safe edition loop | `edition prepare` writes durable edition files; `edition apply-feedback` records accepted/rejected feedback into the smallest supported newsroom files, including `preferences/` and `specs/`. |
| Visual/editor guidance | Composing docs, CSS/style guardrails, `visual-provenance` review findings, tests, and the edition skill require visual QA before delivery. |
| Plugin surfaces | Codex and Claude plugin validation plus install/host plugin smoke pass from the shared skill tree, locked to exactly `setup`, `edition`, and `writing` for 0.8.x. |

## Release Checklist

Completed:

1. Confirmed worktree clean before release.
2. Re-ran the full local verification block.
3. Pushed batched commits to `main`.
4. Tagged `v0.8.2` on the release commit.
5. Built and published clean artifacts through GitHub Actions.
6. Verified PyPI reports `0.8.2`.
7. Clean-installed `morning-paper[pretty]==0.8.2` from PyPI.
8. Ran `morning-paper doctor --strict`.
9. Ran `morning-paper demo --open`.
10. Validated Claude Code and Codex plugin installs from the published tag.
