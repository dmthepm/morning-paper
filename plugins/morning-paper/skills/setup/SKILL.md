---
name: setup
description: >
  Morning Paper cold-start: install the engine, interview the reader, scaffold
  their private newsroom repo with working contracts (not empty folders), and
  offer host-native recurring setup. Use on first run, when
  ~/.config/morning-paper/config.yaml is missing, or when the user says
  "set up my morning paper", "onboard me", "configure morning paper".
---

# Morning Paper — Setup

You are setting up a personal newsroom. The outcome: a config, a private
"newsroom" repo of preferences the user owns **scaffolded with real working
contracts the edition skill obeys** (not four empty directories), and
(optionally) a recurring run in the host the reader already uses. Degrade
honestly at every step — a paper with two sources beats a broken setup with ten.

The keystone of this skill is §5: setup must **write** the newsroom's
contracts. A friend who finishes setup has a `CLAUDE.md`, section specs led by
The Read, newsroom-native taste files (`EDITORIAL.md`, `VISUALS.md`,
`SOURCES.md`, `DELIVERY.md`, `TASTELOG.md`), an empty reads-ledger, a voice
template, an editions dir, and a collector contract with worked examples —
everything the `edition` skill reads. A scaffold of empty folders is a failed
setup.

Resumability rule: as soon as the newsroom path exists, create and keep current
`setup-state.json` and `SETUP.md`. After every major step, update them before
continuing. If setup resumes after compaction or a fresh agent picks it up,
read those two files first and continue from `next_action`.

Use the CLI to update setup state rather than hand-editing JSON:

```bash
morning-paper newsroom state /path/to/newsroom \
  --set demo.pdf_path="/absolute/path/demo.pdf" \
  --set demo.opened_on_screen=true \
  --set doctor.strict_passed=true \
  --pending "Which source should I add first?"
```

## 1. Engine

```bash
uv tool install --python 3.13 "morning-paper[pretty]"   # canonical; pipx install also works.
                                                         # Use bare pip only inside a venv —
                                                         # PEP 668 blocks it on brew/system Python.
morning-paper --version
morning-paper doctor --strict   # must report: typewriter ready and renderer self-test passed
morning-paper demo --output ./morning-paper-demo --open
morning-paper init
```

The plugin updates the skills; the engine on PyPI updates separately. Tell the
reader: to pull a newer engine later, run `uv tool upgrade morning-paper` (add
`--reinstall` if a CDN lag serves the old version).

## 2. The interview (conversational, not a form)

Ask in 2-3 messages, not twenty. Capture:
- **Who they are / what they run** — work, projects, what "useful every morning"
  means to them. This seeds `profile` in config.yaml, the editor's voice, and
  the section specs you scaffold in §5.
- **Sources** — what they already have across work and life: email and
  newsletters, Slack/Discord, GitHub activity, Linear tickets, Main Branch,
  local folders, Obsidian vaults, exports, browser/API scrape outputs, Twitter/X
  or other social feeds, YouTube/podcast history, and agent-produced files.
  RSS/full-text feeds are useful when available; paid feed URLs are credentials,
  so store them in `~/.config/morning-paper/env.sh`, never in a repo.
- **Shape** — `page_budget` (suggest 12-20), how many full reads per edition,
  style (`morning-paper styles` lists the family of four — broadsheet,
  brief, field-card, zine; `broadsheet` is the default recommendation),
  palette (`color` for inkjets, `mono` for laser).
- **Voice** — how should the paper talk? Offer three registers and write
  the answer to `preferences/voice.md` in the newsroom: *dense operator*
  (every word earns its ink; Strunk defluff pass each edition; maximum
  context per inch), *classic newspaper* (measured, narrative), or
  *explanatory* (more scaffolding, gentler). Density is a preference, not
  a virtue — match the reader.
- **Printer** — CUPS name (`lpstat -p`), duplex capable? Save the print
  command in the newsroom README and in `CLAUDE.md`'s delivery placeholder.

Write their answers into `~/.config/morning-paper/config.yaml`.

## 3. Optional unlocks (collector recipes they write, not engine features)

