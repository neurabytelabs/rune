---
name: rune-prompt-amplification
description: "Restructures a flat prompt into a structured 8-layer instruction, and ships the blind A/B harness that measures whether doing so actually helps. In our own pilot the amplified prompts lost — see docs/BENCHMARKS.md before relying on it."
version: "2.1.0"
author: "Mustafa Saraç <mustafa@neurabytelabs.com>"
license: MIT
homepage: https://github.com/neurabytelabs/rune
platforms: [macos, linux]
---

# RUNE — Prompt Amplification & Measurement

> **This file is canonical.** Every distribution surface (clawhub, Hermes, Claude Code,
> OpenClaw, or any future runtime) derives from this file. Do not restate the measured
> result anywhere else — link to the CLAIM block below or to `docs/BENCHMARKS.md`.
> See `RELEASE.md` for the publish checklist.

## What this is

RUNE has two halves, and only one of them is proven:

1. **The amplifier** — an 8-layer restructuring of a flat prompt (role, context, intent,
   governance, reasoning mode, capabilities, QA, output format), plus a Spinoza-style
   validation pass. This is a **hypothesis**, not an established best practice.
2. **The harness** — a reproducible blind pairwise A/B benchmark that measures whether any
   given intervention actually improves output. This is the part that holds up.

<!-- CLAIM:BEGIN -->
**Measured result.** In blind pairwise A/B, RUNE's 8-layer amplification was preferred in
**19.6%** of decided pairs (95% CI [10.2, 29.3]; 46 of 50 pairs decided; exact binomial sign
test p = 4.056e-05). All five rubric criteria showed negative deltas; control won in all five
domains and on both generation models. The result was produced on the Gemini model family
with a single sample per cell, and part of the prompt set was authored by RUNE's developer.
Method, limitations and reproduction: `docs/BENCHMARKS.md`.
<!-- CLAIM:END -->

**What was measured.** The intervention under test is the 8-layer restructuring, including
the extra LLM round-trip it requires. The *prompt repetition* technique documented in
`RUNE.md` §5 is a separate method, is not implemented in this code path, and was not
measured.

## When to use it

Use the **harness** whenever you need to know if a prompt, system message, model or policy
change actually helped:

- comparing two versions of a system prompt or agent instruction file
- deciding whether a prompt edit is safe to ship
- producing a defensible number instead of "it felt better"

Use the **amplifier** as an explicit, opt-in experiment — not as a default. Given the result
above, do not wire it into an agent's default path without measuring it in your own context
first. It may still help on model families or task types the pilot did not cover; that is an
open question, not a claim.

Do not use either for: greetings, one-line factual answers, single-step file operations, or
any case where the user asked for a raw, unmodified response.

## The 8 layers

| Layer | Name | Purpose |
|---|---|---|
| L0 | System Core | Role, stance, behavioral rules |
| L1 | Context Identity | Domain, history, audience, constraints |
| L2 | Intent Scope | Actual goal, success criteria, output format |
| L3 | Governance | Safety, ethics, permissions, non-goals |
| L4 | Cognitive Engine | Reasoning strategy: decomposition, RCA, ToT, critique |
| L5 | Capabilities Domain | Tools, files, integrations, agents, retrieval |
| L6 | QA | Validation and correctness checks |
| L7 | Output Meta | Language, tone, structure, length, delivery format |

Not every prompt needs all eight. Simple requests use L1+L2+L7.

## Spinoza validation

Before final output, check four qualities:

- **Conatus** — does this increase the user's ability to act?
- **Ratio** — is it coherent, grounded, internally consistent?
- **Laetitia** — is it clarifying rather than muddying?
- **Natura** — is it natural and usable, not overengineered?

If one fails, revise before answering. Note that this validator's correlation with actual
output quality has not itself been measured.

## Operating mode (any runtime)

1. **Detect complexity.** Simple request → answer directly. Complex → consider RUNE.
2. **Keep it internal.** Do not dump the layer list unless the user asks to see it.
3. **Ask only load-bearing questions.** If missing context changes the result, ask one short
   question. Otherwise proceed with stated assumptions.
4. **Do not replace execution.** For build/run/verify work, RUNE shapes the plan; it does not
   substitute for running tools and reading real output.
5. **Prefer the raw prompt when unsure.** The measured result says the scaffold can cost more
   than it adds.

When visible RUNE is requested:

```markdown
## RUNE Pass
- L0 Role:
- L1 Context:
- L2 Intent:
- L3 Governance:
- L4 Cognitive Mode:
- L5 Capabilities:
- L6 QA:
- L7 Output:
```

## Install

RUNE is runtime-neutral. It needs the repository and an OpenAI-compatible endpoint; nothing
below is specific to any single agent platform.

```bash
git clone https://github.com/neurabytelabs/rune ~/Documents/GitHub/rune
cd ~/Documents/GitHub/rune
python3 -m pip install -e .
```

Configure a provider — never commit real keys:

```bash
mkdir -p ~/.rune
cat > ~/.rune/config.toml <<'EOF'
[llm]
api_url = "https://your-openai-compatible-endpoint/v1/chat/completions"
api_key = "your-api-key"
default_model = "your-model"
timeout = 300
EOF
```

Or export `RUNE_API_URL` / `RUNE_API_KEY`.

### Loading into an agent runtime

Any runtime that reads a `SKILL.md` can load this file directly. Copy it to whatever path
that runtime expects:

| Runtime | Path |
|---|---|
| Claude Code | `~/.claude/skills/rune-prompt-amplification/SKILL.md` |
| Hermes | `~/.hermes/skills/prompt-engineering/rune-prompt-amplification/SKILL.md` |
| OpenClaw | `~/.openclaw/skills/rune-prompt-amplification/SKILL.md` |
| Other / new | wherever that runtime discovers skills |

Freshly copied skills usually require a new session to be picked up. No runtime is the
primary target; this list is examples, not a hierarchy.

## CLI

```bash
wand inscribe "prompt"      # show the amplified prompt only
wand cast "prompt"          # amplify, then execute
wand duel "prompt"          # A/B: raw vs amplified
wand grimoire               # browse 42 templates
wand bench generate         # run the blind A/B harness
wand bench report           # regenerate docs/BENCHMARKS.md from run artifacts
```

`wand bench` is the part worth reaching for. The judge is pluggable — any system honoring
`benchmark/JUDGE_PROTOCOL.md` (an LLM endpoint, a multi-agent workflow, or a human panel)
produces verdicts the harness can analyze.

## Governance

- Never expose or copy secrets from `~/.rune/config.toml`, `~/.secrets`, `.env`, or any
  runtime's config files.
- Ask before destructive actions, external sends, commits/pushes, or service lifecycle
  changes unless the current instruction clearly grants that scope.
- Treat RUNE as a clarity tool under test, not decoration. If the layers make an answer
  worse, drop them — the benchmark says that happens more often than not.
- **Do not restate the measured result outside the CLAIM block.** Link to it.
