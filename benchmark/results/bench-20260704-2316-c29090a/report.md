# RUNE Benchmark Report — `bench-20260704-2316-c29090a`

- Created: 2026-07-04T23:16:56
- Git SHA: `c29090ab431ab5117ec02cb6539cad0e9d86512e`
- Harness: rune-wand 2.1.0
- Prompt set: `benchmark/promptset_v1.jsonl` (n=25, sha256 `a45bd0f3fd1f…`)
- Models: gemini-3.1-pro-preview, gemini-3-flash-preview
- Seed: 7

## Headline

In blind pairwise comparison, RUNE-amplified prompts were preferred in **19.6%** of decided pairs (95% CI [10.2%, 29.3%]; 46 decided of 50 pairs; ties: 8.0%; exact binomial sign test p = 4.056e-05).

Raw counts: **9 treatment wins / 37 control wins / 4 ties** over 50 pairs.

Judge agreement: 39 unanimous, 11 split.

### Per-criterion score delta (treatment − control, 1–5 scale)

| criterion | mean delta |
|---|---|
| task_fulfillment | -0.31 |
| accuracy | -0.50 |
| depth | -0.23 |
| clarity | -0.36 |
| actionability | -0.61 |

### By domain

| | treatment wins | control wins | ties |
|---|---|---|---|
| analysis | 2 | 8 | 0 |
| coding | 0 | 7 | 3 |
| creative | 3 | 7 | 0 |
| research | 2 | 7 | 1 |
| writing | 2 | 8 | 0 |

### By model

| | treatment wins | control wins | ties |
|---|---|---|---|
| gemini-3-flash-preview | 3 | 20 | 2 |
| gemini-3.1-pro-preview | 6 | 17 | 2 |

## Judge panel note

Judging ran as an external Claude multi-agent workflow (blind, 3 primary judges/pair,
2 adversarial verifiers on any non-unanimous pair — see JUDGE_PROTOCOL.md). Mid-run,
the primary judge model (Claude/Fable) hit its monthly usage limit after 21/50 pairs
were fully judged. The remaining 29 pairs were judged by a second panel explicitly
forced to Claude Sonnet 5. Both panels follow the identical protocol and rubric;
splitting by panel:

| panel | pairs | treatment_win | control_win | tie |
|---|---|---|---|---|
| Fable (pairs 1–21) | 21 | 2 | 16 | 3 |
| Sonnet 5 (remaining 29) | 29 | 7 | 21 | 1 |

Both panels independently show control winning by a wide margin — the headline result
is not an artifact of the panel switch.

## Qualitative root-cause spot-check

Before publishing, we hand-read the 5 coding-domain pairs (0 treatment wins) end to
end — original prompt, full enhanced XML prompt, both outputs, and all judge
rationales unblinded. Findings, to rule out a harness or rubric artifact:

- Enhanced prompts are well-formed, substantive XML (1.5–4.7K chars), not truncated
  or garbled — the enhancement step itself executes correctly.
- Control and treatment outputs are comparable in length (e.g. 425 vs 419 chars,
  6347 vs 6525 chars) — losses are not a length-penalty or truncation artifact.
- Judge rationales cite specific, technical content differences, not generic
  "structure" complaints: e.g. for `p003` (multi-agent Git architecture), all 3
  judges independently flagged that the treatment's `git worktree add <path>
  origin/<branch>` command produces a detached HEAD, breaking the subsequent push —
  a genuine correctness defect, not a style preference. For `p001` (BST explainer),
  treatment stated the ordering property only for direct children instead of entire
  subtrees — an accuracy regression from the same model's un-amplified answer.
  Notably, `p003`'s own generated `L6_QA` layer explicitly asks "Are the Git commands
  syntactically correct?" — the scaffold requested correctness and the model still
  missed it, suggesting some of the model's generation budget went toward satisfying
  the meta-structure (persona, format, self-declared QA criteria) rather than toward
  the technical content itself.

This is a small, hand-read sample (5 of 50 pairs) and the mechanism above is a
plausible reading of the evidence, not a proven causal claim — but it is enough to
rule out "harness bug" or "rubric artifact" as the explanation for the headline
result. The defects are real, varied per pair, and consistent with the quantitative
finding.

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
wand bench generate --promptset benchmark/promptset_v1.jsonl --models gemini-3.1-pro-preview,gemini-3-flash-preview --seed 7
wand bench export
wand bench judge --api-url <openai-compat-endpoint> --model <judge-model>
wand bench ingest
wand bench report
```