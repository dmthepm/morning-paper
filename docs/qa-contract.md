# QA Contract

## Principle

No PDF should be treated as print-ready unless it passes both structural QA and visual QA.

## Required QA Steps

1. verify required inputs exist
2. verify output path is canonical for this run
3. run structural linter
4. run screenshot generation
5. inspect every page
6. fail if artifact freshness is wrong
7. fail if required sections are missing

## Structural QA

Must detect:

- markdown inside HTML blocks
- broken YAML/PDF options
- missing footer/header protections
- HN flexbox regressions
- missing required sections
- obvious page-budget failure

## Visual QA

Must inspect:

- page 1
- every middle page
- last page
- any page containing HN or other section transitions

## Blocking Conditions

- render-breaking layout errors
- stale or missing source inputs
- wrong output target
- missing or malformed required sections
- visible header/footer corruption

## Non-Blocking Warnings

- density/page-budget drift
- sparse sections
- styling nits that do not break the artifact
