# RUNE Benchmark — Judge Protocol

This document is the **file contract** between the RUNE benchmark harness (`wand bench`)
and any external judging system. The harness is judge-agnostic: any judge — a human panel,
a multi-agent LLM workflow, or the built-in inline judge — that honors this contract
produces results the harness can ingest and analyze.

## Flow

```
wand bench generate   →  generations.jsonl            (both arms, all models)
wand bench export     →  judge_inbox/pairs_j{1..J}.jsonl   (blind, per-judge)
<external judging>    →  judge_outbox/verdicts.jsonl       (appended by judges)
wand bench ingest     →  analysis.json                (unblinded, statistics)
wand bench report     →  report.md                    (human-readable results)
```

All paths are relative to `benchmark/results/<run_id>/`.

## Input: `judge_inbox/pairs_j<N>.jsonl`

One file per judge slot (default 3 judges → `pairs_j1.jsonl`, `pairs_j2.jsonl`,
`pairs_j3.jsonl`). Each line is one pair:

```json
{"pair_id": "pr-3fa9c21b", "task_prompt": "…", "response_a": "…", "response_b": "…"}
```

- The A/B assignment is **randomized independently per judge slot** (seeded). Judge 1's
  "A" may be judge 2's "B" for the same pair. Never assume consistency across files.
- The files contain **no** model names, arm labels, timestamps, or metadata. Unblinding
  data lives only in `pairing_key.json`, which judges must never read.

## Output: `judge_outbox/verdicts.jsonl`

Each judge appends one line per pair:

```json
{"pair_id": "pr-3fa9c21b", "judge_id": "j1",
 "winner": "A",
 "scores": {"task_fulfillment": {"a": 4, "b": 5}, "accuracy": {"a": 5, "b": 5},
            "depth": {"a": 3, "b": 4}, "clarity": {"a": 4, "b": 4},
            "actionability": {"a": 3, "b": 4}},
 "rationale": "one line", "flags": []}
```

Rules:
- `judge_id` must match the inbox file the pair was read from (`j1`, `j2`, `j3`).
  Additional adversarial verdicts use `adv1`, `adv2`, …
- `winner` ∈ `{"A", "B", "tie"}` — relative to **that judge's own** A/B assignment.
- All 5 criteria required, integer scores 1–5 for both `a` and `b`.
- `flags` is a free-form list for anomalies (e.g. `["truncated_response"]`).
- One verdict per `(pair_id, judge_id)` — duplicates are rejected at ingest.

## Judging rules (the rubric)

The exact judge instruction text lives in `rune/bench/schemas.py::JUDGE_PROMPT` and MUST
be used verbatim by any LLM-based judge. Its core rules:

1. Evaluate **in the language of the task prompt** (Turkish prompt → judge the Turkish
   quality of the responses).
2. Longer is **not** better. Judge substance relative to what the task warrants.
3. Do not reward structure or formatting for its own sake — only where the task benefits.
4. `tie` only if the responses are genuinely indistinguishable in quality.
5. Judge only what is written. You do not know (and must not guess at) how either
   response was produced.

## Consensus procedure

- 3 primary judges per pair, **majority vote** decides the pair.
- On any non-unanimous outcome, **two** adversarial verifiers re-examine the pair
  (each with its own fresh blind assignment, prepared by the orchestrator — never by
  the verifiers themselves) and append verdicts (e.g. `j4`/`j5` or `adv1`/`adv2`),
  bringing the pair to 5 verdicts.
- Ingest requires every pair to end with an **odd** number of verdicts; the majority
  over all verdicts for the pair is final.

## Known limitation: label-blind, not style-blind

RUNE-amplified responses may self-reveal through structural artifacts (XML-ish scaffolds,
self-assigned confidence scores, layered headings). The protocol anonymizes **labels**,
not **style** — this is inherent to measuring the product as users experience it, and it
is why rubric rules 2–3 exist. Judge agreement rate and tie rate are reported as honesty
diagnostics alongside the headline number.
