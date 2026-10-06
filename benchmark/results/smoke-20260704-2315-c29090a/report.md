# RUNE Benchmark Report — `smoke-20260704-2315-c29090a`

- Created: 2026-07-04T23:15:15  
- Git SHA: `c29090ab431ab5117ec02cb6539cad0e9d86512e`  
- Harness: rune-wand 2.1.0  
- Prompt set: `benchmark/promptset_v1.jsonl` (n=1, sha256 `a45bd0f3fd1f…`)  
- Models: gemini-3.1-pro-preview  
- Seed: 7

## Headline

In blind pairwise comparison, RUNE-amplified prompts were preferred in **100.0%** of decided pairs (95% CI [100.0%, 100.0%]; 1 decided of 1 pairs; ties: 0.0%; exact binomial sign test p = 1).

Raw counts: **1 treatment wins / 0 control wins / 0 ties** over 1 pairs.

Judge agreement: 1 unanimous, 0 split.

### Per-criterion score delta (treatment − control, 1–5 scale)

| criterion | mean delta |
|---|---|
| task_fulfillment | +0.00 |
| accuracy | +1.00 |
| depth | +0.00 |
| clarity | +0.00 |
| actionability | +0.00 |

### By domain

| | treatment wins | control wins | ties |
|---|---|---|---|
| coding | 1 | 0 | 0 |

### By model

| | treatment wins | control wins | ties |
|---|---|---|---|
| gemini-3.1-pro-preview | 1 | 0 | 0 |

## Limitations

- **The protocol is label-blind, not style-blind.** RUNE-amplified responses may self-reveal through
  structural artifacts. Judges are instructed not to reward structure per se; judge
  agreement and tie rates above are the honesty diagnostics.
- **Single sample per cell** at the configured temperature — the benchmark measures the
  output distribution users actually get, not a best-of-N.
- **Generation model family is Gemini only**; judging is cross-family but single-family
  (see JUDGE_PROTOCOL.md for the judge configuration of this run).
- The prompt set was partly authored by RUNE's developer; prompt IDs, sources, and the
  full set are committed for scrutiny.

## Reproduce

```bash
wand bench generate --promptset benchmark/promptset_v1.jsonl --models gemini-3.1-pro-preview --seed 7
wand bench export
wand bench judge --api-url <openai-compat-endpoint> --model <judge-model>
wand bench ingest
wand bench report
```