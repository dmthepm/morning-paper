# Collectors — bring your own sources

Morning Paper works best when it starts from the reader's existing source
stack: email and newsletters, Slack or Discord, GitHub, Linear, Main Branch,
local folders, Obsidian vaults, social and video exports, podcast history,
browser/API scrape outputs, saved articles, and files agents already produce.
The built-in demo proves the paper path without credentials; the product is the
reader's own newsroom, not any one input type.

A **collector** is how any of that enters the paper — a work digest, a saved
thread, a local social export, a weekly research roundup, a folder of notes, or
whatever else earns a place on your desk. This page is the contract a collector
has to honor. Write to it and your source flows into the same edition queue,
through the same renderer, under the same page budget.

## Start With A Source Experiment

Do not make an untested scrape, export, or tool call part of the daily routine
just because it worked once in chat. Start with a source experiment:

1. Name the source and the beat it should support.
2. Inspect the source shape: files, API responses, browser output, rate limits,
   credentials, freshness, and privacy.
3. Write a short ledger entry in `SOURCES.md`: what exists, what is useful,
   what is sensitive, what should be skipped, and which tool was tested.
4. Run the smallest collector or converter once and stage markdown.
5. Decide whether it becomes recurring, stays ad hoc, or gets rejected.

This is especially important for social platforms, browser/API scrape tools,
chat exports, and local data dumps. Morning Paper wants beats with judgment,
not a fragile pile of raw links.

## What a collector is

A collector is **any script or agent workflow you run before you compose**. It
can be a Python file, a shell pipeline, a Claude Code routine, a Codex
automation, a local command, or a manual export. The engine does not care what
language it is or how it runs. Its only job is to turn a source into **staged
material**: markdown the editor will read when it composes today's paper.

Collectors are yours. They live in your private newsroom repo (the `setup`
skill scaffolds a `collectors/` directory for exactly this), never in the
public engine. The engine gives you a stable place to drop their output and a
budget-aware queue to read it back — nothing about your sources, credentials,
or scraping logic ever touches the engine repo.

## Where a collector writes (the staging contract)

Staged material lives in a date-keyed staging directory under the output
directory (`outputs.directory` in your config, default
`~/.local/share/morning-paper`):

```text
<outputs.directory>/staging/<YYYY-MM-DD>/queue.json     # the manifest
<outputs.directory>/staging/<YYYY-MM-DD>/<slug>.md      # one file per item
```

The date is **the edition the item is for**. Edition collectors run as part of
today's compose pass, so they should target today's edition date explicitly.
Ad hoc "read this later" staging still defaults to tomorrow when you call
`morning-paper stage` without `--date`.

You have two ways to write into it.

### The easy way: `morning-paper stage` (recommended)

Let the engine own the file layout, slug collisions, the page estimate, and the
honesty flags. Your collector just calls the CLI once per item:

```bash
# A URL — fetched and extracted exactly like `print`, with the same
# truncation / extractor-fallback honesty notes recorded in the queue:
morning-paper stage "https://example.com/some-article" --title "Optional title"

# A local markdown file your collector already produced:
morning-paper stage ~/tmp/reddit-digest.md --title "r/selfhosted, this week"

# Target a specific edition date (defaults to tomorrow):
morning-paper stage report.md --date 2026-06-14
```

Each call prints a JSON receipt — slug, word count, estimated pages, and any
honesty flags — so an agent collector can report "that adds ~3 pages; it's in
the queue." This is the same path the contributor inbox uses, so a staged item
is identical no matter how it arrived.

### The direct way: write the files yourself

If you would rather not shell out per item (a high-volume collector, an offline
build), write the staging files directly. Append one entry per item to
`queue.json` and drop a matching `<slug>.md`. A queue entry looks like:

```json
{
  "slug": "r-selfhosted-this-week",
  "kind": "file",
  "source": "https://reddit.com/r/selfhosted/top",
  "title": "r/selfhosted, this week",
  "words": 640,
  "est_pages": 2,
  "staged_at": "2026-06-13T18:04:00-04:00",
  "truncated": false,
  "warning": "",
  "extractor_note": "",
  "contributor": ""
}
```

