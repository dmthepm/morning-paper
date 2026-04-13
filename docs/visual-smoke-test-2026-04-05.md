# Visual Smoke Test — 2026-04-05

## Goal

Verify that the recovered `Visual of the Day` image-prep tool works in the real Thoth runtime for both:

- remote image URLs
- local screenshot/file inputs

## Runtime

- host: `thoth`
- script: `/Users/thoth/projects/morning-brief-extracted-smoke/scripts/bw_image.py`

## Tests Run

### 1. Remote URL input

```bash
python3 scripts/bw_image.py \
  https://www.python.org/static/community_logos/python-logo-master-v3-TM.png \
  --output /tmp/brief-visual-url.png \
  --caption "Python logo test"
```

Observed:

- load succeeded
- output image written
- markdown embed snippet printed

### 2. Local screenshot input

```bash
python3 scripts/bw_image.py \
  /Users/thoth/projects/morning-brief-extracted-smoke/tests/fixtures/sample-run-2026-04-05/smoke-runs/20260405-090918/run-01/review/page-01.png \
  --output /tmp/brief-visual-local.png \
  --caption "Local screenshot test"
```

Observed:

- local file load succeeded
- output image written
- markdown embed snippet printed

## Verified Outputs

- `/tmp/brief-visual-url.png`
- `/tmp/brief-visual-local.png`

## Meaning

The visual prep tool is now suitable for the two main nightly-agent sourcing modes:

1. direct remote image extraction from a story page or tweet
2. browser/screenshot capture followed by local file processing

That closes the most important runtime gap for a future `Visual of the Day` lane.
