<div align="center">

# 🧬 Master Prompt

**A structured 8-layer prompt engineering framework for high-fidelity LLM outputs**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-4.4-blue.svg)](docs/CHANGELOG.md)
[![Prompts](https://img.shields.io/badge/prompt_library-10_prompts-green.svg)](prompts/)
[![Models Tested](https://img.shields.io/badge/models_tested-6+-purple.svg)](docs/BENCHMARKS.md)

[Quick Start](#-quick-start) · [Architecture](#-architecture) · [Prompt Library](#-prompt-library) · [Benchmarks](#-benchmarks) · [Contributing](CONTRIBUTING.md)

</div>

---

## What is Master Prompt?

Most prompts are flat text — unstructured, ambiguous, and inconsistent across models. **Master Prompt (MP)** is a layered XML template that tells LLMs *exactly* how to think, respond, and self-correct.

MP wraps your intent in 8 semantic layers — from identity and constraints to cognitive reasoning and output formatting. The result: outputs that are structured, reproducible, and dramatically higher quality across GPT-4o, Gemini, Claude, and others.

Born from real-world prompt engineering across 50+ projects, MP has evolved through 6 major versions. It's battle-tested in production for shader debugging, API design, code review, and technical writing.

> 📖 **Turkish documentation available:** See [LLM Master Prompt Rehberi](LLM%20Master%20Prompt%20Rehberi%20Oluşturma.md)

## ⚡ Quick Start

```bash
# Clone
git clone https://github.com/mrsarac/master-prompts.git
cd master-prompts

# Enhance any prompt with the 8-layer template
python3 mp.py "Write a REST API for a todo app"

# Just see the enhanced prompt (don't run it)
python3 mp.py --raw "Optimize this React component"

# Compare raw vs enhanced output
python3 mp.py --compare "Debug this shader"

# Use a specific model
python3 mp.py --model gemini-3-flash "Design a database schema"
```

## 🏗 Architecture

```
┌─────────────────────────────────────────────┐
│              MASTER PROMPT v4.4              │
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
└─────────────────────────────────────────────┘
```

> Each layer is an XML block. Lower layers override higher ones. Unused layers can be omitted for simpler tasks (Complexity L1–L2 auto-skips).

## ✨ Features

| | Feature | Description |
|---|---|---|
| 🎯 | **8-Layer Structure** | Semantic separation of concerns for prompts |
| 🔄 | **Polyglot Rendering** | Auto-detects language, responds accordingly |
| 🏷️ | **Domain Presets** | CODING / WRITING / ANALYSIS modes |
| 📊 | **Complexity Scaling** | L1–L5 complexity auto-adjusts layer depth |
| 🧠 | **Cognitive Engine** | Built-in chain-of-thought and reasoning |
| ✅ | **Self-QA** | Output validation and retry logic |
| 📦 | **CLI Tool** | `mp.py` enhances any prompt instantly |
| 🧪 | **Cross-Model Testing** | Benchmark prompts across 6+ models |
| 📚 | **Prompt Library** | 10 production-ready prompts included |
| 👁️ | **Observability** | Active layer tracking in responses |

## 📚 Prompt Library

Ready-to-use prompts built on the MP template:

| # | Prompt | Use Case |
|---|--------|----------|
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

Cross-model testing with `cross_model_test.py` across identical prompts:

| Model | Template Compliance | Output Quality | Structured Output |
|-------|:------------------:|:--------------:|:-----------------:|
| Gemini Flash 🥇 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| GPT-4o 🥈 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| Gemini Pro 🥉 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| Claude Sonnet | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| Claude Opus | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |

> **Key finding:** Gemini Flash leads in template compliance. Claude models produce excellent prose but tend to ignore XML structure. See [full benchmarks →](docs/BENCHMARKS.md)

## 🛠 CLI Usage

```bash
# Basic: enhance and run a prompt
python3 mp.py "Explain microservices architecture"

# Raw mode: just get the enhanced prompt
python3 mp.py --raw "Build a login form"

# Compare: see raw vs enhanced output side by side
python3 mp.py --compare "Write unit tests for auth module"

# Choose model
python3 mp.py --model gemini-3-flash "Optimize this SQL query"
```

All outputs are saved to `outputs/YYYY-MM-DD/` with full metadata.

## 📈 Evolution

```
v3.0 ──→ v4.0 ──→ v4.1 ──→ v4.2 ──→ v4.3 ──→ v4.4
 │        │        │        │        │        │
 7        11       12       14       8        8 layers
 static   agentic  multi-   self-    consol-  hyper-
 template arch.    modal    improve  idated   structured
                   + cost   + memory          + polyglot
                   aware                      + presets
```

See [full changelog →](docs/CHANGELOG.md)

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

- 🐛 [Report a bug](.github/ISSUE_TEMPLATE/bug_report.md)
- 💡 [Request a feature](.github/ISSUE_TEMPLATE/feature_request.md)
- 📝 [Submit a prompt](.github/ISSUE_TEMPLATE/new_prompt.md)

## 📄 License

[MIT](LICENSE) © 2026 [NeuraByte Labs](https://neurabyte.com) / [Mustafa Saraç](https://github.com/mrsarac)

## 🙏 Credits

Built by **[NeuraByte Labs](https://neurabyte.com)** — crafting intelligent developer tools.

Developed and tested with [Gemini](https://deepmind.google/technologies/gemini/) and [Claude](https://anthropic.com/claude).

---

<div align="center">

**[Website](https://neurabyte.com)** · **[Twitter](https://twitter.com/00xmorty)** · **[GitHub](https://github.com/mrsarac/master-prompts)**

<sub>If Master Prompt helped you, consider giving it a ⭐</sub>

</div>
