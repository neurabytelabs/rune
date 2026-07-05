"""Verdict ingest/validation, run analysis, and the inline OpenAI-compat judge.

The harness is judge-agnostic: any judge that honors benchmark/JUDGE_PROTOCOL.md
(external multi-agent workflow, human panel, or the inline judge below) writes
the same verdicts.jsonl and flows through the same ingest path.
"""

from __future__ import annotations

import json
import re
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

from rune.bench.schemas import (
    JUDGE_PROMPT,
    RUBRIC_CRITERIA,
    WINNERS,
    append_jsonl,
    read_jsonl,
)
from rune.bench.stats import (
    binomial_sign_test,
    bootstrap_ci,
    criterion_deltas,
    judge_agreement,
    majority_vote,
    preference_rate,
)


class IngestError(ValueError):
    """Raised when the verdict set violates the judge protocol."""


# ── validation ───────────────────────────────────────────────────────────────


def validate_verdicts(key: Dict[str, Any], verdicts: List[Dict[str, Any]]) -> None:
    pairs = key["pairs"]
    seen: set[tuple] = set()
    counts: Dict[str, int] = defaultdict(int)

    for v in verdicts:
        pair_id = v.get("pair_id")
        if pair_id not in pairs:
            raise IngestError(f"unknown pair_id {pair_id}")
        combo = (pair_id, v.get("judge_id"))
        if combo in seen:
            raise IngestError(f"duplicate verdict for {combo}")
        seen.add(combo)
        if v.get("winner") not in WINNERS:
            raise IngestError(f"{pair_id}: invalid winner {v.get('winner')!r}")
        scores = v.get("scores", {})
        for crit in RUBRIC_CRITERIA:
            if crit not in scores:
                raise IngestError(f"{pair_id}: missing criterion {crit}")
            for side in ("a", "b"):
                val = scores[crit].get(side)
                if not isinstance(val, int) or not 1 <= val <= 5:
                    raise IngestError(f"{pair_id}: {crit}.{side} out of range: {val!r}")
        counts[pair_id] += 1

    missing = sorted(set(pairs) - set(counts))
    if missing:
        raise IngestError(f"missing verdicts for pair(s): {', '.join(missing)}")
    for pair_id, n in counts.items():
        if n % 2 == 0:
            raise IngestError(f"{pair_id}: verdict count must be odd, got {n}")


# ── analysis ─────────────────────────────────────────────────────────────────


