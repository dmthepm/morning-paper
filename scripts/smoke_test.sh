#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 2 ] || [ "$#" -gt 3 ]; then
  echo "Usage: smoke_test.sh <fixture_dir> <date_label> [repeat_count]" >&2
  exit 2
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FIXTURE_DIR="$1"
DATE_LABEL="$2"
REPEAT_COUNT="${3:-1}"

if ! [[ "$REPEAT_COUNT" =~ ^[0-9]+$ ]] || [ "$REPEAT_COUNT" -lt 1 ]; then
  echo "repeat_count must be a positive integer" >&2
  exit 2
fi

if [ ! -d "$FIXTURE_DIR" ]; then
  echo "fixture directory not found: $FIXTURE_DIR" >&2
  exit 1
fi

FIXTURE_DIR="$(cd "$FIXTURE_DIR" && pwd)"
RUN_STAMP="$(date +%Y%m%d-%H%M%S)"
RUN_ROOT="$FIXTURE_DIR/smoke-runs/$RUN_STAMP"
SUMMARY_FILE="$RUN_ROOT/summary.tsv"

mkdir -p "$RUN_ROOT"
printf "run\tmd_sha256\tvisual_sha256\treview_signature_sha256\n" > "$SUMMARY_FILE"

for i in $(seq 1 "$REPEAT_COUNT"); do
  RUN_LABEL="$(printf 'run-%02d' "$i")"
  RUN_DIR="$RUN_ROOT/$RUN_LABEL"
  REVIEW_DIR="$RUN_DIR/review"
  mkdir -p "$RUN_DIR"

  python3 "$ROOT_DIR/scripts/assemble_brief.py" \
    --template "$ROOT_DIR/templates/typewriter.md" \
    --candidates "$FIXTURE_DIR/candidates.md" \
    --rabbit-holes "$FIXTURE_DIR/rabbit-holes.md" \
    --content-drafts "$FIXTURE_DIR/content-drafts.md" \
    --context-summary "$FIXTURE_DIR/context-summary.md" \
    --output "$RUN_DIR/assembled-brief.md" \
    --metadata-output "$RUN_DIR/assembled-brief.json" \
    --date-label "$DATE_LABEL"

  bash "$ROOT_DIR/scripts/render_pdf.sh" \
    "$RUN_DIR/assembled-brief.md" \
    "$RUN_DIR/assembled-brief.pdf"

  python3 "$ROOT_DIR/scripts/visual_review.py" \
    --pdf "$RUN_DIR/assembled-brief.pdf" \
    --out-dir "$REVIEW_DIR" \
    --report "$RUN_DIR/visual-review.json"

  MD_SHA="$(shasum -a 256 "$RUN_DIR/assembled-brief.md" | awk '{print $1}')"
  VISUAL_SHA="$(
    find "$REVIEW_DIR" -name 'page-*.png' -type f | sort | while read -r shot; do
      shasum -a 256 "$shot" | awk '{print $1}'
    done | shasum -a 256 | awk '{print $1}'
  )"
  REVIEW_SIG="$(
    python3 - "$RUN_DIR/visual-review.json" <<'PY'
import hashlib
import json
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text())
semantic = {
    "page_count": report["page_count"],
    "errors": report["errors"],
    "warnings": report["warnings"],
    "pages": [
        {
            "page": page["page"],
            "words": page["words"],
            "chars": page["chars"],
            "flags": page["flags"],
            "text_preview": page["text_preview"],
        }
        for page in report["pages"]
    ],
    "pass": report["pass"],
}
payload = json.dumps(semantic, sort_keys=True).encode("utf-8")
print(hashlib.sha256(payload).hexdigest())
PY
  )"
  printf "%s\t%s\t%s\t%s\n" "$RUN_LABEL" "$MD_SHA" "$VISUAL_SHA" "$REVIEW_SIG" >> "$SUMMARY_FILE"
done

MD_UNIQUE="$(tail -n +2 "$SUMMARY_FILE" | awk '{print $2}' | sort -u | wc -l | tr -d ' ')"
VISUAL_UNIQUE="$(tail -n +2 "$SUMMARY_FILE" | awk '{print $3}' | sort -u | wc -l | tr -d ' ')"
REVIEW_UNIQUE="$(tail -n +2 "$SUMMARY_FILE" | awk '{print $4}' | sort -u | wc -l | tr -d ' ')"

echo "run_root=$RUN_ROOT"
echo "md_unique_hashes=$MD_UNIQUE"
echo "visual_unique_hashes=$VISUAL_UNIQUE"
echo "review_signature_unique_hashes=$REVIEW_UNIQUE"

if [ "$MD_UNIQUE" -ne 1 ] || [ "$VISUAL_UNIQUE" -ne 1 ] || [ "$REVIEW_UNIQUE" -ne 1 ]; then
  echo "Smoke test signatures were not stable across repeated runs." >&2
  exit 1
fi
