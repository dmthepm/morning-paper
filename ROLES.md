# Morning Paper Roles

Morning Paper works best when an edition run feels like a small private
newsroom. The host agent is the orchestrator. It assigns work, calls the CLI,
keeps the run moving, and decides whether to use separate context windows,
subagents, profiles, or a single sequential pass.

The roles below are portable. One host may call them subagents, another may map
them to profiles, models, or plain sequential passes. The contract is the same:
each role reads the shared edition folder, does one job, and leaves one
markdown handoff in `editions/<date>/desks/`.

A tiny/simple run can ship without every desk. A substantial edition
(8+ estimated/rendered pages, or any broad source run) must include the late
desks: editor, copy desk, art desk, and producer. Reporter handoffs alone are
not enough for a real paper.

## Role Order

1. `01-orchestrator.md` - starts, resumes, assigns, calls CLI commands, and
   owns delivery.
2. `02-assignment-editor.md` - turns source health and reader priorities into
   the day's assignments.
3. `03.N-<beat>-reporter.md` - reports a source family or beat. These can run
   in parallel: `03.1-x-reporter.md`, `03.2-articles-reporter.md`,
   `03.3-email-reporter.md`, `03.4-work-reporter.md`.
4. `04-editor.md` - selects, cuts, requests more reporting if needed, and
   shapes the edition.
5. `05-copy-desk.md` - tightens language, labels, headlines, and source
   clarity.
6. `06-art-desk.md` - checks page shape, visual furniture, Desk Sheet, and
   print readability.
7. `07-producer.md` - verifies the run can ship, using the run ticket and PDF
   proofs.
8. `08-taste-editor.md` - after reader feedback, updates the smallest durable
   newsroom file.

## Artifact Contract

Each role writes one markdown file with YAML frontmatter and a short body. Do
not split role handoffs into paired JSON and markdown files.

```markdown
---
role: x-reporter
phase: "03.1"
status: ready
date: 2026-06-26
inputs:
  - source-inventory.json
  - assignment-board.json
handoff:
  candidates: 8
  repeats_cut: 2
  needs_followup: false
---

## What I Checked
- Sources, commands, date ranges, limits, and missing access.

## Findings
- Source-backed findings with URLs or local paths.

## Candidates
- Items that may earn ink, why they matter, and repeat risk.

## Cuts
- Interesting material that should not print today.

## Handoff
- What the next role should do.
```

Use `status: ready`, `status: notes`, or `status: blocked`. If a role blocks,
say what is missing and what would unblock it. Do not pretend a role ran if it
did not run.

## Shared Rules

- The agent composes. The CLI renders and checks.
- Missing data prints "not configured" or "nothing today"; never invent source
  facts.
- Beat reporters should find more than the paper needs. The editor chooses
  what earns space.
- The editor checks memory and ledgers before printing repeats.
- Page budgets are ceilings and appetite signals, not quotas. A thin honest
  paper is better than filler.
- Keep process pages small. Unless the reader asks, source/run-status material
  belongs in handoffs and the run ticket, not in the reader's pages.
- The art desk protects readability: printer-friendly, accessible, no gradient
  decoration, no feed chrome.
- The producer does not make the paper better by adding prose. It makes the
  run safer by proving what is ready, noted, or blocked.
- The taste editor changes the reader's durable newsroom, not this public repo.

## References

- [docs/roles/orchestrator.md](docs/roles/orchestrator.md)
- [docs/roles/assignment-editor.md](docs/roles/assignment-editor.md)
- [docs/roles/beat-reporter.md](docs/roles/beat-reporter.md)
- [docs/roles/editor.md](docs/roles/editor.md)
- [docs/roles/copy-desk.md](docs/roles/copy-desk.md)
- [docs/roles/art-desk.md](docs/roles/art-desk.md)
- [docs/roles/producer.md](docs/roles/producer.md)
- [docs/roles/taste-editor.md](docs/roles/taste-editor.md)