The engine ships the generic stage/inbox contract any script or agent workflow
can write to. Everything below is a **collector**: a small source bridge the
operator authors and runs at compose time, dropping markdown into the staging
queue. A collector might summarize a work system, stage saved reading, digest a
local folder, or turn a personal export into something the editor can judge.
None of these ship in the engine; they are recipes to build in the newsroom's
`collectors/` (which §5 scaffolds with the contract and three worked examples).
See
[docs/collectors.md](https://github.com/dmthepm/morning-paper/blob/main/docs/collectors.md)
for the contract.

- **Social/export tools**: local Twitter/X exports, browser/API scrapes, or
  services the reader already trusts. Treat these as reader-owned source
  systems, not Morning Paper defaults.
- **Research plugins**: a collector wrapping a tool such as last30days for a
  weekly trends page.
- **gh CLI**: a collector that builds a "shipped while you slept" section from
  their repos (scaffolded as `collectors/shipped.sh` in §5).
- **Local drop folder**: a collector that stages `.md`, `.txt`, and `.url`
  files from a folder the user already owns: Obsidian exports, synced folders,
  agent-produced files, or manual dumps.
Each collector they skip = a section that prints "not configured", never fake data.

## 4. The masthead (the contributor inbox)

Ask: **who should be able to feed this paper?** A spouse, a co-founder, the
one friend who always finds the good stuff — people whose mail should become
pages. If the answer is "nobody yet", skip; the block ships disabled.

If yes:
- Add the `inbox:` block to config.yaml (see docs/inbox.md): `enabled: true`,
  their mail provider's `imap_host`/`imap_user`, and `contributors:` — the
  masthead, a strict allowlist of `{email, name}`. Mail from anyone else is
  never staged.
- The password is an **app password**, never the account password and never
  in config: Gmail at myaccount.google.com/apppasswords (needs 2-Step
  Verification; host `imap.gmail.com`), iCloud at account.apple.com →
  Sign-In and Security → App-Specific Passwords (host `imap.mail.me.com`).
  Store it as `MORNING_PAPER_IMAP_PASSWORD` in
  `~/.config/morning-paper/env.sh` like the other credentials.
- Verify with `morning-paper inbox --dry-run`, then have the user send
  themselves a test mail with "paper" in the subject and poll for real.
- Give the user the sentence to send each contributor: *"See something I
  should read? Email it to me with \"paper\" in the subject — it'll be on my
  desk tomorrow morning."* Tip: a plus address (`you+paper@gmail.com`) plus
  a label/filter keeps the poll out of their main inbox (docs/inbox.md).
- Upsell, honestly labeled: a hosted door (Cloudflare Worker email address)
  for **instant** confirmations instead of poll-time ones is on the roadmap —
  **not yet shipped**. Today's path is the IMAP poll, which the edition skill
  runs every morning anyway.

## 5. The newsroom repo — scaffold the contracts (the keystone)

Create a PRIVATE repo (suggest `<user>/newsroom`) by running the engine's
deterministic scaffold, then personalize it from the interview:

```bash
morning-paper newsroom init /path/to/newsroom --name "<paper name>"
cd /path/to/newsroom
git init
```

Do not stop at `mkdir`: the `edition` skill reads these files; empty folders
make it improvise. The CLI scaffold writes the contract below and safely skips
existing files on rerun unless `--force` is passed. Personalize the placeholders
from the interview, but ship every file. None of this is the engine's content -
it is the reader's owned algorithm, in files they can edit.
After each personalization step, run `morning-paper newsroom state . --set ...`
so `SETUP.md` and `setup-state.json` stay true.
Use `morning-paper sources list --newsroom .` after scaffolding, and
`morning-paper sources check --newsroom .` when the reader is ready to verify
source entries and collector syntax. Read its `source_model`, `newsroom.local_drop`, and
`next_actions` before asking more source questions.
If your shell is already inside the scaffolded newsroom root, plain
`morning-paper sources check` auto-detects the newsroom; use `--newsroom .`
when you want the path to be unambiguous in logs.

```
newsroom/
  SETUP.md                   # resumable setup journal for humans and agents
  setup-state.json           # resumable setup state, updated after each step
  CLAUDE.md                  # the operating constitution (the keystone)
  EDITORIAL.md               # what earns ink, gets cut, and becomes The Read
  VISUALS.md                 # the visual desk: charts, images, PDF/email rules
  SOURCES.md                 # source purpose, trust, cadence, health, backlog
  DELIVERY.md                # PDF, print, email/article, archive preferences
  TASTELOG.md                # accepted/rejected durable taste changes
  specs/
    _template.md             # the five-field section contract
    the-read.md              # THE LEAD intelligence section
    front-page.md            # masthead + one headline as a judgment
    reading.md               # full reads + menu, source-mix + freshness law
  preferences/
    voice.md                 # the three-register voice template (from §2)
    algorithm-prior.yaml     # the owned-algorithm artifact (commented stub)
    checks.yaml              # review thresholds/mutes (commented stub)
  collectors/
    _lib.sh                  # the collector contract helpers (stage-based)
    run_all.sh               # run every collector, write a status report
    shipped.sh               # example: "shipped while you slept" (gh)
    read.sh                  # example: stage a URL as tomorrow's read
    local-drop.sh            # example: stage files from inbox/
  memory/
    reads-ledger.md          # empty; one line per printed read
    MEMORY.md                # empty thread index
    threads/README.md        # the advance-or-kill convention
  editions/
    .gitignore               # *.pdf — the landing spot for each day's archive
  examples/
    edition-skeleton.md      # the masthead/section furniture starting point
```

Explain the point in one line: *your feed has an algorithm you can't see; your
paper's algorithm is files you can read and edit.*

### Resumable setup files

Write these first, then keep them current.

**`setup-state.json`**:

```json
{
  "status": "in_progress",
  "updated_at": "YYYY-MM-DDTHH:MM:SSZ",
  "newsroom_path": "/absolute/path/to/newsroom",
  "installed_version": "",
  "engine_install_command": "uv tool install --python 3.13 \"morning-paper[pretty]\"",
  "doctor": {
    "strict_passed": false,
    "renderer_self_test_passed": false,
    "python": "",
    "weasyprint": ""
  },
  "demo": {
    "pdf_path": "",
    "opened_on_screen": false
  },
  "plugin_state": {
    "claude_code": "unknown",
    "codex": "unknown"
  },
  "source_choices": {
    "work_streams": [],
    "personal_feeds": [],
    "local_folders": [],
    "collectors": [],
    "inbox": "ask"
  },
  "printer_choice": {
    "mode": "ask",
    "command": ""
  },
  "pending_questions": [],
  "next_action": "finish interview and write config"
}
```

**`SETUP.md`**:

```markdown
# Morning Paper Setup

## Current Status
- Status: in progress
- Installed version:
- Demo PDF:
- Demo opened on screen: no
- Newsroom path:
- Next action:

## Source Choices
- Work streams:
- Personal feeds:
- Local folders / exports:
- Collectors:
- Inbox:

## Printer
- Mode:
- Command:

## Pending Questions
- None yet.
```

### The contracts to write

**`CLAUDE.md`** — the operating constitution. This is what makes the `edition`
skill obey the newsroom instead of improvising:

```markdown
# Newsroom — operating constitution

The engine renders; this repo decides. The Morning Paper engine lays out and
prints faithfully. *What* runs, in *what order*, in *whose voice* is decided
here, in files I own.

## The law (read in this precedence, top wins)

1. `specs/*` — the section contracts. The Read leads.
2. `EDITORIAL.md` — what earns ink, what gets killed, and what makes The Read.
3. `VISUALS.md` — the visual desk: charts, images, illustrations, PDF/email.
4. `SOURCES.md` — source purpose, trust, cadence, health, and backlog.
5. `DELIVERY.md` — PDF, print, email/article, archive preferences.
6. `preferences/voice.md` — how the paper talks. Overrides any engine default.
7. `preferences/algorithm-prior.yaml` — my standing interests (absent = ignore).
8. `memory/reads-ledger.md` — everything already printed. Never reprint a read.
9. `editions/<latest>/operator-answers.md` — my triaged ink. Honor it exactly.
10. `TASTELOG.md` — accepted and rejected taste changes over time.
11. `memory/MEMORY.md` + `memory/threads/` — running threads (load on slug match).
12. `collectors/` — my sources. What they don't return prints "not configured".

## The honesty rule

A missing source prints "not configured" — never a fabricated number, headline,
or quote. If a collector returns nothing, say so plainly. The paper is allowed
to notice that yesterday's open question is still open.

## Delivery

<!-- Your print command goes here, duplex flag and all, e.g.
     lp -o sides=two-sided-long-edge -d YourPrinter <pdf>
     or "hand me the PDF path" if you read on screen. -->
```

**`specs/_template.md`** — the five-field contract, so the reader can write
their own sections:

```markdown
# Section: <name>

- **Pages**: <target, e.g. 1–2; or "as earned">
- **Source**: <which collector / feed / staged material feeds this>
- **Content**: <what belongs here, what does not>
- **Voice**: <register for this section; defaults to preferences/voice.md>
- **Failure mode**: <what to print when the source is empty —
  always "not configured", never invented>

> Sections are RENAMEABLE. The label is a preference, not a hardcode — call this
> whatever fits your morning. The engine renders whatever you compose; these
> specs are how you tell the editor what each section is for.
```

**`specs/the-read.md`** — the lead intelligence section. The Read is the paper's
front-of-mind synthesis, not a link dump:

```markdown
# Section: The Read (the lead)

- **Pages**: 1, leading the edition.
- **Source**: everything collected today, read against my standing interests
  (`preferences/algorithm-prior.yaml`) and yesterday's threads.
- **Voice**: judgment first. Lead with the single thing that matters, stated as
  a claim I can act on — not "here is what happened."
- **Failure mode**: a thin news day is honest. Say "quiet morning" and move on;
  never inflate.

## The four moves

The Read earns its lead spot by doing four things a feed cannot:

1. **GAPS** — what is *missing* from today's coverage that I should be asking
   about. The dog that didn't bark.
2. **CONNECTIONS** — two items from different sources that are the same story,
   or that only mean something together.
3. **ALIGNMENT / DRIFT** — is the day's signal pulling toward or away from what
   I said I care about (`[your-project]`, `[your-beat]`)? Name the drift.
4. **NEXT MOVE** — the one thing worth doing today because of all this. Concrete.

## Three rules

- **NO MIRRORING** — never just restate a headline back to me. If The Read says
  what the feed already said, it failed.
- **OUTSIDE-IN** — start from the world, land on my desk; not the reverse.
- **SURPRISE ONCE** — one genuinely non-obvious connection per edition. If
  everything is obvious, dig further or admit the day was quiet.

Replace `[your-project]` / `[your-beat]` with your own — these are the lanes The
Read measures the day against.
```

**`specs/front-page.md`**:

```markdown
# Section: Front Page

- **Pages**: shares page 1 with The Read.
- **Source**: the masthead furniture + the day's strongest single item.
- **Content**: the masthead (paper name + dateline), and ONE headline written
  as a judgment, not a label — a sentence with a verb that tells me what to
  think, plus 2–4 teasers pointing deeper into the edition.
- **Voice**: a front page has a point of view. The headline is an argument.
- **Failure mode**: no strong item → a quiet, honest masthead. Never a
  manufactured lead.
```

**`specs/reading.md`**:

```markdown
# Section: Reading

- **Pages**: as earned by what's staged; the back half of the edition.
- **Source**: full reads from the staging queue (`morning-paper queue`) and
  full-text feeds, plus a short menu of lighter items.
- **Content**: entire articles, typeset — not summaries. Then a menu: a few
  one-line "here's what else, and why" pointers.
- **Voice**: let the reads breathe; the menu is terse.
- **Failure mode**: nothing staged → print the menu only, or say the reading
  pile is empty. Never pad.

## Two laws

- **Source mix** — never fill the reading section from a single source. A paper
  that is all one feed is that feed with extra steps.
- **Fresh vs repeat** — check `memory/reads-ledger.md` before printing a read.
  A read already on the ledger is a hard fail; when today's edition ships,
  append today's reads to the ledger. Replace any paid/full-text feed reference
  with your own full-text feeds.
```

**`preferences/voice.md`** — write the three-register template, with the
reader's chosen register marked as active (from §2). Keep it generic.

**`preferences/algorithm-prior.yaml`** — the owned-algorithm artifact. Ship a
commented stub; the editor treats absent/empty as "ignore", so this is safe to
ship blank:

```yaml
# algorithm-prior.yaml — your standing interests, in a file you can read.
# This is the "own your algorithm" artifact: the editor amplifies what you
# say you care about. It NEVER amplifies pure velocity (a thing being loud is
# not a reason to print it) — only revealed intent.
#
# Everything here is OPTIONAL. Absent or empty → the editor ignores it.
#
# version: 1
# revealed_themes:        # topics you keep coming back to — weight UP
#   - [your-theme]
#   - [another-theme]
# recent_search_terms:    # what you've been looking into lately
#   - [a phrase you searched]
# damp:                   # topics to weight DOWN (still printed if it matters)
#   - [a topic you're tired of]
#
# Boundary: amplify intent, never amplify pure-velocity formats. A trending
# format is not an interest.
```

**`preferences/checks.yaml`** — commented stub; `review` reads it when present,
applies defaults when absent:

```yaml
# checks.yaml — tune the `morning-paper review` copy desk. Read, never written.
# Defaults apply to every check when this file is absent or a key is omitted.
#
# version: 1
# thresholds:
#   headline-line-count:
#     warn_at_lines: 3          # flag a head estimated to wrap this many lines
#   headline-length:
#     nudge_at: 60              # nudge a true headline over this many chars
# mute:
#   - check: headline-length
#     when: { section: "Field Notes" }   # this section runs long on purpose
#   - check: stale-dateline
#     scope: global                       # I read evergreens; age is fine
```

**`memory/reads-ledger.md`** — ship EMPTY with one header line:

```markdown
# Reads ledger

<!-- One line per printed read; never reprint a read already listed here.
     The edition skill appends today's reads when the paper ships. -->
```

**`memory/MEMORY.md`** — empty index:

```markdown
# Memory index

<!-- Running threads load on slug match: when today's news matches a thread
     slug below, the editor loads that thread and advances it (second-day lede)
     instead of re-reporting the story cold. One line per thread. -->
```

**`memory/threads/README.md`**:

```markdown
# Threads

A thread is a story you're following across editions. One file per thread.
The convention: each morning, **advance or kill**. A thread either earns a
second-day lede (something moved) or it gets killed (it's over). A thread that
neither advances nor dies for a week is probably dead — kill it.
```

**`collectors/_lib.sh`** — the collector contract, written to the **public
`morning-paper stage` contract** (NOT an `editions/<date>/data/` path — that is
not what the engine reads):

```bash
#!/usr/bin/env bash
# _lib.sh — shared helpers for collectors. Source this from each collector.
#
# THE CONTRACT: a collector turns a source into staged markdown by calling
# `morning-paper stage`. The engine owns the file layout, slug collisions, the
# page estimate, and the honesty flags. Collectors NEVER write engine files by
# hand. Degrade, never fabricate: an empty source stages nothing (the section
# prints "not configured"); it never stages a fake.

set -euo pipefail

# The edition we're collecting FOR. Edition collectors run as part of today's
# compose pass, so their default is today's edition date. Ad hoc `stage`
# calls without --date are still "read this later" and target tomorrow.
EDITION_DATE="${1:-$(date +%F)}"

# stage_markdown <title> <file.md> — stage a markdown file you produced.
stage_markdown() {
  local title="$1" file="$2"
  [ -s "$file" ] || { unavailable "$title" "produced no content"; return 0; }
  morning-paper stage "$file" --title "$title" --date "$EDITION_DATE"
}

# stage_url <title> <url> — let the engine fetch + extract a URL (same path,
# same honesty flags, as the contributor inbox).
stage_url() {
  local title="$1" url="$2"
  morning-paper stage "$url" --title "$title" --date "$EDITION_DATE"
}

# ok / unavailable — print one status line per collector for run_all's report.
ok()          { echo "ok: $1"; }
unavailable() { echo "unavailable: $1 — ${2:-not configured}"; }
```

**`collectors/run_all.sh`**:

```bash
#!/usr/bin/env bash
# run_all.sh — run every collector for the edition date, print a status line
# each. The edition skill runs this in the Collect step, then reads the queue.
set -euo pipefail
cd "$(dirname "$0")"

EDITION_DATE="${1:-$(date +%F)}"
echo "collectors for $EDITION_DATE:"
for c in *.sh; do
  case "$c" in _lib.sh|run_all.sh) continue ;; esac
  echo "--- $c"
  bash "$c" "$EDITION_DATE" || echo "unavailable: $c — exited nonzero"
done
echo "queue:"
morning-paper queue list --date "$EDITION_DATE"
```

**`collectors/shipped.sh`** — the "shipped while you slept" worked example:

```bash
#!/usr/bin/env bash
# shipped.sh — a "shipped while you slept" section from your own merged PRs.
# Needs the `gh` CLI authenticated; stages nothing if you shipped nothing.
set -euo pipefail
source "$(dirname "$0")/_lib.sh" "${1:-}"

command -v gh >/dev/null || { unavailable "Shipped" "gh CLI not installed"; exit 0; }

tmp="$(mktemp -t shipped.XXXXXX).md"
{
  echo "# Shipped while you slept"
  echo
  gh search prs --author=@me --merged --merged-at=">$(date -v-1d +%F 2>/dev/null || date -d yesterday +%F)" \
    --json title,url,repository \
    | jq -r '.[] | "- [\(.title)](\(.url)) — \(.repository.name)"'
} > "$tmp"

# Only stage if there's a body beyond the heading — honest empty beats a fake.
if [ "$(grep -c '^- ' "$tmp")" -gt 0 ]; then
  stage_markdown "Shipped" "$tmp" && ok "Shipped"
else
  unavailable "Shipped" "nothing merged since yesterday"
fi
rm -f "$tmp"
```

**`collectors/read.sh`** — the simplest collector: stage one URL as a read for
the current edition date. Edit the URL, or wrap it to read a list from a file:

```bash
#!/usr/bin/env bash
# read.sh — stage a single URL as a full read for the current edition. The bring-your-own
# pattern: the engine fetches and extracts exactly like `print`.
set -euo pipefail
source "$(dirname "$0")/_lib.sh" "${1:-}"

URL="https://example.com/replace-with-something-worth-reading"
case "$URL" in
  *replace-with-*) unavailable "Read" "no URL set — edit collectors/read.sh"; exit 0 ;;
esac
stage_url "Today's read" "$URL" && ok "Read"
```

**`collectors/local-drop.sh`** — stage markdown/text/URL files from a folder
the reader already owns. This is the gentle path for Obsidian exports, synced
folders, agent-produced files, and manual source dumps:

```bash
#!/usr/bin/env bash
# local-drop.sh — stage files from inbox/ for the current edition.
set -euo pipefail
source "$(dirname "$0")/_lib.sh" "${1:-}"

DROP_DIR="${MORNING_PAPER_DROP_DIR:-$(dirname "$0")/../inbox}"
mkdir -p "$DROP_DIR"
shopt -s nullglob

count=0
for file in "$DROP_DIR"/*; do
  [ -f "$file" ] || continue
  base="$(basename "$file")"
  case "$base" in .* ) continue ;; esac
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
  esac
done

if [ "$count" -gt 0 ]; then
  ok "Local drop ($count)"
else
  unavailable "Local drop" "put .md, .txt, or .url files in $DROP_DIR"
fi
```

**`editions/.gitignore`** — one line: `*.pdf`. The `edition` skill writes
`editions/<date>/operator-answers.md` and archives the composed md + html here.

**`examples/edition-skeleton.md`** — copy the engine's edition skeleton as the
starting point for hand-composed editions: it shows the masthead, strip, and
section furniture. Point the reader at the engine's
[examples/brief.example.md](https://github.com/dmthepm/morning-paper/blob/main/examples/brief.example.md)
and write a copy
into the newsroom they can edit. It is fully synthetic (Port Anselm) — replace
the place and the prose with their own.

After personalizing the scaffold, make the first commit.

## 6. Recurrence (host-native first)

Default: each morning they say "paper" or invoke the `edition` skill and watch
the editor work.

If they want it to run automatically, lean into the primitive of the host they
already use. Do not install a local scheduler unless they explicitly ask for
that fallback.

Offer the matching prompt:

```text
Set up a Claude Code routine with /schedule that builds my Morning Paper each
weekday morning. Use this private newsroom, run the Morning Paper edition
workflow, render the PDF, open or deliver it according to DELIVERY.md, and tell
me only if the run failed or needs my attention.
```

```text
Set up a Codex automation that builds my Morning Paper each weekday morning.
Use this private newsroom, run the Morning Paper edition workflow, render the
PDF, and report the PDF path plus anything that needs my attention.
```

```text
Set up a ChatGPT scheduled task for my Morning Paper. Each weekday morning,
use my newsroom sources and preferences to produce one calm edition, render the
PDF, and summarize only the actions or blockers I need to review.
```

Only if they specifically want a machine-local fallback, run
`morning-paper routine install|status|uninstall` from inside the newsroom repo
and explain that it uses the machine scheduler (launchd/systemd/cron), so local
runs depend on that machine being available.

## 7. The return path (how their ink comes back)

Tell the reader where their reactions land: the `edition` skill reads the most
recent `editions/<date>/operator-answers.md` and honors it. So if they reply
"more like this", "kill section X", or "print `<url>` tomorrow", the editor
chooses the smallest durable route and records stable notes with
`morning-paper edition apply-feedback . --date <edition-date> --route
editorial|voice|visuals|sources|prior|delivery|checks|the-read|front-page|reading|taste --note "<reader note>" --why
"<why it should change tomorrow>"`. That writes the target file, `TASTELOG.md`,
and the edition's `feedback-plan.md`. Then it stages anything they asked to
read. The newsroom is a loop: what they write today shapes tomorrow's paper.

## 8. First edition, now

Run the edition skill once end-to-end while they watch. It will collect
(`collectors/run_all.sh`), read the specs you scaffolded, compose, render, and
`review`. Print it if the printer is ready. Hand them the paper. Done is a
physical object.
