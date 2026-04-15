# Morning Paper

Use this skill when the user wants to:

- build a daily paper
- print one or more articles right now
- stage material for later paper work
- verify the install or renderer state

## Commands

Build today's paper:

```bash
morning-paper build
```

Build for a specific date:

```bash
morning-paper build --date 2026-04-15
```

Print one or more articles immediately:

```bash
morning-paper print https://example.com/article
morning-paper print https://example.com/a https://example.com/b
```

Check whether the richer print renderer is ready:

```bash
morning-paper doctor
```

## Notes

- `typewriter` is the main product renderer.
- If the pretty stack is missing, `doctor` will tell you and `typewriter` should fail clearly instead of silently degrading.
- The article extractor is pluggable. The default is currently `jina`.
- Prefer using the CLI rather than reimplementing pipeline logic inside the agent runtime.
