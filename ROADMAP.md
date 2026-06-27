# Roadmap

## Shipped (`v0.1.x`)

- `morning-paper init`, `build`, `print <url>`, `doctor`
- early built-in web/feed sources
- `typewriter` renderer with `WeasyPrint`
- `portable` PDF fallback with `fpdf2`
- Article extraction with inline image handling; local extraction later became
  the default path
- X/Twitter metadata via FxTwitter
- Content validation gate so bad extractions do not print garbage
- Pluggable extractor architecture
- Visual regression testing for the article page
- PyPI publishing with trusted GitHub publishing

## Shipped (`v0.2.0`)

- `morning-paper render <file.md>` — one-off local markdown typesetting through style packs
- Style packs (`typewriter`, `flow`, `ops-card`) + palettes (`mono`, `color`)
- Chart directives (`mp-bars`, `mp-spark`, `mp-stats`) → inline SVG, stdlib-only
- Page footers via CSS paged-media margin boxes
- `morning-paper styles` listing command

## Shipped (`v0.3.x`)

- `morning-paper stage <url|file>` (alias: `add`) — queue material for
  tomorrow's paper with a page estimate
- `morning-paper queue` (alias: `status`) — staged items vs the page budget
- `morning-paper estimate <file.md>` — page-budget estimation
- `editorial` style pack and the Claude Code plugin (`setup` + `edition` skills)
- vendored Courier Prime (OFL) for offline-deterministic rendering
- `doctor --json` and `doctor --strict` for machine-readable install checks

## Shipped (`v0.4.2`)

- `local` article extractor as the default — URLs stay on your machine; remote
  readers are explicit choices, not the default path
- "Set up with AI" onboarding prompt at the top of the README

## Shipped (`v0.4.4`)

- the contributor inbox ("the masthead") — `morning-paper inbox` polls a
  mailbox over IMAP; trusted senders' mail becomes staged pages with a
  FROM <NAME> kicker and a warm confirmation reply (docs/inbox.md)

## Shipped (`v0.5.0`)

- the style family: four packs named for the job — `broadsheet` (was
  `editorial`, absorbing `magazine`), `brief` (was `flow`, absorbing
  `typewriter`'s link-card grid), `field-card` (was `ops-card`), and the
  rebuilt `zine` (the photocopier field zine: paste-up cover plate, halftone
  bands, rubber stamp, command bars). Old names are deprecated aliases for one
  release; the build front page is broadsheet-native for every style
- `v0.5.1` — `morning-paper routine` (install/status/uninstall): the daily
  edition as a headless `claude -p` run (launchd / systemd / cron ladder)
- `v0.5.2` — the scheduled routine pins its working directory to the newsroom

## Shipped (`v0.6.x`)

- `v0.6.0` — the layout taste layer (keep-together craft, free in every pack)
  and `morning-paper review`: editorial QC on a finished edition (eight
  text-only checks, warnings never hard fails; reads `preferences/checks.yaml`)
- `v0.6.1` — `review` headline-length checks scoped to true headlines, not
  deck/department titles

## Shipped (`v0.7.0`)

- full-text RSS: feeds that ship the whole article in `content:encoded` print
  as real reads (a new `body` field on each item), summary feeds stay summaries
- the setup scaffold: `setup` now WRITES the newsroom's working contracts (an
  operating `CLAUDE.md`, section specs led by The Read, an empty reads-ledger,
  voice + algorithm-prior + checks templates, a `stage`-based collector
  contract with worked examples, and an editions dir) instead of empty folders
- removed the thin shadowing skill stub; doc tightening + version re-baseline

## Shipped (`v0.8.x private newsroom`)

- WeasyPrint is treated as the production renderer, not an implementation
  detail: `doctor --strict` runs a real layout self-test and `doctor --json`
  reports Python, WeasyPrint, tinycss2, cssselect2, pydyf, cffi, Pillow,
  fontTools, the enforced WeasyPrint support range, and detectable native Pango
  status
- the `[pretty]` extra is bounded to the current supported WeasyPrint major
  line and a clean virtualenv install has proved WeasyPrint 69.0 can run the
  doctor self-test and demo render
- pretty-renderer CI exercises the WeasyPrint path on Python 3.13 for macOS
  and Ubuntu
- `morning-paper newsroom init <path>` scaffolds a private newsroom repo with
  `setup-state.json`, `SETUP.md`, `CLAUDE.md`, specs, preferences, collectors,
  memory files, an inbox drop folder, and edition templates; reruns skip
  user-edited files unless `--force` is explicit
- `morning-paper newsroom state <path> --set key=value` updates setup state
  and refreshes `SETUP.md` so install proof, source choices, printer choices,
  plugin state, pending questions, and next action stay durable
- private newsroom taste primitives now ship with the scaffold:
  `EDITORIAL.md`, `VISUALS.md`, `SOURCES.md`, `DELIVERY.md`, and
  `TASTELOG.md`; they are newsroom-native files for editorial judgment,
  visuals, sources, delivery, and accepted/rejected taste changes
- `morning-paper sources list|check` inventories built-in and RSS sources and
  labels checked RSS feeds as full-text or summary-only; with `--newsroom
  <path>` it also inventories local collector scripts and checks shell syntax