Honesty is part of the contract, not an afterthought. If your collector only
captured a partial source, set `truncated: true` and put a plain-language
reason in `warning` ("paywall cut the body after 3 paragraphs"). If the content
left the machine through a third-party service, say so in `extractor_note`. The
editor surfaces these notes rather than printing a clipped article as if it were
whole. `slug` must be unique within the day; `est_pages` is your honest page
estimate (the CLI computes it from a real layout pass — if you are writing the
file by hand, a words-per-page heuristic of roughly 550 words/page is the
engine's own fallback).

`kind` is free-form metadata: `url`, `file`, or `note` are the conventions the
built-in paths use.

## Reading the queue back

Whatever wrote it, the editor reads the same queue:

```bash
morning-paper queue                  # what's staged vs the page budget (JSON)
morning-paper queue --date 2026-06-14
morning-paper queue list --date 2026-06-14
morning-paper queue show <slug> --date 2026-06-14 --content
morning-paper queue remove <slug> --date 2026-06-14
```

`queue` reports the item list, total estimated pages, your `page_budget`, and
how many pages remain; `show` reads the staged markdown; `remove` drops an item
and its staged file. The compose step can know what fits before it lays a
single column. Anything in the queue was put there on purpose (by you, a
collector, or a trusted contributor) and is treated as belonging in the paper
unless the editor removes it.

## Output formats

A staged `.md` file is **markdown**, and it may contain the same raw HTML and
chart directives (`mp-bars`, `mp-spark`, `mp-stats`) the composer uses — see
[docs/composing.md](composing.md) for the class vocabulary. A collector can
either:

- hand the engine a **URL** and let `stage` fetch and render it, or
- produce its own **markdown** (already-formatted prose, tables, charts) and
  stage that.

JSON only appears in `queue.json` (the manifest) — the staged *content* is
always markdown, because markdown is the durable intermediate the renderer
consumes.

## Collectors run at compose time, outside the page budget

A collector runs **before** composition, during the edition skill's "Collect"
step. Running a collector does not, by itself, cost pages — it fills the queue.
The page budget is enforced later, when the editor composes: it reads the queue
with `morning-paper queue`, weighs everything staged against `page_budget`, and
cuts the weakest material to fit. So a collector can stage generously; the
editor decides what survives to print. A collector that stages ten pages into a
twelve-page budget has not broken anything — it has given the editor choices.

## The shape of a minimal collector

```bash
#!/usr/bin/env bash
# collectors/shipped.sh — a "shipped while you slept" section.
set -euo pipefail

edition_date="${1:-$(date +%F)}"
tmp="$(mktemp -t shipped.XXXXXX).md"

{
  echo "# Shipped while you slept"
  echo
  gh search prs --author=@me --merged --merged-at=">$(date -v-1d +%F 2>/dev/null || date -d yesterday +%F)" \
    --json title,url,repository \
    | jq -r '.[] | "- [\(.title)](\(.url)) — \(.repository.name)"'
} > "$tmp"

# Only stage if there's a body beyond the heading — honest empty beats a fake.
# `stage` takes a real file or a URL; write a temp file rather than piping into
# it (the CLI checks for a regular file, so /dev/stdin and `<(...)` don't work).
if [ "$(grep -c '^- ' "$tmp")" -gt 0 ]; then
  morning-paper stage "$tmp" --title "Shipped" --date "$edition_date"
fi
rm -f "$tmp"
```

That is the whole idea: a source turns into markdown and gets staged. A
collector can be tiny because the durable contract is simple: gather something
the reader already values, mark how trustworthy and complete it is, and let the
editor decide whether it earns space.

## Local drop-folder collector

Use this when the reader already has files somewhere: an Obsidian export, a
synced folder, a generated report directory, or source dumps from another
agent. It does not move the source files; it stages copies into the edition
queue.

```bash
#!/usr/bin/env bash
# collectors/local-drop.sh — stage files from inbox/ for the current edition.
set -euo pipefail
source "$(dirname "$0")/_lib.sh" "${1:-$(date +%F)}"

DROP_DIR="${MORNING_PAPER_DROP_DIR:-$(dirname "$0")/../inbox}"
mkdir -p "$DROP_DIR"
shopt -s nullglob

count=0
unsupported=()
for file in "$DROP_DIR"/*; do
  [ -f "$file" ] || continue
  base="$(basename "$file")"
  case "$base" in .* ) continue ;; esac
  case "$base" in README.md ) continue ;; esac
  case "$file" in
    *.md|*.markdown)
      stage_markdown "${base%.*}" "$file" && count=$((count + 1))
      ;;
    *.txt)
      tmp="$(mktemp -t morning-paper-drop.XXXXXX).md"
      { echo "# ${base%.*}"; echo; cat "$file"; } > "$tmp"
      stage_markdown "${base%.*}" "$tmp" && count=$((count + 1))
      rm -f "$tmp"
      ;;
    *.url)
      url="$(grep -Eo 'https?://[^[:space:]]+' "$file" | head -1 || true)"
      if [ -n "$url" ]; then
        stage_url "${base%.*}" "$url" && count=$((count + 1))
      fi
      ;;
    *)
      unsupported+=("$base")
      ;;
  esac
done

if [ "$count" -gt 0 ]; then
  ok "Local drop ($count)"
else
  unavailable "Local drop" "put .md, .txt, or .url files in $DROP_DIR"
fi
if [ "${#unsupported[@]}" -gt 0 ]; then
  unavailable "Unsupported local drop" "needs a converter collector: ${unsupported[*]}"
fi
```

The `setup` skill scaffolds this exact pattern into your newsroom's
`collectors/` directory — `_lib.sh` (the shared `stage`-based helpers),
`run_all.sh` (run every collector, then print the queue), and worked examples
(`shipped.sh`, `read.sh`, and `local-drop.sh`). Start from those rather than
from a blank file.

If `local-drop.sh` reports unsupported files, do not make the engine bigger.
Write a converter collector in the private newsroom. Start from the scaffolded
`collectors/CONVERTERS.md` or the public
[source conversion playbook](source-conversion.md), then stage the converted
markdown with `morning-paper stage`.
