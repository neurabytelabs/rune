# 📊 Benchmarks

## Methodology

All prompts from the library were tested across 6 models using `cross_model_test.py`. Each prompt was run 3 times per model with identical parameters. Evaluation criteria:

1. **Template Compliance** — Does the output follow the requested structure?
2. **Output Quality** — Is the content accurate, complete, and useful?
3. **Structured Output** — Does it use proper formatting (headers, code blocks, lists)?

Scores are averaged across all prompts and runs (1–5 scale).

## Results

| Model | Template Compliance | Output Quality | Structured Output | Overall |
|-------|:------------------:|:--------------:|:-----------------:|:-------:|
| **Gemini Flash** 🥇 | 4.8 | 4.2 | 4.7 | **4.57** |
| **GPT-4o** 🥈 | 4.1 | 4.7 | 4.3 | **4.37** |
| **Gemini Pro** 🥉 | 4.0 | 4.3 | 4.1 | **4.13** |
| Claude Sonnet 3.5 | 3.2 | 4.6 | 3.4 | **3.73** |
| Claude Opus | 3.0 | 4.8 | 3.3 | **3.70** |
| GPT-4o Mini | 3.5 | 3.8 | 3.9 | **3.73** |

## Key Findings

### 🏆 Gemini Flash leads in template compliance
Flash consistently respects XML layer structure and produces outputs that match the requested format. It's the best model for MP-style structured prompts.

### 📝 Claude produces the best prose
Claude Opus and Sonnet excel at natural language quality — nuanced, well-written, comprehensive. However, they tend to **ignore XML structure** and reformulate prompts in their own style.

### ⚡ Flash > Pro for templates
Counterintuitively, Gemini Flash outperforms Gemini Pro on template compliance. Pro tends to "overthink" and deviate from structure, while Flash follows instructions more literally.

### 🔄 GPT-4o is the all-rounder
Solid across all categories. Best choice when you need both structure and quality without committing to a specific model ecosystem.

## Recommendations

| Use Case | Recommended Model |
|----------|-------------------|
| Maximum template compliance | Gemini Flash |
| Best prose quality | Claude Opus |
| Balanced performance | GPT-4o |
| Cost-effective testing | Gemini Flash |
| Creative writing with MP | Claude Sonnet |
| API/code generation | GPT-4o or Gemini Flash |

## Running Your Own Benchmarks

```bash
python3 cross_model_test.py
```

Results are saved to `outputs/` with full metadata for analysis.
