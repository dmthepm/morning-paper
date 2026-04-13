# Visual Sourcing

## Goal

Give the nightly agent a disciplined way to find one print-worthy visual without turning the brief into a slideshow.

## Selection Hierarchy

The agent should look for a visual only after the banner story and full reads are already chosen.

Priority order:

1. chart or diagram from the banner story
2. screenshot that proves a product/release/bug story
3. article hero image that materially improves recall
4. tweet image / infographic with real informational density

Avoid:

- generic stock imagery
- aesthetic-only images
- low-resolution memes
- screenshots full of tiny UI text that will die on paper

## Tooling Strategy

### Best sources for the nightly agent

- Browser tools / screenshots:
  - useful when the story is a web page, chart, dashboard, or product release page
  - agent can screenshot the exact region it wants, then pass the local file to `bw_image.py`

- Article/tweet image URLs:
  - useful when the source has a clean hero image or infographic
  - agent can pass the remote URL directly to `bw_image.py`

- Apify / web scraping:
  - useful for extracting image URLs from a known story page or social post at scale
  - should be used when browser capture is too manual or the page has multiple candidate images

- Readwise / saved links:
  - useful for story selection context
  - not the primary image extraction surface by itself

## Recommended Runtime Flow

1. Choose the banner story.
2. Ask: does this story deserve a visual on paper?
3. If yes, fetch one candidate by the selection hierarchy.
4. Run `scripts/bw_image.py` on the source URL or local screenshot.
5. Keep both original and processed source references in metadata.
6. Insert only after the brief passes structural QA.
7. Require page screenshot review of the page containing the visual.

## Why Local File Support Matters

The best visual may come from a screenshot the agent captures itself, not a clean remote image URL.

That is why `bw_image.py` should support:

- `https://...`
- `/absolute/path/to/image.png`
- `file:///absolute/path/to/image.png`

## Future Automation Shape

The eventual repo-owned pipeline should add a small selector step that writes metadata like:

```json
{
  "story": "Anthropic's OpenClaw Ban: What's Actually Happening",
  "source_type": "browser_screenshot",
  "source_ref": "file:///Users/thoth/tmp/anthropic-openclaw-shot.png",
  "processed_ref": "/Users/thoth/.hermes/brief-assets/2026-04-05-visual.png",
  "caption": "Anthropic notice and live community reaction",
  "alt": "Screenshot of Anthropic policy notice and related discussion"
}
```

That metadata should then feed the assembly step instead of forcing the template to rediscover the visual.

## Product Rule

The nightly agent should surface at most one primary visual by default.

If more than one image seems important, the default answer should still be one:

- the single highest-signal image
- the rest stay in references or research, not in the printed brief
