# 🏗 Architecture

## The 8-Layer Model

Master Prompt v4.3+ uses an 8-layer XML structure. Each layer has a specific responsibility, creating a separation of concerns for prompt engineering.

```
┌─────────────────────────────────────┐
│  L0: System Core                    │  ← Runtime config, polyglot, presets
├─────────────────────────────────────┤
│  L1: Context & Identity             │  ← Who the AI is, expertise level
├─────────────────────────────────────┤
│  L2: Intent & Scope                 │  ← What to do, boundaries
├─────────────────────────────────────┤
│  L3: Governance                     │  ← Rules, ethics, constraints
├─────────────────────────────────────┤
│  L4: Cognitive Engine               │  ← How to think (CoT, reasoning)
├─────────────────────────────────────┤
│  L5: Capabilities & Domain          │  ← Tools, APIs, domain knowledge
├─────────────────────────────────────┤
│  L6: Quality Assurance              │  ← Validation, self-check, retry
├─────────────────────────────────────┤
│  L7: Output & Meta                  │  ← Format, language, observability
└─────────────────────────────────────┘
```

## Layer Breakdown

### L0: System Core
The bootstrap layer. Sets rendering mode (polyglot), domain preset (CODING/WRITING/ANALYSIS), and complexity level (L1–L5). This layer determines which other layers are activated.

### L1: Context & Identity
Defines the AI's persona, expertise, and background. A shader debugging prompt sets a "senior WebGL/GLSL engineer" identity; an API design prompt sets a "senior API architect."

### L2: Intent & Scope
The mission statement. What the AI must accomplish, what deliverables are expected, and what's out of scope. Prevents scope creep.

### L3: Governance
Guardrails and constraints. "Never modify working code outside the bug scope." "Always preserve backward compatibility." This layer keeps the AI safe and focused.

### L4: Cognitive Engine
Reasoning instructions. Chain-of-thought depth, analysis approach, decision frameworks. Tells the AI *how* to think, not just what to think about.

### L5: Capabilities & Domain
Domain-specific knowledge, tool access, API references. The "knowledge base" layer.

### L6: Quality Assurance
Self-validation rules. The AI checks its own output against criteria before responding. Includes retry logic for failed validations.

### L7: Output & Meta
Format specification (markdown, JSON, code), language selection, and observability metadata (which layers were active).

## Design Decisions

### Why XML?
XML provides clear nesting, named sections, and is well-understood by all major LLMs. JSON was considered but lacks readability for long-form content. Markdown headers lack the semantic nesting depth needed.

**Trade-off:** Claude models tend to ignore XML structure more than Gemini models. This is a known issue documented in [BENCHMARKS.md](BENCHMARKS.md).

### Why 8 Layers? (v4.2→v4.3 Consolidation)

v4.2 had 14 layers. Testing revealed:
- **Redundancy:** Several layers overlapped (e.g., separate "Ethics" and "Constraints" layers)
- **Token waste:** ~40% more tokens for marginal quality improvement
- **Cognitive overload:** Models sometimes lost track of deeply nested structures

The v4.3 consolidation merged related layers:
- Ethics + Constraints → **Governance** (L3)
- Tools + Knowledge → **Capabilities & Domain** (L5)
- Format + Language + Observability → **Output & Meta** (L7)

**Result:** ~35% fewer tokens, equivalent or better output quality.

### Complexity Scaling
Not every prompt needs 8 layers. The complexity system (L1–L5) auto-skips unnecessary layers:

| Complexity | Active Layers | Use Case |
|:----------:|:-------------:|----------|
| L1 | L1, L2, L7 | Simple Q&A |
| L2 | L1, L2, L3, L7 | Constrained tasks |
| L3 | L0–L3, L6, L7 | Standard tasks |
| L4 | L0–L7 | Complex tasks |
| L5 | L0–L7 + extended | Expert tasks |

### Token Efficiency

| Version | Layers | Avg. Tokens (template) | Quality Score |
|---------|:------:|:----------------------:|:-------------:|
| v4.0 | 11 | ~2,800 | 7.2/10 |
| v4.1 | 12 | ~3,200 | 7.8/10 |
| v4.2 | 14 | ~4,100 | 8.1/10 |
| v4.3 | 8 | ~2,600 | 8.3/10 |
| v4.4 | 8 | ~2,700 | 8.6/10 |

The v4.3 consolidation achieved **better quality with fewer tokens** — the ideal outcome.
