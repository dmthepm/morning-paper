# Visual Contract

## Status

The Morning Brief has a recovered but not yet fully wired visual lane.

Recovered from imported live Thoth assets:

- `scripts/bw_image.py` already existed in the live Morning Brief print skill
- it was explicitly labeled `Visual of the Day — B&W Printer Optimization`
- it was intended to turn article, tweet, chart, diagram, and screenshot imagery into print-safe monochrome assets

## What The Visual Lane Is For

The visual is not decorative filler.

It should do one of these jobs:

- make the banner story more concrete
- carry a chart, screenshot, or diagram that is easier to understand visually than in prose
- act as a single high-signal artifact from the overnight run

If it does not improve comprehension on paper, it should be omitted.

## Print Rules

- optimize for monochrome laser printing, not phone display
- preserve line clarity and chart legibility
- avoid large dark fills that waste toner
- prefer one strong visual over a collage
- prefer screenshots, charts, diagrams, and article images with clear edges

## Current Processing Rules

`scripts/bw_image.py` currently applies:

1. resize down to a print-safe width
2. convert to grayscale
3. contrast boost
4. brightness correction
5. sharpen pass
6. posterize when the image appears diagram-like / low-gray-variance

Default tuning:

- contrast: `1.4`
- brightness: `1.1`
- threshold: `128`
- max width: `680px`

## Input Contract

The visual prep tool should accept either:

- a remote image URL
- a local file path
- a `file://` path from a browser screenshot or prior download

That matters because the nightly agent may source visuals from:

- scraped article hero images
- tweet photos
- screenshots taken by browser tools
- locally saved charts/diagrams

## Output Contract

For each selected visual, the pipeline should preserve:

- original source URL or local source path
- processed local asset path
- caption
- alt text
- story association

The markdown embed form is currently:

```md
![Alt text](file:///path/to/visual.png)

*Caption*
```

## Cutover Guidance

Do not insert a permanent `Visual of the Day` section into the canonical template until:

- the nightly sourcing logic exists
- captions/attribution rules are explicit
- visual QA includes placement/page-fit checks
- a golden output with a visual section is approved

Until then, the visual lane should be treated as an explicit optional module, not an always-on requirement.
