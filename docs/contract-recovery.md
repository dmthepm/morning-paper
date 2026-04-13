# Contract Recovery

This file captures the engineering truths recovered from Apr 4-5 Hermes sessions and Thoth runtime state.

## Recovered Product Truths

### The brief is a physical ritual artifact

The brief exists for:

- coffee-time pickup
- reading in bed with kids
- highlighter markup
- replacing first-thing Slack/email/GitHub checking

Engineering implication:

- print correctness is a product requirement
- review-before-print is mandatory

### The brief is a system-awareness surface

It must eventually cover:

- external signals
- business changes
- system health
- money/cost signals
- dropped comms / operator attention items

Engineering implication:

- the Morning Brief is a product, not just a PDF template

### The layout contract is no longer exploratory

Recovered from approved PDFs and Apr 4 sessions:

- `Courier Prime` body
- white page
- black text
- subtle gray cards are allowed and correct
- section headers are transparent
- page-1 title/date/rule are body content, not Chrome header content
- `headerTemplate: "<span></span>"` is required
- footer must use flex layout with precise inset margins
- HN uses CSS columns, not flexbox
- markdown headers must not appear inside raw HTML blocks

Engineering implication:

- these are testable invariants
- they belong in template code and QA, not just prompts

### Visual QA is intended to be systematic

Apr 4 converged on:

- linter
- screenshot pass
- per-page inspection
- toner-waste prevention

Engineering implication:

- QA must inspect every page, not only page 1 or one HN page

## Recovered Failure Modes

### Runtime drift

- skills changed without cron behavior being updated
- cron prompts drifted from the skill contract
- emergency recovery artifacts bypassed the approved styling lane

### Content pipeline drift

- Pass 2 and Pass 3 outputs did not always match spec
- date naming drift existed between research date and delivery date
- a brief could pass render QA while still being built from partial or stale inputs

### Review/print conflation

- the system could generate and print too close together
- a review PDF was needed, but the system did not cleanly distinguish review from print

## Primary Evidence Sources

Use these first:

- Hermes session DB: `/Users/thoth/.hermes/state.db`
- Hermes CLI: `hermes sessions ...`
- live cron definitions: `/Users/thoth/.hermes/cron/jobs.json`

Use raw JSON transcripts only as fallback:

- `/Users/thoth/.hermes/sessions/*.json`
