# 🚀 Quick Start Guide

## Prerequisites

- Python 3.9+
- API access to at least one LLM (Gemini, OpenAI, or Anthropic)

## Installation

```bash
git clone https://github.com/mrsarac/master-prompts.git
cd master-prompts
```

No dependencies required beyond Python standard library and your LLM SDK.

## Your First Enhanced Prompt

```bash
# Take any simple prompt and enhance it with MP's 8-layer structure
python3 mp.py --raw "Write a function to parse CSV files"
```

This outputs the enhanced prompt wrapped in MP's XML template. You can copy this into any LLM chat interface.

## Run It End-to-End

```bash
# Enhance AND execute the prompt
python3 mp.py "Write a function to parse CSV files"
```

This enhances the prompt, sends it to the model, and saves the result to `outputs/`.

## Compare Raw vs Enhanced

```bash
python3 mp.py --compare "Explain Docker networking"
```

See the difference MP makes — same question, dramatically different output quality.

## Using the Prompt Library

Browse `prompts/` for 10 ready-made prompts:

```bash
ls prompts/
# 01_shader_debug.md  02_ui_polish.md  03_performance_audit.md ...
```

Each prompt file contains the XML template ready to paste into your LLM.

## Running Cross-Model Tests

```bash
python3 cross_model_test.py
```

Tests all prompts across multiple models and saves results to `outputs/`.

## Creating Custom Prompts

1. Start with the [v4.4 template](../Master%20Prompt%20Template%20v4.4.md)
2. Fill in L1 (Identity) and L2 (Mission) for your use case
3. Add L3 constraints specific to your domain
4. Set complexity level (L1–L5) in L0
5. Test with `mp.py --raw` to verify the structure
6. Consider [contributing it](../CONTRIBUTING.md) to the library!

## Next Steps

- 📖 Read the [Architecture](ARCHITECTURE.md) doc to understand the 8 layers
- 📊 Check [Benchmarks](BENCHMARKS.md) for model recommendations
- 📝 See the [Changelog](CHANGELOG.md) for version history
