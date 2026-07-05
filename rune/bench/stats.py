"""Benchmark statistics — pure stdlib (repo policy: requests is the only dependency).

Headline metric: blind pairwise preference rate = wins / (wins + losses), ties
excluded from the denominator but reported. Uncertainty via cluster bootstrap
over prompt_id (the 2 model-pairs of one prompt are correlated). Significance
via exact two-sided binomial sign test.
"""

from __future__ import annotations

import math
import random
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Tuple

from rune.bench.schemas import RUBRIC_CRITERIA


def _arm_vote(verdict: Dict[str, Any], assignment: Dict[str, Dict[str, str]]) -> str:
    winner = verdict["winner"]
    if winner == "tie":
        return "tie"
    return assignment[verdict["judge_id"]][winner]


def majority_vote(verdicts: List[Dict[str, Any]], assignment: Dict[str, Dict[str, str]]) -> str:
    """Map each verdict through its judge's A/B assignment, take the plurality.

    A plurality tie between outcomes resolves to "tie".
    """
    counts = Counter(_arm_vote(v, assignment) for v in verdicts)
    top = counts.most_common()
    if len(top) > 1 and top[0][1] == top[1][1]:
        return "tie"
    return top[0][0]


def preference_rate(wins: int, losses: int) -> Optional[float]:
    decided = wins + losses
    if decided == 0:
        return None
    return wins / decided


def binomial_sign_test(wins: int, losses: int) -> float:
    """Exact two-sided binomial sign test against p=0.5, ties excluded."""
    n = wins + losses
    if n == 0:
        return 1.0
    k = min(wins, losses)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2**n
    return min(1.0, 2 * tail)


def bootstrap_ci(
    pair_results: List[Dict[str, Any]],
    iters: int = 10_000,
    seed: int = 7,
    confidence: float = 0.95,
) -> Tuple[float, float]:
    """Cluster bootstrap over prompt_id.

    Args:
        pair_results: [{"prompt_id": ..., "result": "treatment_win|control_win|tie"}]
    """
    clusters: Dict[str, List[str]] = defaultdict(list)
    for r in pair_results:
        clusters[r["prompt_id"]].append(r["result"])
    prompt_ids = sorted(clusters)

    rng = random.Random(seed)
    rates: List[float] = []
    for _ in range(iters):
        wins = losses = 0
        for _ in prompt_ids:
            for result in clusters[rng.choice(prompt_ids)]:
                if result == "treatment_win":
                    wins += 1
                elif result == "control_win":
                    losses += 1
        rate = preference_rate(wins, losses)
        if rate is not None:
            rates.append(rate)

    if not rates:
        return (0.0, 1.0)
    rates.sort()
    alpha = (1 - confidence) / 2
    lo = rates[int(alpha * (len(rates) - 1))]
    hi = rates[int((1 - alpha) * (len(rates) - 1))]
    return (lo, hi)


def criterion_deltas(
    verdicts: List[Dict[str, Any]], assignment: Dict[str, Dict[str, str]]
) -> Dict[str, float]:
    """Mean per-criterion score delta (treatment − control) across verdicts."""
    sums: Dict[str, float] = {c: 0.0 for c in RUBRIC_CRITERIA}
    n = 0
    for v in verdicts:
        slot_a_arm = assignment[v["judge_id"]]["A"]
        t_key, c_key = ("a", "b") if slot_a_arm == "treatment" else ("b", "a")
        for crit in RUBRIC_CRITERIA:
            sums[crit] += v["scores"][crit][t_key] - v["scores"][crit][c_key]
        n += 1
    if n == 0:
        return {c: 0.0 for c in RUBRIC_CRITERIA}
    return {c: sums[c] / n for c in RUBRIC_CRITERIA}


def judge_agreement(
    pair_verdicts: Dict[str, List[Dict[str, Any]]],
    pair_assignments: Dict[str, Dict[str, Dict[str, str]]],
) -> Dict[str, int]:
    """Count pairs with unanimous vs split arm-level votes (honesty diagnostic)."""
    agg = {"unanimous": 0, "split": 0}
    for pair_id, verdicts in pair_verdicts.items():
        votes = {_arm_vote(v, pair_assignments[pair_id]) for v in verdicts}
        agg["unanimous" if len(votes) == 1 else "split"] += 1
    return agg
