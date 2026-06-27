# Feedback Loop

Morning Paper gets better when the reader marks up the paper and the agent
turns stable feedback into the smallest durable newsroom change. The goal is
not to preserve every reaction. The goal is to improve tomorrow without
overfitting today.

The command is intentionally explicit:

```bash
morning-paper edition apply-feedback . \
  --date YYYY-MM-DD \
  --route editorial \
  --note "More source-backed synthesis, fewer status bullets." \
  --why "reader wants The Read to make a judgment"
```

It updates the routed file, appends `TASTELOG.md`, and writes an Applied
Feedback line into that edition's `feedback-plan.md`.

Think of this as the taste desk. A reader's chat replies, dictated notes,
desk-sheet marks, and delivery complaints should not stay trapped in the host
conversation. The agent decides whether the note is durable, chooses the
smallest route, and uses the CLI so tomorrow's editor can see exactly what
changed. A future dedicated feedback skill should wrap this workflow, but the
current edition skill already has the contract.

## Route To The Smallest File

| Reader feedback | Route |
|---|---|
| "More judgment, less roundup." | `editorial` |
| "The voice is too fluffy." | `voice` |
| "That wide chart worked." | `visuals` |
| "Add my GitHub/Main Branch pulse." | `sources` |
| "Email me the article view too." | `delivery` |
| "Dampen pure viral stories." | `interests` |
| "Give Shopify one page when it has real source records." | `budgets` |
| "Stop warning about this Field Notes headline style." | `checks` |
| "The Read should connect work and personal sources." | `the-read` |
| "The front page needs one verb headline." | `front-page` |
| "Do not reprint reads I already got." | `reading` |
| "We tried this and rejected it." | `taste` |

## Do Not Overfit

Do not turn every irritated sentence into a permanent law. Save a durable rule
when at least one is true:

- the reader explicitly asks to remember it;
- the same note appears more than once;
- the issue clearly violates an existing newsroom contract;
- tomorrow's paper will be materially better if the rule exists.

Otherwise, summarize it in the delivery handoff or leave it in
`operator-answers.md` for tomorrow's agent to notice.

## Examples

### Visual Preference

Reader:

> The chart was useful, but it should have taken the whole measure.

Command:

```bash
morning-paper edition apply-feedback . --date 2026-06-22 \
  --route visuals \
  --note "Useful charts should be full-measure or placed in a deliberate visual grid." \
  --why "reader disliked narrow floating visuals"
```

Durable result: `VISUALS.md` gets a feedback note, `TASTELOG.md` records the
decision, and `feedback-plan.md` proves the path changed.

### Source Preference

Reader:

> Tomorrow, include the GitHub/Main Branch pulse before random reads.

Command:

```bash
morning-paper edition apply-feedback . --date 2026-06-22 \
  --route sources \
  --note "Work-system pulses outrank casual reading when they contain open asks or blocked work." \
  --why "reader wants the paper to catch operational fires first"
```

Durable result: `SOURCES.md` changes. The agent may also create or adjust a
collector, but the taste rule lives in the source desk.

### Rejected Taste

Reader:

> Maybe make it forty pages every day.

Command:

```bash
morning-paper edition apply-feedback . --date 2026-06-22 \
  --route taste \
  --decision rejected \
  --note "Make the default edition forty pages." \
  --why "conflicts with finite attention and page-budget discipline"
```

Durable result: only `TASTELOG.md` and `feedback-plan.md` change. The rejected
idea remains visible without bloating tomorrow's editorial rules.

### YAML Preferences

For `interests`, `budgets`, and `checks`, feedback is appended as YAML comments
first. The file stays parseable. Promote the comment into real YAML only when
the exact setting is clear.
