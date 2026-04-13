# Candidates — 2026-04-05

## Story Candidates

1. **Anthropic's OpenClaw Ban: What's Actually Happening** — Hacker News (Algolia) + Readwise — score: 95 [BANNER]
   Why: Devon runs sovereign AI on OpenClaw. Anthropic sent notices blocking Claude Code subscriptions from using OpenClaw harness. One-time credit offered until April 17. This affects every Main Branch member running Claude Code with OpenClaw.
   Link: https://news.ycombinator.com/item?id=47633396
   HN Signal: 411+ pts, top of HN. Security guides circulating. NIST CVE published for OpenClaw (CVE-2026-33579).
   Seed quality: HIGH — Devon needs to know: (a) is self-hosted affected? (b) Franceschi workaround still viable? (c) what's Anthropic's actual enforcement mechanism?
   Already covered: YES (2026-04-03 candidates) — but has new developments: security CVE published, community workarounds emerging

2. **"Components of a Coding Agent" — Sebastian Raschka's Architecture Deep Dive** — Hacker News — score: 88
   Why: Raschka (researcher, not blogger) dissects what actually makes coding agents work — planning, tool use, memory, reflection. Directly relevant to how Devon should architect Hermès agent skills.
   Link: https://magazine.sebastianraschka.com/p/components-of-a-coding-agent
   HN Signal: 204 pts, rising. 67 comments.
   Seed quality: HIGH — technical depth that matches Devon's "how does this actually work" questions. Could inform Hermès architecture decisions.
   Already covered: NO — new article, just published

3. **Qwen 3.6 Plus: Opus-Level Coding, Free, Local** — Readwise (Alex Finn, others) — score: 85
   Why: Claims to beat Claude Opus 4.6 for coding, state-of-the-art tool calling, runs on Mac Mini with 32GB RAM. If true, this is the open-source model Devon has been waiting for — free, local, sovereign.
   Link: https://x.com/AlexFinn/status/2038737372024553891
   Signal: Multiple developers sharing as "this changes everything" — but needs verification against benchmarks.
   Seed quality: MEDIUM — unverified claims. Need to find actual benchmark data vs Opus/Sonnet. If real, high-ticket agency clients would care.
   Already covered: NO — new model release

4. **Open Source AI CRM on OpenClaw Hits 1.4k Stars** — Readwise (Mark Rachapoom) — score: 82
   Why: "Crest" (rebranded from Ironclaw) shows real commercial products being built ON OpenClaw. 1.4k GitHub stars in weeks. Confirms OpenClaw is becoming a platform, not just a tool.
   Link: https://x.com/markrachapoom/status/2039093718511448395
   Signal: Devon's content strategy around "open source beats closed" gets validated by community building ON his recommended stack.
   Seed quality: HIGH — shows ecosystem health, validates Main Branch thesis
   Already covered: YES (2026-04-03 candidates, item 4) — but 1.4k stars is new growth

5. **AutoResearch: Self-Evaluating AI Agent Loop** — Readwise — score: 79
   Why: Agent that evaluates its own results and iterates until better. The "autoresearch loop" Karpathy popularized extended to autonomous research. Directly mirrors the Hermès "self-improve" goal.
   Link: https://x.com/DavidOndrej1/status/2039293377043849502
   Signal: The knowledge compounding pattern (query → wiki → better wiki → better query) is becoming a recognized architectural pattern.
   Seed quality: MEDIUM — needs more specifics on implementation
   Already covered: NO — new pattern emerging

6. **kepano (Obsidian Founder) on Karpathy's Vault Architecture** — Readwise — score: 77
   Why: Obsidian founder weighs in on the "clean vault vs messy vault for agents" question. High signal for Devon's Obsidian vs Git primitives decision.
   Link: https://x.com/kepano/status/2039805659525644595
   Signal: Clean/dirty vault separation is the emerging best practice. Devon is actively deciding between Obsidian and Git primitives.
   Seed quality: HIGH — directly affects Devon's architectural decision
   Already covered: NO — new commentary from Obsidian founder

7. **Manus AI Always-On Agent Mode Launches** — Readwise (TestingCatalog) — score: 76
   Why: Meta entering the agent space with skills, subagents, memory, dedicated compute, identity, messengers. Directly competitive with OpenClaw.
   Link: https://x.com/georgesttock/status/2038614675216105472
   Signal: Every major player is now building "always-on agent with memory." OpenClaw's first-mover advantage is being tested.
   Seed quality: MEDIUM — competitive landscape, good for Devon's market awareness
   Already covered: YES (2026-04-03 candidates, item 5) — Meta entering is new context

## Already Covered Yesterday (skip unless MAJOR new development)

- Anthropic/OpenClaw ban — BANNER story, workarounds documented
- Karpathy's KB loop — pattern established, new commentary from kepano adds signal
- /dev/agents (former Android team) — no new signal
- Agent-Browser tool — still relevant but no new developments
- Hermès multi-agent setup (Benny Berman) — no new signal

## New Blind Spots Caught Today

1. **Sebastian Raschka coding agent architecture** — Devon would not have seen this (research paper level). Fits his "how does this actually work" style.
2. **kepano (Obsidian founder) commentary** — Obsidian vs Git primitives decision is active, this is the founder's take.
3. **AutoResearch pattern** — knowledge compounding loop applied to autonomous research is new.

## Source Audit

| Source | Cost | Status | Quality |
|--------|------|--------|---------|
| Readwise highlights | FREE | WORKING | Excellent — Devon signal, bookmarks |
| HN Algolia API | FREE | BLOCKED (security scan) | API works but pipe-to-python blocked |
| HN via browser | FREE | Worked | Got front page data |
| Web search (Firecrawl) | $0 | FAILED | Payment required — no credits |
| YouTube transcripts | FREE | Working | Most recent: Pierre Poilievre, black plastics, 3-layer AI framework |

## Cost This Pass: ~$0

All signals from free sources. No paid APIs used.

## Pass 1 Status: COMPLETE

Output written: `~/projects/noontide/staging/candidates-2026-04-05.md`

## Pass 2 Should Prioritize (in order)

1. **Anthropic/OpenClaw ban** (BANNER) — What's the actual enforcement mechanism? Is self-hosted affected? Franceschi workaround status?
2. **Components of a Coding Agent** — Raschka's technical breakdown. Does it inform Hermès architecture?
3. **Qwen benchmark verification** — Are the claims real? What about the 1M token context claim?
4. **kepano vault separation** — Obsidian founder's take on clean vs messy vaults. Decision impact for Devon.

## Devon Filter Summary

Stories that scored 70+ (included above): 7
Stories filtered out (< 70): ~10
Most filtered: generic AI hype, crypto, consumer tech, content without technical depth

Devon's current priorities from context:
- Hermès architecture decisions (Raschka article helps)
- OpenClaw ecosystem health (CRM, Manus)
- Sovereign AI validation (Qwen, local models)
- Security (CVE, OpenClaw hardening)
- Obsidian vs Git primitives decision (kepano signal)