<div align="center">

# 🧬 RUNE

**Every prompt is a spell.**

*Where Spinoza Meets Silicon*

A structured 8-layer prompt engineering framework with philosophical validation for high-fidelity LLM outputs.

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-1.0-blue.svg)](docs/CHANGELOG.md)
[![Models](https://img.shields.io/badge/models-Grok_4.1_|_Gemini_3_Pro_|_Claude_Opus_|_GPT--4o-purple.svg)](#-supported-models)

[Quick Start](#-quick-start) · [Architecture](#-architecture) · [Supported Models](#-supported-models) · [Prompt Library](#-prompt-library) · [Benchmarks](#-benchmarks) · [Contributing](CONTRIBUTING.md)

</div>

---

## What is RUNE?

Most prompts are flat text — unstructured, ambiguous, and inconsistent across models. **RUNE** is a layered prompt engineering framework that tells LLMs *exactly* how to think, respond, and self-correct — then validates outputs through a Spinoza-inspired philosophical lens.

RUNE wraps your intent in 8 semantic layers — from identity and constraints to cognitive reasoning and output formatting. Every output passes through the **Spinoza Validator**: coherence, necessity, and ethical alignment checks inspired by Baruch Spinoza's *Ethics*.

The result: outputs that are structured, reproducible, and dramatically higher quality across Grok 4.1, Gemini 3 Pro, Claude Opus, GPT-4o, and others.

> 📖 **Turkish documentation available:** See [LLM Master Prompt Rehberi](LLM%20Master%20Prompt%20Rehberi%20Oluşturma.md)

## ⚡ Quick Start

```bash
# Clone
git clone https://github.com/neurabytelabs/rune.git
cd rune

# Install
pip install -r requirements.txt

# Cast your first spell
wand cast "Write a REST API for a todo app"

# Just see the enhanced prompt (don't execute)
wand inscribe "Optimize this React component"

# A/B compare: raw vs enhanced output
wand duel "Debug this shader"

# Use a specific model
wand cast --model grok-4-1 "Design a database schema"

# Run Spinoza validation on any text
wand validate "Your LLM output here"

# Browse the grimoire (prompt library)
wand grimoire
```

### Configuration

Create `~/.rune/config.toml` to configure your API keys and default model:

```toml
[default]
model = "grok-4-1"

[providers.xai]
api_key = "your-xai-api-key"
endpoint = "https://api.x.ai/v1"

[providers.google]
api_key = "your-google-ai-key"

[providers.anthropic]
api_key = "your-anthropic-key"

[providers.openai]
api_key = "your-openai-key"
```

## 🤖 Supported Models

| Provider | Model | Strengths |
|----------|-------|-----------|
| xAI | **Grok 4.1** | Fast reasoning, 2M context, cost-effective |
| Google | **Gemini 3 Pro** | Template compliance, structured output |
| Anthropic | **Claude Opus** | Exceptional prose, deep reasoning |
| OpenAI | **GPT-4o** | Balanced quality, multimodal |

## 🏗 Architecture

```
┌─────────────────────────────────────────────┐
│                RUNE v1.0                    │
│        "Every prompt is a spell"            │
├─────────────────────────────────────────────┤
│                                             │
│  L0  ░░░░░░░░░░  System Core               │
│      Polyglot rendering, domain presets     │
│                                             │
│  L1  ██░░░░░░░░  Context & Identity         │
│      Role, expertise, persona               │
│                                             │
│  L2  ████░░░░░░  Intent & Scope             │
│      Mission, deliverables, boundaries      │
│                                             │
│  L3  ██████░░░░  Governance                 │
│      Constraints, ethics, guardrails        │
│                                             │
│  L4  ████████░░  Cognitive Engine           │
│      Chain-of-thought, reasoning depth      │
│                                             │
│  L5  ██████████  Capabilities & Domain      │
│      Tools, APIs, domain knowledge          │
│                                             │
│  L6  ██████████  Quality Assurance          │
│      Self-check, validation, retry logic    │
│                                             │
│  L7  ██████████  Output & Meta              │
│      Format, language, observability        │
│                                             │
├─────────────────────────────────────────────┤
│  🔮 SPINOZA VALIDATOR                       │
│  Coherence · Necessity · Ethical Alignment  │
└─────────────────────────────────────────────┘
```

> Each layer is an XML block. Lower layers override higher ones. Unused layers can be omitted for simpler tasks (Complexity L1–L2 auto-skips).

## ✨ Features

| | Feature | Description |
|---|---|---|
| 🎯 | **8-Layer Structure** | Semantic separation of concerns for prompts |
| 🔮 | **Spinoza Validator** | Philosophical validation: coherence, necessity, ethics |
| 🔄 | **Polyglot Rendering** | Auto-detects language, responds accordingly |
| 🏷️ | **Domain Presets** | CODING / WRITING / ANALYSIS modes |
| 📊 | **Complexity Scaling** | L1–L5 complexity auto-adjusts layer depth |
| 🧠 | **Cognitive Engine** | Built-in chain-of-thought and reasoning |
| ✅ | **Self-QA** | Output validation and retry logic |
| 🪄 | **Wand CLI** | `wand cast` enhances any prompt instantly |
| 🧪 | **Cross-Model Testing** | Benchmark prompts across multiple models |
| 📚 | **Grimoire** | Prompt library with production-ready runes |
| 👁️ | **Observability** | Active layer tracking in responses |

## 📚 Prompt Library (Grimoire)

Ready-to-use runes built on the RUNE template:

| # | Rune | Use Case |
|---|------|----------|
| 01 | [🔮 Shader Debug & Fix](prompts/01_shader_debug.md) | WebGL/GLSL shader diagnostics |
| 02 | [🎨 UI/UX Polish](prompts/02_ui_polish.md) | Interface refinement & enhancement |
| 03 | [⚡ Performance Audit](prompts/03_performance_audit.md) | Optimization & bottleneck analysis |
| 04 | [🗺️ Feature Roadmap](prompts/04_feature_roadmap.md) | Architecture & planning |
| 05 | [🔍 Code Review](prompts/05_code_review.md) | Deep code analysis |
| 06 | [🐛 Bug RCA](prompts/06_bug_rca.md) | Root cause analysis |
| 07 | [🔧 Refactoring](prompts/07_refactoring.md) | Safe code restructuring |
| 08 | [🧪 Test Generation](prompts/08_test_generation.md) | Test scenario creation |
| 09 | [🌐 API Design](prompts/09_api_design.md) | REST/GraphQL API documentation |
| 10 | [📚 Documentation](prompts/10_documentation.md) | Technical writing |

## 📊 Benchmarks

Cross-model testing with `wand test` across identical prompts:

| Model | Template Compliance | Output Quality | Structured Output |
|-------|:------------------:|:--------------:|:-----------------:|
| Gemini Flash 🥇 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| GPT-4o 🥈 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| Gemini Pro 🥉 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| Claude Sonnet | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| Claude Opus | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |

> **Key finding:** Gemini Flash leads in template compliance. Claude models produce excellent prose but tend to ignore XML structure. See [full benchmarks →](docs/BENCHMARKS.md)

## 🛠 CLI Usage (Wand)

```bash
wand cast "Explain microservices architecture"      # Enhance + run
wand inscribe "Build a login form"                  # Show enhanced prompt only
wand duel "Write unit tests for auth module"        # A/B compare
wand cast --model gemini-3-pro "Optimize SQL query" # Choose model
wand grimoire                                       # Browse prompt library
wand validate "Check this output"                   # Spinoza validation
wand forge                                          # Create new rune template
wand stats                                          # Usage statistics
```

All outputs are saved to `outputs/YYYY-MM-DD/` with full metadata.

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

- 🐛 [Report a bug](.github/ISSUE_TEMPLATE/bug_report.md)
- 💡 [Request a feature](.github/ISSUE_TEMPLATE/feature_request.md)
- 📝 [Submit a rune](.github/ISSUE_TEMPLATE/new_prompt.md)

## 📄 License

[MIT](LICENSE) © 2026 [NeuraByte Labs](https://neurabyte.com) / [Mustafa Saraç](https://github.com/mrsarac)

## 🙏 Credits

Built by **[NeuraByte Labs](https://neurabyte.com)** — crafting intelligent developer tools.

Developed and tested with [Grok](https://x.ai), [Gemini](https://deepmind.google/technologies/gemini/), [Claude](https://anthropic.com/claude), and [GPT-4o](https://openai.com).

---

<div align="center">

**[Website](https://neurabyte.com)** · **[Twitter](https://twitter.com/00xmorty)** · **[GitHub](https://github.com/neurabytelabs/rune)**

*Where Spinoza Meets Silicon* 🧬

<sub>If RUNE helped you, consider giving it a ⭐</sub>

</div>
