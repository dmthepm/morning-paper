# Edition Run Contract

Morning Paper needs an unattended completion promise. A routine, automation, or
scheduled agent should keep working until it has produced a real edition or hit
a defined blocker. It should not stop mid-run to ask the reader ordinary
editorial questions.

Cadence is a reader preference, not part of the contract. One newsroom may run
every weekday, another weekly, monthly, quarterly, or only on demand. Once a run
starts, the same edition-run rules apply.

The paper is the product. The Assignment Board, collectors, ledgers, review
files, and source health notes exist so agents can coordinate and recover
without turning the reader's morning into a dashboard session.

## Default Contract

For the public project, a run is **complete** when all of these are true:

1. Sources were checked or explicitly reported as not configured.
2. Collectors ran, skipped honestly, or wrote source-health notes.
3. Candidates were assigned, cut, held, or recorded as absent.
4. The edition was composed from the newsroom's files and current Assignment
   Board.
5. The desk sheet was included when `preferences/desk-sheet.yaml` enables it.
6. `morning-paper edition estimate` ran against the current draft.
7. The PDF rendered successfully.
8. `morning-paper review` ran and was either clean, notes-only, or explicitly
   accepted with rationale.
9. `morning-paper edition visual-qa` ran.
10. `morning-paper edition final-editor` ran and returned `clean` or `notes`,
    or the agent recorded a clear rationale for shipping despite a review flag.
11. Memory and ledgers were updated enough to prevent obvious repeats in the
    next edition.
12. `morning-paper edition status` wrote a current production record.
13. The edition folder contains the durable artifacts another agent needs to
    resume: source inventory, collector report, Assignment Board, draft,
    estimate, render result, review, visual QA, final-editor files, production record,
    feedback plan, and operator answers.
14. Delivery was attempted only where configured, and the final handoff names
    the PDF path plus anything that needs attention.

The default status words are:

- **complete** - the paper rendered, checks ran, ledgers updated, and configured
  delivery succeeded or was not configured.
- **complete_with_notes** - the paper rendered and can be read, but one or more
  sources, collectors, review nudges, visual checks, or delivery attempts need
  attention.
- **blocked** - no readable edition can be produced without reader action or a
  repaired environment.

## Graceful Source Failure

Source failure is usually not a blocker. A reader should still get a useful
paper when one source is empty, stale, rate-limited, unauthenticated, or
incomplete.

The agent should:

- print "not configured" for absent sources;
- write a source-health note for failed or skipped collectors;
- route partial social/search results to `Needs Source Record` or `Source Health`,
  not to print-ready cards;
- cut or hold candidates that cannot be sourced honestly;
- include a short final note when an important desk was thin, unavailable, or
  needs configuration.

The paper should not pad around a missing source. It should ship the best
edition the newsroom can support today.

## Hard Blockers

Stop only for blockers that make a readable, honest edition impossible:

- no valid newsroom path or missing core contracts;
- unable to write `editions/<date>/` artifacts;
- renderer or PDF stack broken after `doctor`/render repair attempts;
- no PDF produced or produced PDF is unreadable or blank;
- privacy or sensitivity conflict where the source cannot be safely printed;
- required credentials are missing for every configured source and there is no
  staged/local material to make an honest paper;
- final-editor reports stale or missing artifacts and rerender/review cannot
  repair them.

When blocked, write the blocker into the edition folder if possible and tell
the reader the smallest repair step. Do not pretend delivery happened.

## Per-Newsroom Overrides

Different readers need different definitions of done. Public defaults live
here; private overrides live in the reader's newsroom, usually in
`DELIVERY.md`, `preferences/desk-sheet.yaml`, `preferences/checks.yaml`,
`SOURCES.md`, and source-specific ledgers.

Examples:

- one reader requires local Preview to open the PDF;
- another requires Telegram delivery;
- another wants GitHub artifact links committed;
- another disables the desk sheet and accepts PDF path only;
- another treats a specific work source as mandatory and blocks if it fails.

Overrides should be explicit. If a preference is not written down, the default
contract applies.

## Assignment Board Role

The Assignment Board is the agent coordination layer for this contract. It is
not the primary reader interface. It should help agents and interested operators
see:

- which desks produced material;
- which candidates are collected, need source records, ready, or source-health
  only;
- when editor/producer handoffs record it, which candidates were selected, cut,
  held, or printed;
- estimated pages and page budget remaining;
- trust, sensitivity, freshness, extraction status, and repeat/staleness notes;
- why a candidate moved lanes or was cut.

The reader's normal feedback loop remains the paper and desk sheet:

```text
read paper -> mark desk sheet or reply in chat -> agent applies feedback ->
the next edition is better
```

## No External Action By Default

Core Morning Paper does not take action outside the paper. It may brief,
render, review, archive, deliver configured artifacts, and update newsroom
memory. It should not publish posts, send replies, draft outbound emails, edit
Shopify, or run work loops unless a future explicit extension says so.

Future action-oriented desks can build on the same newsroom model, but they are
not part of the default edition run contract.
