# Smoke Test — 2026-04-05

## Scope

End-to-end smoke test of the extracted Morning Brief repo on Thoth.

## Runtime

- host: `thoth`
- extracted repo path: `/Users/thoth/projects/morning-brief-extracted-smoke`
- fixture: `tests/fixtures/sample-run-2026-04-05`

## Commands Run

```bash
python3 scripts/assemble_brief.py \
  --template templates/typewriter-v5.md \
  --candidates tests/fixtures/sample-run-2026-04-05/candidates.md \
  --rabbit-holes tests/fixtures/sample-run-2026-04-05/rabbit-holes.md \
  --content-drafts tests/fixtures/sample-run-2026-04-05/content-drafts.md \
  --context-summary tests/fixtures/sample-run-2026-04-05/context-summary.md \
  --output tests/fixtures/sample-run-2026-04-05/assembled-brief.md \
  --metadata-output tests/fixtures/sample-run-2026-04-05/assembled-brief.json \
  --date-label "5 APRIL 2026"

bash scripts/render_pdf.sh \
  tests/fixtures/sample-run-2026-04-05/assembled-brief.md \
  tests/fixtures/sample-run-2026-04-05/assembled-brief.pdf

python3 scripts/visual_review.py \
  --pdf tests/fixtures/sample-run-2026-04-05/assembled-brief.pdf \
  --out-dir tests/fixtures/sample-run-2026-04-05/review
```

## Result

- assembly: passed
- render: passed
- visual review: passed with warnings
- output page count: `4`

## Artifacts

On Thoth:

- `/Users/thoth/projects/morning-brief-extracted-smoke/tests/fixtures/sample-run-2026-04-05/assembled-brief.md`
- `/Users/thoth/projects/morning-brief-extracted-smoke/tests/fixtures/sample-run-2026-04-05/assembled-brief.pdf`
- `/Users/thoth/projects/morning-brief-extracted-smoke/tests/fixtures/sample-run-2026-04-05/review/visual-review.json`
- `/Users/thoth/projects/morning-brief-extracted-smoke/tests/fixtures/sample-run-2026-04-05/review/page-01.png`
- `/Users/thoth/projects/morning-brief-extracted-smoke/tests/fixtures/sample-run-2026-04-05/review/page-02.png`
- `/Users/thoth/projects/morning-brief-extracted-smoke/tests/fixtures/sample-run-2026-04-05/review/page-03.png`
- `/Users/thoth/projects/morning-brief-extracted-smoke/tests/fixtures/sample-run-2026-04-05/review/page-04.png`

Copied back into this workspace:

- `.context/morning-brief-smoke-review/assembled-brief-sample-2026-04-05.pdf`
- `.context/morning-brief-smoke-review/visual-review.json`
- `.context/morning-brief-smoke-review/page-01.png`
- `.context/morning-brief-smoke-review/page-02.png`
- `.context/morning-brief-smoke-review/page-03.png`
- `.context/morning-brief-smoke-review/page-04.png`

## Warnings

The current `visual_review.py` heuristic flagged:

- `Page 2 mentions Hacker News but heading format may be off.`
- `Page 3 mentions Hacker News but heading format may be off.`

These are false positives from a crude heuristic, not confirmed layout failures. The HN section starts on page 3, but the full-read content on page 2 references Hacker News in body copy.

## Follow-Up

- repeated-run durability check now passes on the right contract:
  - markdown hash stable across three runs
  - page screenshot hash stable across three runs
  - normalized review signature stable across three runs
- raw PDF byte hash is not stable because `md-to-pdf` / headless Chrome embeds run-specific metadata:
  - dynamic localhost port in PDF title metadata
  - changing creation/modification timestamps
- durability should therefore be judged on markdown + visual/review signatures, not raw PDF bytes
- add approved golden outputs, not just a smoke-test fixture
- only then rewire Hermes cron to this repo
