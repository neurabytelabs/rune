"""Tests for rune.bench.stats — vote mapping, sign test, cluster bootstrap, deltas."""

from __future__ import annotations

import pytest

from rune.bench.stats import (
    binomial_sign_test,
    bootstrap_ci,
    criterion_deltas,
    judge_agreement,
    majority_vote,
    preference_rate,
)


def _verdict(judge_id, winner, a=3, b=3):
    scores = {
        c: {"a": a, "b": b}
        for c in ("task_fulfillment", "accuracy", "depth", "clarity", "actionability")
    }
    return {
        "pair_id": "pr-x",
        "judge_id": judge_id,
        "winner": winner,
        "scores": scores,
        "rationale": "",
        "flags": [],
    }


ASSIGN = {
    "j1": {"A": "treatment", "B": "control"},
    "j2": {"A": "control", "B": "treatment"},
    "j3": {"A": "treatment", "B": "control"},
}


# ── majority vote ───────────────────────────────────────────────────────────


def test_majority_vote_maps_through_assignments():
    # j1: A=treatment wins; j2: B=treatment wins; j3: B=control wins → treatment 2-1
    verdicts = [_verdict("j1", "A"), _verdict("j2", "B"), _verdict("j3", "B")]
    assert majority_vote(verdicts, ASSIGN) == "treatment"


def test_majority_vote_control_wins():
    verdicts = [_verdict("j1", "B"), _verdict("j2", "A"), _verdict("j3", "A")]
    assert majority_vote(verdicts, ASSIGN) == "control"


def test_majority_vote_tie_plurality():
    verdicts = [_verdict("j1", "tie"), _verdict("j2", "tie"), _verdict("j3", "A")]
    assert majority_vote(verdicts, ASSIGN) == "tie"


def test_majority_vote_with_adversarial_fifth_judge():
    assign = dict(ASSIGN)
    assign["adv1"] = {"A": "control", "B": "treatment"}
    assign["j4"] = {"A": "treatment", "B": "control"}
    verdicts = [
        _verdict("j1", "A"),  # treatment
        _verdict("j2", "A"),  # control
        _verdict("j3", "B"),  # control
        _verdict("j4", "A"),  # treatment
        _verdict("adv1", "B"),  # treatment
    ]
    assert majority_vote(verdicts, assign) == "treatment"


# ── headline stats ──────────────────────────────────────────────────────────


def test_preference_rate_ignores_ties():
    assert preference_rate(wins=6, losses=2) == pytest.approx(0.75)


def test_preference_rate_no_decided_pairs():
    assert preference_rate(wins=0, losses=0) is None


def test_binomial_sign_test_exact_values():
    # X ~ Bin(10, 0.5): 2 * P(X <= 2) = 2 * (1+10+45)/1024 = 0.109375
    assert binomial_sign_test(wins=8, losses=2) == pytest.approx(0.109375)
    # symmetric
    assert binomial_sign_test(wins=2, losses=8) == pytest.approx(0.109375)
    # even split → p = 1.0 (capped)
    assert binomial_sign_test(wins=5, losses=5) == pytest.approx(1.0)


def test_bootstrap_ci_deterministic_and_sane():
    # 10 prompts, one pair each: 8 treatment wins, 2 control wins
    results = [
        {"prompt_id": f"p{i:03d}", "result": "treatment_win" if i <= 8 else "control_win"}
        for i in range(1, 11)
    ]
    lo1, hi1 = bootstrap_ci(results, iters=2000, seed=7)
    lo2, hi2 = bootstrap_ci(results, iters=2000, seed=7)
    assert (lo1, hi1) == (lo2, hi2)
    assert 0.0 <= lo1 <= 0.8 <= hi1 <= 1.0


def test_bootstrap_ci_all_wins_degenerate():
    results = [{"prompt_id": f"p{i}", "result": "treatment_win"} for i in range(5)]
    lo, hi = bootstrap_ci(results, iters=500, seed=7)
    assert (lo, hi) == (1.0, 1.0)


# ── criterion deltas & agreement ────────────────────────────────────────────


def test_criterion_deltas_signed_treatment_minus_control():
    # j1: A=treatment. treatment scores a=5, control b=3 → delta +2 per criterion
    # j2: A=control. treatment is b=4, control a=2 → delta +2 per criterion
    verdicts = [_verdict("j1", "A", a=5, b=3), _verdict("j2", "B", a=2, b=4)]
    deltas = criterion_deltas(verdicts, ASSIGN)
    assert set(deltas) == {"task_fulfillment", "accuracy", "depth", "clarity", "actionability"}
    for crit in deltas:
        assert deltas[crit] == pytest.approx(2.0)


def test_judge_agreement_counts():
    pair_verdicts = {
        "pr-1": [_verdict("j1", "A"), _verdict("j2", "B"), _verdict("j3", "A")],
        "pr-2": [_verdict("j1", "A"), _verdict("j2", "A"), _verdict("j3", "B")],
    }
    assignments = {"pr-1": ASSIGN, "pr-2": ASSIGN}
    agg = judge_agreement(pair_verdicts, assignments)
    # pr-1: arm votes = treatment, treatment, treatment → unanimous
    # pr-2: treatment, control, control → split
    assert agg == {"unanimous": 1, "split": 1}
