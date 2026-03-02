<div align="center">

# ᚱ RUNE

### Every prompt is a spell.

*347 years ago, Spinoza wrote that understanding is power.*
*Today, we write prompts. Most of them are wishes. RUNE turns them into spells.*

<br>

![RUNE Hero](docs/rune_hero.jpeg)

<br>

[![Version](https://img.shields.io/badge/version-1.9-magenta.svg)](docs/CHANGELOG.md)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](#-quick-start)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Models](https://img.shields.io/badge/models-Gemini_3_|_GPT--5.2_|_Grok_4.1_|_Claude_4.6-purple.svg)](#-supported-models)
[![Grimoire](https://img.shields.io/badge/grimoire-42_runes-cyan.svg)](#-the-grimoire)
[![OpenClaw](https://img.shields.io/badge/OpenClaw-skill-green.svg)](#-openclaw-integration)

[The Problem](#-the-problem) · [The Solution](#-eight-layers-of-intent) · [Watch It Work](#-watch-it-work) · [Quick Start](#-quick-start) · [Grimoire](#-the-grimoire) · [Philosophy](#-why-spinoza) · [Roadmap](#-roadmap)

</div>

---

## 💀 The Problem

You write a prompt. You hope the AI understands. It doesn't. You rewrite. You add "be specific" and "think step by step." You get something mediocre. You accept it because you're tired.

**This is how 99% of people use AI.**

The gap between what you *mean* and what the AI *produces* is not a model problem. It's a **prompt problem.** You're casting spells without a wand.

> *"Most people don't have bad ideas. They have bad prompts."*

---

## ✨ The Solution

RUNE doesn't fix your prompt. It **transforms** it.

Your flat, ambiguous text becomes a structured 8-layer directive that tells the AI *exactly* who to be, how to think, what constraints to follow, and how to validate its own output.

Then it runs every result through the **Spinoza Validator** — a philosophical scoring engine based on four principles a 17th-century lens grinder would recognize.

<div align="center">

![Before & After](docs/rune_before_after.jpeg)

*Left: what you typed. Right: what the AI actually needed.*

</div>

### The numbers

| | Without RUNE | With RUNE |
|---|---|---|
| Prompt structure | Flat text | 8 semantic layers (XML) |
| Output quality | Hope-based | Validated (Spinoza A–F grade) |
| Reproducibility | Random | Deterministic |
| Cross-model consistency | Varies wildly | Structurally identical |
| Cost awareness | None | Per-call tracking |

---

## 🏗 Eight Layers of Intent

Every spell has structure. Every RUNE prompt has eight layers:

```
╔══════════════════════════════════════════════╗
║  L0  System Core      Who the AI is         ║
║  L1  Context           What it knows         ║
║  L2  Intent            What you want         ║
║  L3  Governance        What it can't do      ║
║  L4  Cognitive Engine  How it should think   ║
║  L5  Capabilities      What tools it has     ║
║  L6  Quality Assurance How it checks itself  ║
║  L7  Output Meta       How it delivers       ║
╚══════════════════════════════════════════════╝
```

You provide the intent. RUNE provides the architecture.

---

## 🔮 Watch It Work

### Interactive Mode — The AI asks before it acts

```
$ wand cast "Write a blog post about AI agents"

🔮 Spell Analysis
Domain: WRITING | Lang: EN

1) Audience?
   a) Developer  b) General  c) C-level  d) Custom...
2) Tone?
   a) Academic  b) Blog  c) Manifesto  d) Tutorial
3) Length?
   a) ~500  b) ~1500  c) ~3000+

▸ 1a 2c 3b

✓ Audience: technical | Tone: provocative | Length: medium

📋 Spell Summary
  8 RUNE layers will be applied ✨
  ✅ Confirm? [E/h]
```

### Quick Mode — No questions, pure speed

```bash
wand cast "Optimize this React component!"   # trailing ! = instant
wand cast -q "Debug this memory leak"         # --quick flag
```

### The Full Arsenal

```bash
wand cast "prompt"          # Interactive Q&A → enhance → execute
wand cast "prompt!"         # Quick mode — skip Q&A
wand inscribe "prompt"      # Show enhanced prompt only
wand duel "prompt"          # A/B: your prompt vs RUNE'd version
wand validate "any text"    # Spinoza philosophical validation
wand grimoire               # Browse 42 spell templates
wand forge                  # Create your own rune
wand fuse a.txt b.txt       # Merge multiple prompts into one
wand test "prompt"          # Benchmark across models
wand cost                   # What you've spent, by model
wand stats                  # Your prompt evolution over time
```

---

## ⚡ Quick Start

```bash
git clone https://github.com/neurabytelabs/rune.git
cd rune

# Configure (pick your model)
mkdir -p ~/.rune
cat > ~/.rune/config.toml << EOF
[llm]
api_url = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
api_key = "your-gemini-key"
default_model = "gemini-2.5-flash"
EOF

# Cast your first spell
python3 wand.py cast "Explain quantum computing to a curious 12-year-old"
```

That's it. No dependencies beyond Python 3.11+ and `requests`.

### One-command install for OpenClaw agents

```bash
npx clawhub@latest install rune-prompt-amplification
```

---

## 🔮 Why Spinoza?

In 1677, Baruch Spinoza published the *Ethics* — a book that argued understanding the nature of things is the highest form of freedom. He was excommunicated for it.

RUNE borrows four ideas from Spinoza and turns them into a validation engine:

| Principle | Weight | What it measures |
|-----------|--------|------------------|
| **Conatus** | 30% | Drive. Is the output *trying* to be useful? Does it persist toward a goal? |
| **Ratio** | 35% | Reason. Is the logic coherent? Is the structure sound? |
| **Laetitia** | 15% | Joy. Is the output clear, positive, and elevating? |
| **Natura** | 20% | Nature. Does it flow? Does it feel *right*? |

Every output gets a score. Every score gets a grade.

```
  clarity         ██████████ 1.0
  coherence       ██████████ 1.0
  completeness    █████████░ 0.9
  accuracy        ██████████ 1.0
  relevance       ██████████ 1.0
  depth           ████████░░ 0.8
  actionability   ██████████ 1.0

  Overall: 0.96  Grade: A
```

> *"The highest activity a human being can attain is learning for understanding, because to understand is to be free."*
> — Baruch Spinoza

---

## 📚 The Grimoire

42 battle-tested spell templates across 5 schools of magic:

### 💻 Coding (10 runes)
Shader debug · Code review · Security review · Refactoring · Test generation · API design · Systematic debug · Architecture · DB schema · CI/CD pipeline

### 📝 Writing (6 runes)
Blog post · Pitch deck · Technical doc · Email outreach · Social media · Storytelling

### 📊 Analysis (6 runes)
Competitor · SWOT · Data analysis · Market research · Financial model · User research

### 🎨 Creative (6 runes)
Brainstorm · Naming · Design brief · Game design · Music composition · UX flow

### 🤖 AI/ML (6 runes)
Model evaluation · Dataset curation · Prompt chain · Agent design · Fine-tuning plan · RAG system

> Browse: `wand grimoire` · Search: `wand grimoire search "security"` · Create your own: `wand forge`

---

## 🧬 Architecture

```
┌─────────────────────────────────────────────┐
│              RUNE v1.9                      │
│         "Every prompt is a spell"           │
├─────────────────────────────────────────────┤
│                                             │
│  🪄 WAND CLI                                │
│  Interactive Q&A · Quick Mode · 12 commands │
│                                             │
│  📜 8-LAYER ENHANCER                        │
│  L0 → L7: structured prompt transformation  │
│                                             │
│  🔮 SPINOZA VALIDATOR                       │
│  Conatus · Ratio · Laetitia · Natura        │
│                                             │
├─────────────────────────────────────────────┤
│                                             │
│  🧬 Synthesis    Fuse multiple prompts      │
│  🧠 Memory       Track prompt evolution     │
│  🔀 Router       Pick the right model       │
│  🔍 Search       TF-IDF grimoire search     │
│  🧪 Evaluator    Cross-model A/B testing    │
│  💰 Cost         Per-model spend tracking   │
│  🐝 Swarm        Multi-agent tournament     │
│                                             │
└─────────────────────────────────────────────┘
```

---

## 🤖 Supported Models

| Provider | Model | Best For |
|----------|-------|----------|
| **Google** | Gemini 3 Flash | Fast, cheap, great compliance |
| **Google** | Gemini 3 Pro | Deep tasks, structured output |
| **xAI** | Grok 4.1 Fast | Best quality-per-dollar |
| **xAI** | Grok Code Fast | Code generation |
| **Anthropic** | Claude Opus 4.6 | Deep reasoning, prose |
| **Anthropic** | Claude Sonnet 4.5 | Balanced quality |
| **OpenAI** | GPT-5.2 | Multimodal, balanced |
| **OpenAI** | o4-mini | Math, logic, complex reasoning |

RUNE works with any OpenAI-compatible endpoint. Bring your own model.

---

## 🗺 Roadmap

### v1.9 ✅ Current
- [x] Interactive Q&A with compact answers (`1a 2b 3c`)
- [x] Quick mode (trailing `!` or `--quick`)
- [x] Intent detection (domain + language)
- [x] 42 grimoire templates across 5 domains
- [x] Swarm — multi-agent prompt tournament
- [x] OpenClaw skill integration
- [x] Spinoza Validator (EN + TR)
- [x] Cost tracking + memory evolution

### v2.0 — The Awakening
- [ ] **Oracle** — self-improving prompts via feedback loops
- [ ] **Prompt DNA** — genetic algorithm prompt evolution
- [ ] **Marketplace** — community prompt sharing & rating
- [ ] **Visual Pipeline** — text-to-image prompt engineering
- [ ] **Agent Negotiation** — agent-to-agent prompt collaboration

---

## 🤝 For Everyone

<div align="center">

![RUNE for Everyone](docs/rune_for_everyone.jpeg)

</div>

You don't need to be a developer. You don't need to understand AI. You just need to know what you want.

RUNE is the bridge between your intent and the AI's capability. It's the difference between asking and commanding. Between hoping and knowing.

**Students** use it to write better papers. **Parents** use it to get actual help with homework. **Founders** use it to draft pitches that close. **Developers** use it to generate code that works the first time.

The spell is the same. The wand makes it work.

---

<div align="center">

<br>

*"We are not meant to interact with machines through hope.*
*We are meant to interact through understanding."*

— The RUNE Manifesto

<br>

**[GitHub](https://github.com/neurabytelabs/rune)** · **[NeuraByte Labs](https://neurabytelabs.com)** · **[ClawHub](https://clawhub.com)**

*Where Spinoza Meets Silicon* ᚱ

<br>

[![Star](https://img.shields.io/github/stars/neurabytelabs/rune?style=social)](https://github.com/neurabytelabs/rune)

*If RUNE made your prompts better, give it a ⭐*

<sub>Built with 🔮 by [NeuraByte Labs](https://neurabytelabs.com) · MIT License · © 2026</sub>

</div>
