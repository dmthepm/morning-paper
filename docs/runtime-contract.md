# Runtime Contract

## Runtime Split

### Repo owns

- templates
- render scripts
- QA scripts
- visual prep scripts
- fixture tests
- golden outputs
- operating docs

### Hermes/Thoth owns

- cron scheduling
- runtime paths
- Telegram delivery
- local secrets
- local context synthesis
- private artifact storage

## Pass 4 Contract

Pass 4 should:

1. resolve `TODAY`
2. verify inputs
3. call versioned assembly code
4. write canonical markdown
5. run QA
6. render review PDF
7. archive screenshots and report
8. deliver review notification

If a visual is used, Pass 4 should also:

9. persist visual source metadata
10. process the selected image for monochrome print
11. ensure the page containing the visual is included in screenshot review

## 07:00 Digest Contract

The digest should:

- read the canonical reviewed artifact path
- send through Hermes-native routing only
- never use legacy OpenClaw sender paths

## Deployment Rule

Cron should call versioned repo scripts with absolute paths. Cron prompts should describe orchestration, not re-encode the product logic.
