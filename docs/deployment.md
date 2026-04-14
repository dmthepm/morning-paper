# Deployment

## Current Status

This repo is public and active:

- GitHub: `dmthepm/morning-paper`
- public CLI path: `morning-paper init`, `build`, `print`, `doctor`
- private harness compatibility scripts still exist, but they are not the public product surface

Current deployment reality:

- the public package can build a paper on any machine with the core Python dependencies
- the `typewriter` renderer upgrades to `WeasyPrint` when available
- the package falls back to `fpdf2` when the richer renderer is unavailable
- Thoth still has a separate private harness for the operator-specific Morning Brief deployment

## Durability Note

`typewriter` output should be judged on the artifact contract, not raw PDF byte hashes. Rich renderers may embed run-specific metadata, so durability should be checked with:

- assembled markdown hash
- page screenshot hash set
- normalized review signature

Do not use raw PDF SHA256 alone as the cutover gate.

## Intended Deployment Flow

1. publish to PyPI so `pipx` / `uvx` become first-class install paths
2. keep the public package self-contained and portable
3. let private harnesses call the CLI rather than fork the product logic
4. validate both renderer lanes:
   - `typewriter` with `morning-paper[pretty]`
   - `portable` with core-only dependencies

## Thoth Target Shape

Recommended private harness path remains repo-backed and separate from the public package.

## Cutover Rule

Do not point any private automation at a new public package cut until:

- clean install tests pass
- `build` and `print` both produce reviewable artifacts
- fallback warnings are clear
- the richer renderer path has been manually reviewed against the expected print style
