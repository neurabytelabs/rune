# 📝 Changelog

## v2.1.0 — Visible Lineage (2026-05)
- **GEPA-viz bridge:** `wand lineage --export-gepa run.json` exports RUNE prompt ancestry into a GEPA-viz-compatible candidate tree.
- **Observable prompt evolution:** Exported nodes include parent links, Spinoza score, grade, model, strategy, refinement round, and feedback.
- **README release story:** Added the Lineage section showing how to cast, export, and optionally inspect the run with `gepa-viz serve`.
- **No new runtime dependency:** RUNE remains lightweight; GEPA-viz is an optional viewer.
- **Local demo:** `demo/gepa-lineage/` ships a zero-install HTML demo plus sample `run.json` for the release walkthrough.

## v2.0.0 — Deus Sive Natura (2026-03)
- **Unified versioning:** Single 2.0.0 across all components
- **pyproject.toml:** pip-installable package (`rune-wand`)
- **Modular CLI:** wand.py refactored from 1318-line monolith → rune/cli/ package (helpers, cast, commands, main, swarm_cmd)
- **SpinozaValidator:** New local heuristic validator (rune/core/validator.py) — no LLM needed
- **Unified providers:** rune/providers/ with OpenAI-compatible base (works with Gemini, xAI, OpenAI, Anthropic, local)
- **Swarm integration:** `wand swarm "prompt"` — multi-agent evolution now accessible from main CLI
- **Swarm modularized:** swarm.py → rune/swarm/ (agents, tournament, orchestrator)
- **Test suite:** 23 tests covering validator, router, CLI helpers (pytest)
- **Meta-prompt updated:** RUNE Architect v2.0

## v4.4 — Hyper-Structured (2026-02)
- **Polyglot rendering:** Auto-detects input language, responds in kind
- **Domain presets:** CODING / WRITING / ANALYSIS modes with tailored defaults
- **Observability:** Active layer tracking in output metadata
- **Complexity scaling:** L1–L5 auto-skips unnecessary layers
- Refined XML schema for better cross-model compatibility

## v4.3 — Consolidated (2026-01)
- **14→8 layer consolidation:** Merged redundant layers for token efficiency
- ~35% token reduction with equivalent quality
- 10 new production-ready prompts added to library
- `mp.py` CLI tool for prompt enhancement
- `cross_model_test.py` for multi-model benchmarking
- Self-QA layer with retry logic
- Improved governance layer (merged ethics + constraints)

## v4.2 — Self-Improving (2025)
- 14 layers — maximum granularity
- Self-improvement: AI reflects on and refines its own outputs
- Memory layer: Context persistence across turns
- Token budget awareness
- Expanded constraint system

## v4.1 — Multimodal (2025)
- 12 layers
- Multimodal support (text, code, diagrams)
- Cost awareness: Token estimation and budget warnings
- Enhanced cognitive engine with decision trees
- Improved cross-model compatibility

## v4.0 — Agentic (2025)
- 11 layers
- Agentic architecture: AI can plan, execute, and iterate
- Tool integration layer
- Dynamic complexity adjustment
- First version with XML structure

## v3.0 — Foundation (2024)
- 7 components (flat structure)
- Static template — no dynamic behavior
- Single-language (Turkish)
- Manual prompt construction
- The beginning of Master Prompt
