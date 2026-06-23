# Source Conversion

Morning Paper does not need every source to become a first-class engine
integration. Most sources only need a small private collector that turns the
thing the reader already owns into staged markdown:

```bash
morning-paper stage converted-source.md --title "Source name" --date YYYY-MM-DD
```

Keep converters in the reader's private newsroom, usually under
`collectors/`. Do not move the original source, do not commit credentials, and
do not pretend partial extraction is complete. If the converter skips rows,
uses a remote service, hits a paywall, or only sees metadata, say that in the
staged markdown and/or queue warning.

## Agent Prompt

When `morning-paper sources check --newsroom .` reports unsupported local-drop
files, paste this into the host agent from the private newsroom:

```text
Write a Morning Paper converter collector for the unsupported files in
inbox/. Keep it local-first. Turn the source into markdown, stage it with
morning-paper stage --date YYYY-MM-DD, and report exactly what was skipped,
truncated, inferred, or unavailable. Do not move or mutate the originals. Read
collectors/CONVERTERS.md and docs/source-conversion.md if present.
```

## CSV Exports

Use for histories, analytics, ticket exports, reading logs, watch history,
calendar exports, or spreadsheet dumps.

Pattern:

1. Inspect columns and row count.
2. Choose the few columns that make editorial sense.
3. Group by date, source, project, person, or topic.
4. Emit markdown tables only when the table helps; otherwise write prose plus
   bullets.
5. Stage one digest, not hundreds of raw rows.

Minimal Python sketch:

```python
import csv
from pathlib import Path

source = Path("inbox/export.csv")
rows = list(csv.DictReader(source.open()))
out = Path("/tmp/export-digest.md")
with out.open("w") as f:
    f.write("# Export digest\n\n")
    f.write(f"Rows inspected: {len(rows)}.\n\n")
    for row in rows[:25]:
        title = row.get("title") or row.get("name") or row.get("url") or "item"
        date = row.get("date") or row.get("created_at") or ""
        f.write(f"- {date} {title}\n")
```

## JSON Exports

Use for app exports, API dumps, social history, browser history, issue lists,
or agent logs.

Pattern:

1. Load the JSON and identify whether it is a list, object, or nested export.
2. Select the records relevant to the edition date or current question.
3. Preserve IDs/URLs when present so claims are traceable.
4. Emit source notes when fields are missing or nested data was ignored.

## PDFs

Use for reports, slides exported as PDFs, receipts, papers, or saved articles.

Pattern:

1. Prefer a local text extractor already on the machine (`pdftotext`, Python
   libraries, or host-agent document tools).
2. If extraction is weak, stage a short source trace instead of a fake full
   read.
3. Mention page count and extraction quality in the markdown.
4. For scanned PDFs, ask before OCR if it may be slow or privacy-sensitive.

## Obsidian Vaults And Folders

Use for notes, daily logs, project folders, reports, and agent-produced files.

Pattern:

1. Do not ingest the whole vault by default.
2. Select by modified date, folder, tag, backlinks, or filenames the reader
   asked about.
3. Preserve wikilinks as text or convert them to readable names.
4. Stage a digest with links back to local paths, not a raw dump.

## GitHub, Main Branch, And Work Systems

Use for repos, pull requests, issues, decisions, bets, pushes, risks, asks, and
team activity.

Pattern:

1. Prefer an existing CLI or local export the reader already uses.
2. Group by project and decision, not by tool event order.
3. Separate shipped work, blocked work, open asks, and things needing the
   reader.
4. Stage one operational digest with source links.

## Social, Video, Podcast, And Browser Exports

Use for Twitter/X, YouTube, TikTok, Instagram, Spotify/podcast history, browser
history, or local-first feed tools.

Pattern:

1. Treat this as taste/source intelligence, not an excuse to re-create a feed.
2. Group by story, topic, creator, channel, or repeated interest.
3. Prefer "what this says about the reader's algorithm" over raw chronology.
4. Mark private or sensitive analysis plainly before printing.

## What Not To Build Yet

- No hosted OAuth registry inside the engine.
- No scraper marketplace as product identity.
- No silent remote extraction.
- No broad import of a private archive without a small smoke pass first.

The useful primitive is smaller: source becomes markdown, markdown gets staged,
the editor decides what earns ink.
