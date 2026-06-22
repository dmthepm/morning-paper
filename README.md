<div align="center">
  <img src="docs/assets/hero.jpg" alt="A printed Morning Paper edition" width="720">

  <h1>Morning Paper</h1>

  <p><strong>Own your algorithm. Your personal newsroom.</strong></p>

  <p>An agent composes your newspaper. Code prints it.<br>
  Your preferences live in files you own.</p>
</div>

---

## Set up with AI (recommended)

Open your strongest model — Claude Opus 4.8 with the 1M context works great — and paste this:

```text
I want a Morning Paper: an open-source personal newspaper my agent composes
and prints, with preferences I own as files
(https://github.com/dmthepm/morning-paper). First read the entire README,
then explore the repo enough to understand the architecture (agent composes,
code renders; a private newsroom repo holds my preference files; the honesty
doctrine binds). Then interview me briefly about my sources, page budget, and
printer. Then: install the engine, run `morning-paper doctor` and fix
anything it flags, run `morning-paper demo` so I see the product, scaffold my
private newsroom repo (the operating constitution, section specs led by The
Read, the reads-ledger, voice, and example collectors — real files, not empty
folders), build my first real edition, and teach me the daily loop and the
return path (replies I leave in `editions/<date>/operator-answers.md` shape
tomorrow's paper). Get me to a printed (or PDF) first edition, then stop and
show me what you set up.
```

Prefer to drive it yourself? Everything below is the manual path.

## Try it

Typeset the bundled sample edition — no config, no network, no keys:

```bash
uvx --from "morning-paper[pretty]" morning-paper demo
```

> macOS first: `brew install pango gdk-pixbuf` (WeasyPrint needs Pango).

Or keep it on your PATH instead of a one-off run:

```bash
uv tool install "morning-paper[pretty]"
morning-paper demo
```

The demo renders a fully synthetic edition through the `broadsheet` style pack
and tells you exactly where the PDF landed. Print it. That is the product.

## The Claude Code plugin

The plugin turns Claude Code into your newsroom staff:

```text
/plugin marketplace add dmthepm/morning-paper
/plugin install morning-paper@morning-paper
```

Then say "set up my morning paper". The `setup` skill installs the engine,
interviews you about sources and shape, and creates your private newsroom
repo — your preferences as files you own, not a feed you rent. The `edition`
skill composes and prints each day's paper.

## For Agents (read this first if you are one)

