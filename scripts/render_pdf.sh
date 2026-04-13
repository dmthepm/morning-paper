#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
  echo "Usage: render_pdf.sh <input.md> [output.pdf]" >&2
  exit 2
fi

INPUT_MD="$1"
OUTPUT_PDF="${2:-${INPUT_MD%.md}.pdf}"

if [ ! -f "$INPUT_MD" ]; then
  echo "Input markdown not found: $INPUT_MD" >&2
  exit 1
fi

TMP_EXPECTED="${INPUT_MD%.md}.pdf"
md-to-pdf "$INPUT_MD"

if [ ! -f "$TMP_EXPECTED" ]; then
  echo "md-to-pdf did not produce expected output: $TMP_EXPECTED" >&2
  exit 1
fi

if [ "$TMP_EXPECTED" != "$OUTPUT_PDF" ]; then
  mkdir -p "$(dirname "$OUTPUT_PDF")"
  cp "$TMP_EXPECTED" "$OUTPUT_PDF"
fi

echo "$OUTPUT_PDF"
