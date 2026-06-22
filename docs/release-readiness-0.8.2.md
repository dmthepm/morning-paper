# Morning Paper 0.8.2 Release Readiness

Status: local release candidate, not published.

Date: 2026-06-22

## Release Line

- Local package version: `0.8.2`
- Public PyPI version verified on 2026-06-22: `0.8.1`
- Latest local tag: `v0.8.1`
- Local branch state at latest audit: `main` ahead of `origin/main` by 14
  commits

0.8.2 is ready for release review from the local repo, but it still needs the
normal publish sequence: push commits, tag `v0.8.2`, build clean artifacts,
publish to PyPI, then verify PyPI, tag, install, doctor, demo, and plugin
surfaces again.

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
- Hacker News is no longer a friend-facing identity claim. It remains a legacy
  optional built-in source in the engine and tests.
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
  instead of only the broad desk files.
- The shipped plugin surface is locked to exactly `setup`, `edition`, and
  `writing` for 0.8.x. Future newsroom desk skills are documented as design
  direction and cannot leak into the plugin without validation failures.
- Native recurrence is framed through the host's own primitive: Codex
  automations, Claude Code routines, or ChatGPT scheduled tasks. The CLI
  `routine` command remains a local fallback.
- Visual integration guardrails now cover chart and illustration width,
  label-density, print suitability, captions/source notes, and review
  expectations.

## Verification Run

The current local candidate has been checked with:

```bash
python -m pytest
python scripts/setup_scaffold_smoke.py  # run from a clean current [pretty] env when ambient Python is stale
python scripts/fresh_friend_smoke.py
python scripts/install_smoke.py
python scripts/host_plugin_smoke.py
python scripts/validate_codex_plugin.py
claude plugin validate --strict /Users/devonmeadows/Documents/GitHub/morning-paper
python3 scripts/release_candidate_check.py --outdir /tmp/morning-paper-rc-082 --install-check
```

Last full local result: `211 passed`.

The release-candidate artifact check builds a clean wheel and sdist, installs
both with `[pretty]`, verifies the reported core dependency and print-stack
versions, verifies WeasyPrint 69.0, runs `doctor --strict`, and renders a
two-page demo PDF.

Local machine note: the ambient system Python currently has stale WeasyPrint
68.1 and trafilatura 2.0.0, so strict setup smoke fails there by design. A
clean isolated install of the current project with `[pretty]` resolves
WeasyPrint 69.0 and trafilatura 2.1.0 and passes setup smoke.

## Completion Gate Map

| Gate | Evidence |
| --- | --- |
| Docs and skills agree | README, `AGENTS.md`, setup/edition skills, changelog, and product-readiness docs use the same setup/source/feedback model. |
| README stays concise and true | README now keeps details to setup, sources, daily routine, styles, agents, and development. |
| No stale HN identity | Friend-facing docs describe the whole source stack; HN remains only as an optional legacy built-in source and historical changelog/test fixture. |
| No stale scraper assumption | Local extraction is default; remote fallback is explicit and tested. Jina/trafilatura are implementation details, not the product promise; dependency versions are visible in `doctor --json` and release checks. |
| Native recurrence prompts | README carries Claude Code routine, Codex automation, and ChatGPT scheduled-task prompts. |
| Source onboarding durable path | `sources check --newsroom`, scaffolded-newsroom auto-detection, collector recipes, staging, queue inspection, and fresh-friend smoke all exercise reader-owned sources. |
| Compaction-safe edition loop | `edition prepare` writes durable edition files; `edition apply-feedback` records accepted/rejected feedback into the smallest supported newsroom files, including `preferences/` and `specs/`. |
| Visual/editor guidance | Composing docs, CSS/style guardrails, tests, and the edition skill require visual QA before delivery. |
| Plugin surfaces | Codex and Claude plugin validation plus install/host plugin smoke pass from the shared skill tree, locked to exactly `setup`, `edition`, and `writing` for 0.8.x. |

## Release Checklist

Before publishing:

1. Confirm worktree clean.
2. Re-run the full verification block above.
3. Push the batched commits.
4. Tag `v0.8.2` on the release commit.
5. Build and publish clean artifacts.
6. Verify PyPI reports `0.8.2`.
7. Clean-install `morning-paper[pretty]` from PyPI.
8. Run `morning-paper doctor --strict`.
9. Run `morning-paper demo --open`.
10. Validate Claude Code and Codex plugin installs from the published repo.

Do not call the release done until the published package, tag, local binary,
demo PDF, and both plugin surfaces are verified directly.