Your human wants a daily printed paper. You can give them one. If they pasted
the ["Set up with AI" prompt](#set-up-with-ai-recommended) above, follow it —
it is the full onboarding arc (read, explore, interview, install, demo,
newsroom repo, first edition, daily loop). Otherwise:

1. Install: `uv tool install "morning-paper[pretty]"` (or
   `pipx install "morning-paper[pretty]"`; use `pip` only inside a venv —
   PEP 668 blocks it on brew/system Pythons), then `morning-paper doctor`.
   `morning-paper demo` proves the print path end to end.
2. If this repo is installed as a Claude Code plugin, run the `setup` skill —
   it interviews the reader, creates their private newsroom repo (preferences
   as files: the owned algorithm), and wires a morning routine. The `edition`
   skill composes and renders each day's paper.
3. The CLI speaks JSON. The verbs you need:
   - `morning-paper stage <url>` -> stages it for tomorrow and answers with a
     page estimate ("that adds ~5 pages")
   - `morning-paper inbox` -> poll the contributor inbox: mail from the
     configured masthead (an allowlist of trusted senders) becomes staged
     pages and the sender gets a confirmation; `--dry-run` previews
     ([docs/inbox.md](docs/inbox.md))
   - `morning-paper queue` -> what's staged vs the page budget
   - `morning-paper estimate <file.md>` -> page count, nothing written
   - `morning-paper render <file.md> --style <s> --palette <p>` -> the PDF
   - `morning-paper review <edition>` -> editorial QC on a finished edition
     (long/label headlines, lopsided or dead sections, duplicate stories,
     stale leads) as JSON warnings — never fails the build; `--strict` makes a
     flag exit nonzero for CI. Run it after `render`, before delivery
   - `morning-paper routine install|status|uninstall` -> schedule the daily
     edition as a headless `claude -p` run (the scheduling ladder, below);
     `status` answers "did the paper build this morning?" in JSON
   - `morning-paper doctor --json` -> machine-readable install status,
     including whether the routine is installed
     (add `--strict` to get a nonzero exit when the typewriter renderer
     is unavailable)
4. Page estimates need the pretty print stack (`[pretty]` + WeasyPrint):
   `estimate` fails without it, and `stage` falls back to a rough
   words-per-page heuristic instead of a real layout pass. Run
   `morning-paper doctor` first if the numbers matter.
5. Article extraction is local by default (`trafilatura`): the URL is fetched
   from this machine and never sent to a third party. If local extraction
   recovers too little, the `jina` fallback re-fetches through `r.jina.ai`
   (anonymous tier: shared rate limits, 40-second timeout) and the result
   carries an honest note saying the URL left the machine. Failures raise
   clean errors instead of staging garbage.
6. Composition contract, class vocabulary, and chart directives: [docs/composing.md](docs/composing.md).
7. Honesty rule: a section with no data says "not configured" — never fabricate.

## What it does

- Builds a daily paper from Hacker News and RSS feeds — JSON, Markdown, HTML,
  and print-ready PDF artifacts on disk
- Prints any article on demand with `morning-paper print <url>`
- Stages material for tomorrow's edition against a page budget
  (`stage`, `queue`, `estimate`)
- Typesets any markdown file through four print style packs with
  `morning-paper render` — with a shared taste layer (keep-together heads,
  orphan/widow control, atomic furniture) free in every pack
- Reviews a finished edition for editorial problems CSS can't fix with
  `morning-paper review` — warnings, never a hard fail
- Renders charts from plain-text directives (`mp-bars`, `mp-spark`,
  `mp-stats`) as inline SVG — stdlib only, no plotting library
- Works without an LLM key

No database. No Docker. No SaaS requirement. It is not a second-brain
platform, a wiki, or a closed recommendation engine — it is a CLI that
prints a newspaper.

## Your daily paper

```bash
uv tool install "morning-paper[pretty]"
morning-paper init      # starter config
morning-paper doctor    # must say: typewriter ready
morning-paper build     # today's edition
```

`pipx install "morning-paper[pretty]"` works the same way. Prefer either
over bare `pip`: on Macs and Linux boxes whose default Python is Homebrew's
or the distro's, `pip install` outside a virtual environment fails with
`externally-managed-environment` (PEP 668), and inside an existing
environment it can silently keep an older version unless you pass
`--upgrade`. If you manage your own venv,
`pip install "morning-paper[pretty]"` is still fine.

Artifacts land under:

```text
~/.local/share/morning-paper/<date>/
```

The plain `morning-paper` install (no `[pretty]`) falls back to a simpler
renderer — it works, but it is not the output you should judge the product by.

## The morning routine (the scheduling ladder)

The paper is best when it is simply *there*. Four tiers, in order of effort —
climb only as far as you want.

**Tier 0 — say "paper" each morning.** The default. Open Claude Code and ask
for your paper (the `edition` skill). Zero setup, full control, and you watch
the editor work. Most readers should start — and many should stay — here.

**Tier 1 — `morning-paper routine install`.** One command schedules a daily
headless run: `claude -p` invokes the edition skill through your existing
Claude subscription — no extra API key, no daemon. Default time is 05:00
(`--time HH:MM` to change it, `--command CMD` to replace the job entirely).
On macOS this is a launchd LaunchAgent using `StartCalendarInterval`, chosen
deliberately because launchd *coalesces* runs missed during sleep into one
run on the next wake: a closed laptop at 5am means the paper builds the
moment you open it, instead of being skipped. On Linux it is a systemd user
timer with `Persistent=true` (same catch-up behavior), falling back to a
crontab line where systemd is absent — with the honest note that cron has no
coalescing. `morning-paper routine status` reports schedule, last run, and
next fire as JSON; `routine uninstall` removes it cleanly; the job logs to
`~/.local/share/morning-paper/routine.log`.

**Tier 2 — always-on.** A Mac mini, desktop, or home server that never
sleeps runs the same routine at exactly 05:00 every day — pair it with a
printer and the paper is on the tray before you wake. A Mac that should wake
itself instead of staying on: `sudo pmset repeat wakeorpoweron MTWRFSU
04:55:00` wakes it five minutes before the routine fires.

**Tier 3 — the cloud-compose split.** Compose in the cloud, print at home: a
scheduled cloud agent (or CI job) runs the edition skill on its own clock and
commits the composed markdown to your newsroom repo; any local machine that
comes online runs `morning-paper render` and the print command. The judgment
can run anywhere — the paper still lands on your desk.

## Sources

| Source | Auth needed? | Status |
| --- | --- | --- |
| Hacker News | No | Included |
| RSS feeds | No | Included |
| Article URLs | No | Included via `print` / `stage` |

Everything else — a subreddit digest, your GitHub activity, an X radar, a
weekly research roundup — is a *collector*: a small script you run before
composing that stages markdown into the queue. See
[docs/collectors.md](docs/collectors.md) for the contract.

## Four styles, two palettes

`morning-paper styles` lists them all — a family of four, each named for the
print genre it is and the job it does. Every style pairs with either palette:
`mono` (laser printers; weight carries emphasis) or `color` (inkjet: warm
ink, working red, data blue).

| Style | What it is |
| --- | --- |
| `broadsheet` | The newspaper you read: unified serif system, restrained color — the default recommendation |
| `brief` | The operator brief you work through with a pen: dense Courier, queue rows, link cards, no forced page breaks |
| `field-card` | The reference card you tape next to the phone: boxed sans one-pager — scripts, checklists, do/don't splits |
| `zine` | The pocket guide you hand to someone: half-letter photocopier paste-up — marker strips, halftone bands, checkbox steps |

```bash
morning-paper render brief.md --style broadsheet --palette color
```

The 0.4.x names (`editorial`, `flow`, `ops-card`, `magazine`, `typewriter`)
still work for one release as deprecated aliases of their successors.

## Rendering

Two renderers, one honest contract:

- `typewriter` — the product look. Requires the pretty stack
  (`[pretty]` + WeasyPrint). Courier Prime ships vendored (SIL OFL), so
  typesetting is offline-deterministic.
- `portable` — explicit pure-Python fallback. Lower fidelity; use it only
  when you intentionally want the simpler output.

If `typewriter` cannot render, Morning Paper fails clearly instead of
silently generating a lower-quality PDF. `morning-paper doctor` says plainly
which path you are on, and on macOS prints the exact Pango fix when that is
the problem.

Article extraction defaults to `local`: the page is fetched directly from
your machine and parsed with [trafilatura](https://trafilatura.readthedocs.io/)
— no API key, no rate limits, and **the URLs you read never leave your
computer**. The `jina` extractor (the anonymous `r.jina.ai` reader tier)
remains available, and runs automatically as a fallback when local
extraction recovers too little content — with the privacy trade stated
plainly: jina sends each URL to a third-party service, so the fallback is
flagged with an honest note in the `print`/`stage` output rather than
happening silently. Set `article_extractor: jina` in config if you prefer
the remote reader. Some domains (YouTube, GitHub, Instagram, LinkedIn, HN
comment pages) do not extract meaningfully and are rejected with a clear
error. A validation gate rejects shell pages and too-short extractions
instead of printing garbage. Extraction is a replaceable backend; the
renderer, validation, and image pipeline are designed to survive extractor
upgrades.

## The honesty doctrine

A section with no data prints "not configured" — never invented headlines,
never filler. Page estimates come from a real layout pass when the print
stack is installed. Malformed chart data degrades to an honest placeholder.
If the good renderer can't run, the build fails loudly rather than quietly
shipping something worse. The paper never lies to you about what it knows.

## Docs

- [docs/composing.md](docs/composing.md) — the composition contract for agents:
  document structure, class vocabulary, chart directives
- [docs/collectors.md](docs/collectors.md) — bring your own sources: how to add
  anything beyond the built-in HN + RSS by staging into the queue
- [docs/inbox.md](docs/inbox.md) — the contributor inbox: let people you
  trust email articles into tomorrow's paper (Gmail/iCloud app-password setup)
- [ROADMAP.md](ROADMAP.md) — what shipped, what's next
- [CHANGELOG.md](CHANGELOG.md) — release history
- [CONTRIBUTING.md](CONTRIBUTING.md) — how to help

## Platform notes

- **macOS / Linux** — recommended. Install `morning-paper[pretty]`; you may
  need system libraries for WeasyPrint (`brew install pango gdk-pixbuf` on
  macOS, pango/cairo packages on Linux).
- **Windows** — the CLI works; the `portable` fallback is the more reliable
  path today, and `typewriter` via WeasyPrint is best-effort.

Run `morning-paper doctor` after install: `renderer: typewriter ready` means
you are on the real print path.

## Development

```bash
git clone https://github.com/dmthepm/morning-paper.git
cd morning-paper
pip install -e ".[dev]"
python -m pytest tests/
morning-paper doctor
```

## Community

- Main Branch: [skool.com/main](https://skool.com/main)
- Issues: [github.com/dmthepm/morning-paper/issues](https://github.com/dmthepm/morning-paper/issues)
- Post your paper: [Discussions](https://github.com/dmthepm/morning-paper/discussions)

## License

MIT
