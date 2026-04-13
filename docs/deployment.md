# Deployment

## Current Status

This extracted repo has not been pushed anywhere yet.

Nothing in this bundle has been automatically deployed back to Thoth.

The extracted assembly path is now real enough to smoke test:

- `scripts/assemble_brief.py` is implemented and fixture-backed
- `scripts/visual_review.py` is implemented as a starter full-page review tool
- `scripts/smoke_test.sh` can run repeated end-to-end smoke tests and compare hashes
- local compile checks pass
- render still needs to happen on Thoth because this Mac is missing the full PDF review toolchain

## Durability Note

`md-to-pdf` output is visually stable but not byte-stable. Headless Chrome embeds run-specific PDF metadata
(creation/modification timestamps and localhost title metadata), so durability should be checked with:

- assembled markdown hash
- page screenshot hash set
- normalized review signature

Do not use raw PDF SHA256 alone as the cutover gate.

## Intended Deployment Flow

1. commit and push this repo to GitHub
2. clone it onto Thoth in a stable path
3. update the `06:00` and `07:00` Hermes cron jobs to call repo-owned scripts
4. validate the runtime paths, review artifact generation, and Hermes-native Telegram routing

## Thoth Target Shape

Recommended eventual path:

`/Users/thoth/projects/morning-brief`

## Cutover Rule

Do not point cron at this repo until:

- assembly entrypoint is real
- visual review is real
- fixture render tests exist
- golden outputs are approved
- Hermes cron paths are updated to repo-owned scripts with absolute Thoth paths
