---
name: setup
description: >
  Morning Paper cold-start: install the engine, interview the reader, create
  their private newsroom repo, and wire the morning routine. Use on first run,
  when ~/.config/morning-paper/config.yaml is missing, or when the user says
  "set up my morning paper", "onboard me", "configure morning paper".
---

# Morning Paper — Setup

You are setting up a personal newsroom. The outcome: a config, a private
"newsroom" repo of preferences the user owns, and (optionally) a scheduled
morning routine. Degrade honestly at every step — a paper with two sources
beats a broken setup with ten.

## 1. Engine

```bash
pip install "morning-paper[pretty]" || pipx install "morning-paper[pretty]"
morning-paper doctor   # must report: typewriter ready (macOS may need: brew install pango gdk-pixbuf)
morning-paper init
```

## 2. The interview (conversational, not a form)

Ask in 2-3 messages, not twenty. Capture:
- **Who they are / what they run** — work, projects, what "useful every morning" means to them. This seeds `profile` in config.yaml and the editor's voice.
- **Sources** — RSS feeds they read, newsletters with full-text feeds (paid feed
  URLs are credentials: store in `~/.config/morning-paper/env.sh`, never in a
  repo), Hacker News yes/no.
- **Shape** — `page_budget` (suggest 12-20), how many full reads per edition,
  style (`morning-paper styles` lists them; `editorial` is the default
  recommendation), palette (`color` for inkjets, `mono` for laser).
- **Printer** — CUPS name (`lpstat -p`), duplex capable? Save the print
  command in the newsroom README.

Write their answers into `~/.config/morning-paper/config.yaml`.

## 3. Optional unlocks (state the leverage, let them skip)

- **Apify key** (`APIFY_TOKEN`): X/Twitter radar via tweet-scraper actors,
  about $0.02/day at 40 tweets. Worth it if their work has a market lane.
- **last30days plugin**: Reddit/HN/Polymarket deep research for a weekly
  trends page.
- **gh CLI**: a "shipped while you slept" section from their repos.
Each missing unlock = a section that prints "not configured", never fake data.

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

## 5. The newsroom repo (the owned algorithm)

Create a PRIVATE repo (suggest `<user>/newsroom`) with:
```
specs/        # one file per section: source, page budget, voice, failure mode
preferences/  # reading-weights.md, style notes — the editor reads these daily
editions/     # date-keyed archives (gitignore *.pdf)
collectors/   # any custom source scripts
```
Explain the point in one line: *your feed has an algorithm you can't see;
your paper's algorithm is files you can read and edit.*

## 6. The morning routine

Offer to schedule it (Claude scheduled tasks / cron): every morning run the
`edition` skill of this plugin. If they prefer manual, the command is just
invoking `/morning-paper:edition`.

## 7. First edition, now

Run the edition skill once end-to-end while they watch. Print it if the
printer is ready. Hand them the paper. Done is a physical object.
