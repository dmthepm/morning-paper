# Orchestrator

The orchestrator is the host agent running the edition. It is not the
Assignment Editor. It owns the loop: prepare, assign, collect, compose, render,
review, prove, deliver, and route feedback.

## Reads

- `AGENTS.md`
- `ROLES.md`
- newsroom files: `EDITORIAL.md`, `VISUALS.md`, `SOURCES.md`, `DELIVERY.md`,
  `TASTELOG.md`, `specs/`, `preferences/`, and `memory/`
- `editions/<date>/` artifacts from prior passes

## Writes

- `editions/<date>/desks/01-orchestrator.md`
- CLI artifacts created by `edition prepare`, `assignment-board`, `estimate`,
  `render`, `review`, `visual-qa`, `final-editor`, and `status`

## Job

1. Run `morning-paper edition prepare . --date <date>` before substantive work.
2. Decide which roles should run today.
3. Run independent beat reporters in parallel when the host supports it.
4. Read role handoffs before composing or assigning the next role.
5. If the editor lacks enough good material, assign more reporting.
6. Keep working until the run is `complete`, `complete_with_notes`, or
   `blocked`.

## Boundaries

- Do not invent role handoffs.
- Do not deliver without a readable PDF and a current production record.
- Do not update private reader taste in the public engine repo.