- `morning-paper queue list|show|remove` makes the staged edition queue
  inspectable and editable by agents
- `morning-paper edition prepare <newsroom>` writes the compaction-safe edition
  workspace: source inventory, collector report, queue snapshot, draft,
  render/review placeholders, and operator answers
- `scripts/setup_scaffold_smoke.py` runs the setup path from a temporary home:
  default config, `doctor --strict --json`, demo PDF, newsroom scaffold,
  setup-state refresh, local-drop collector, edition prepare, render, review,
  and feedback artifact without touching real user config or routines
- `scripts/new_user_smoke.py` runs deterministic local simulations for the
  creator/news reader, business owner/Main Branch, technical agent,
  nontechnical RSS/newsletter, and local-folder/source-dump personas; each now
  reaches a rendered PDF, complete edition artifact set, and clean review
- `scripts/host_plugin_smoke.py` installs the current worktree through real
  Claude Code and Codex plugin hosts using temporary homes, proving clean host
  discovery and the shared setup/edition/writing skills without mutating the
  reader's installed plugin state
- `scripts/release_candidate_check.py` builds release artifacts from a clean
  source copy, rejects stale build debris, and can install both wheel and sdist
  with `[pretty]` to prove `doctor --strict` and `demo` before PyPI publish
- a live Codex agent, running from temporary `CODEX_HOME`, `HOME`, and
  `XDG_CONFIG_HOME` with the local plugin installed, used the
  setup/edition/writing skill path to create a fresh newsroom, stage a
  synthetic local source through the scaffolded local-drop collector, render a
  one-page PDF, accept reviewer feedback, and finish with clean review; no
  real config or routine was touched
- a live authenticated Claude Code session ran the demo, produced a real
  two-page PDF, and opened it on screen; full interactive setup against the
  real home directory remains intentionally unforced because it can install a
  routine and write user config
- chart directives now have print-layout guardrails: built-in `mp-bars`,
  `mp-spark`, and `mp-stats` align with surrounding sections, cap density,
  clip labels, and add honest overflow notes instead of colliding or floating
  as narrow inserts
- `v0.8.1` — deterministic typography: MP Serif (TeX Gyre Pagella) and MP Sans
  (Arimo) are vendored and wired through `@font-face`, charts lead with
  vendored Courier Prime, and WeasyPrint gets the correct OTF/TTF `format()`
  hint so the same paper uses the same glyphs on macOS and Linux
- `v0.8.2` candidate — reader-stack-first source framing, durable
  `feedback-plan.md` artifacts, visual integration guardrails, explicit
  opt-in remote extractor fallback, and stricter release-candidate artifact
  checks
- skill architecture is banked in `docs/newsroom-skill-suite.md`: keep the
  public setup/edition/writing path stable while roles mature inside the
  edition workflow
- collector date semantics are explicit: edition collectors target the
  edition date, ad hoc `stage` remains "read this later" and defaults to
  tomorrow
- setup and edition skills now require durable state files so a compacted or
  fresh agent can resume from disk

## Next

- publish `v0.8.2`, then run the published package/plugin live-agent pass from
  the installed artifact
- first-edition acceptance test proving a real agent uses the prepared
  workspace, overwrites pending render/review artifacts, and ends by asking
  for natural-language feedback
- independent final-editor workflow: a separate context window reviews the
  rendered paper against the reader's editorial, visual, source, and delivery
  contracts before delivery, then routes stable feedback into the smallest
  durable newsroom file
- visual geometry checks for arbitrary agent-created raw HTML/SVG/images
- style x palette snapshot expansion in CI
- palette-aware article image pipeline (color images on the color palette)
- source plugins for YouTube transcripts and X/Twitter thread workflows
- social source-record contract: discovery collectors find candidate
  URLs/IDs, then finalists become complete records with full text, metrics,
  media, thread/reply context, and long-native-post routes before print
- social beat budgeting: let agents allocate pages across subtopics such as
  frontier agents, coding workflows, commerce, creative tools, and reader-owned
  projects, then use rendered proof pages to tune density
- source media triage: CLI/review help for deciding whether social images,
  screenshots, demos, and long native posts become small figures, mini-reads,
  full reads, source-health notes, or cuts
- optional LLM scoring via OpenRouter / Anthropic / OpenAI
- named sections and better front-page composition
- a genericized public return-path skill (modeled on the newsroom triage flow)

## Future

- a hosted contributor door (Cloudflare Worker email address) for instant
  confirmations — today's path is the IMAP poll
- preference learning
- private perspective analysis over reader-owned exports: YouTube, podcasts,
  music, social downloads, email/newsletters, work tools, local notes, and
  other private datasets can reveal attention patterns, blind spots, recurring
  storylines, and cross-domain connections for the paper to consider
- shared community curation and page exchange
- agent slot competition against a page budget
- coverage / breadth analysis for major stories
- image-of-the-day or full-page visual mode
- E Ink / device delivery surfaces
- additional explicit extractor backends (readability exports, browser session
  capture, paid/private readers, or paywalled-page sessions)
- sensitive export handling: source analysis over health, genetic, financial,
  legal, or identity-adjacent data must be explicit opt-in, local-first,
  minimally copied, and careful about unsupported inferences or essentialist
  claims