def analyze_run(
    run_dir: Path | str,
    prompt_domains: Dict[str, str],
    bootstrap_iters: int = 10_000,
    seed: int = 7,
) -> Dict[str, Any]:
    """Unblind verdicts via pairing_key.json, compute stats, write analysis.json."""
    run_dir = Path(run_dir)
    key = json.loads((run_dir / "pairing_key.json").read_text(encoding="utf-8"))
    verdicts = read_jsonl(run_dir / "judge_outbox" / "verdicts.jsonl")
    validate_verdicts(key, verdicts)

    by_pair: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for v in verdicts:
        by_pair[v["pair_id"]].append(v)

    pair_results: Dict[str, Dict[str, Any]] = {}
    flat_results: List[Dict[str, Any]] = []
    wins = losses = ties = 0
    by_domain: Dict[str, Dict[str, int]] = defaultdict(
        lambda: {"treatment_win": 0, "control_win": 0, "tie": 0}
    )
    by_model: Dict[str, Dict[str, int]] = defaultdict(
        lambda: {"treatment_win": 0, "control_win": 0, "tie": 0}
    )

    for pair_id, meta in key["pairs"].items():
        outcome = majority_vote(by_pair[pair_id], meta["assignments"])
        result = {"treatment": "treatment_win", "control": "control_win", "tie": "tie"}[outcome]
        if result == "treatment_win":
            wins += 1
        elif result == "control_win":
            losses += 1
        else:
            ties += 1
        pair_results[pair_id] = {
            "prompt_id": meta["prompt_id"],
            "model": meta["model"],
            "result": result,
        }
        flat_results.append({"prompt_id": meta["prompt_id"], "result": result})
        domain = prompt_domains.get(meta["prompt_id"], "unknown")
        by_domain[domain][result] += 1
        by_model[meta["model"]][result] += 1

    assignments_by_pair = {pid: key["pairs"][pid]["assignments"] for pid in by_pair}
    deltas_sum: Dict[str, float] = {c: 0.0 for c in RUBRIC_CRITERIA}
    for pid, vs in by_pair.items():
        d = criterion_deltas(vs, assignments_by_pair[pid])
        for c in RUBRIC_CRITERIA:
            deltas_sum[c] += d[c]
    n_pairs = len(by_pair)
    deltas = {c: deltas_sum[c] / n_pairs for c in RUBRIC_CRITERIA} if n_pairs else deltas_sum

    ci_lo, ci_hi = bootstrap_ci(flat_results, iters=bootstrap_iters, seed=seed)
    analysis = {
        "run_id": key["run_id"],
        "pairs": pair_results,
        "headline": {
            "wins": wins,
            "losses": losses,
            "ties": ties,
            "preference_rate": preference_rate(wins, losses),
            "ci95": [ci_lo, ci_hi],
            "p_value": binomial_sign_test(wins, losses),
            "n_pairs": n_pairs,
        },
        "criterion_deltas": deltas,
        "breakdowns": {"by_domain": dict(by_domain), "by_model": dict(by_model)},
        "judge_agreement": judge_agreement(dict(by_pair), assignments_by_pair),
    }
    (run_dir / "analysis.json").write_text(
        json.dumps(analysis, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return analysis


# ── inline judge (outside reproducibility path) ──────────────────────────────


def _chat(api_url: str, api_key: str, model: str, prompt: str, timeout: int) -> str:
    """Minimal OpenAI-compat chat call. Deliberately independent of cli.helpers:
    no global CONFIG, no sys.exit — errors propagate to the caller."""
    resp = requests.post(
        api_url,
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0,
        },
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def _parse_verdict_json(raw: str) -> Optional[Dict[str, Any]]:
    match = re.search(r"\{[\s\S]*\}", raw)
    if not match:
        return None
    try:
        data = json.loads(match.group())
    except json.JSONDecodeError:
        return None
    if data.get("winner") not in WINNERS:
        return None
    scores = data.get("scores", {})
    for crit in RUBRIC_CRITERIA:
        for side in ("a", "b"):
            val = scores.get(crit, {}).get(side)
            if not isinstance(val, int) or not 1 <= val <= 5:
                return None
    return data


def judge_pairs_inline(
    run_dir: Path | str,
    api_url: str,
    api_key: str,
    model: str,
    judges: int = 3,
    timeout: int = 120,
    delay: float = 0.0,
) -> int:
    """Judge every un-judged pair in each judge slot's inbox. Resumable.

    Returns the number of new verdicts written.
    """
    run_dir = Path(run_dir)
    outbox = run_dir / "judge_outbox" / "verdicts.jsonl"
    done = {(v["pair_id"], v["judge_id"]) for v in read_jsonl(outbox)}

    written = 0
    for n in range(1, judges + 1):
        slot = f"j{n}"
        for rec in read_jsonl(run_dir / "judge_inbox" / f"pairs_{slot}.jsonl"):
            if (rec["pair_id"], slot) in done:
                continue
            prompt = JUDGE_PROMPT.format(
                task_prompt=rec["task_prompt"],
                response_a=rec["response_a"],
                response_b=rec["response_b"],
            )
            verdict = None
            for _attempt in range(2):
                raw = _chat(api_url, api_key, model, prompt, timeout)
                verdict = _parse_verdict_json(raw)
                if verdict is not None:
                    break
            if verdict is None:
                raise IngestError(f"{rec['pair_id']}/{slot}: judge returned unparseable JSON")
            append_jsonl(
                outbox,
                {
                    "pair_id": rec["pair_id"],
                    "judge_id": slot,
                    "winner": verdict["winner"],
                    "scores": verdict["scores"],
                    "rationale": verdict.get("rationale", ""),
                    "flags": verdict.get("flags", []),
                },
            )
            written += 1
            if delay:
                time.sleep(delay)
    return written
