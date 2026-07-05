"""Tests for rune.bench.judging — verdict ingest/validation and the inline judge."""

from __future__ import annotations

import json

import pytest

from rune.bench.judging import (
    IngestError,
    analyze_run,
    judge_pairs_inline,
    validate_verdicts,
)
from rune.bench.pairing import export_judge_inboxes
from rune.bench.schemas import append_jsonl, read_jsonl

RUN_ID = "bench-20260704-1200-abc1234"


def _gen(prompt_id, model, arm, output):
    return {
        "gen_id": f"{prompt_id}|{model}|{arm}",
        "prompt_id": prompt_id,
        "model": model,
        "arm": arm,
        "enhanced_prompt": None,
        "output": output,
        "started_at": "2026-07-04T10:00:00",
        "duration_s": 1.0,
        "chars_out": len(output),
        "error": None,
    }


def _scores(a=3, b=3):
    return {
        c: {"a": a, "b": b}
        for c in ("task_fulfillment", "accuracy", "depth", "clarity", "actionability")
    }


@pytest.fixture
def run_dir(tmp_path):
    """A tiny exported run: 2 prompts × 1 model = 2 pairs, 3 judges."""
    gens = []
    for pid in ("p001", "p002"):
        gens.append(_gen(pid, "model-x", "control", f"raw answer {pid}"))
        gens.append(_gen(pid, "model-x", "treatment", f"amplified answer {pid}"))
    prompts = {"p001": "task one", "p002": "task two"}
    export_judge_inboxes(tmp_path, RUN_ID, seed=7, generations=gens, prompts=prompts, judges=3)
    return tmp_path


def _winner_for(key, pair_id, slot, arm):
    """Return the A/B letter that maps to `arm` for this judge slot."""
    assignment = key["pairs"][pair_id]["assignments"][slot]
    return "A" if assignment["A"] == arm else "B"


def _write_unanimous_verdicts(run_dir, winning_arm="treatment"):
    key = json.loads((run_dir / "pairing_key.json").read_text())
    for pair_id in key["pairs"]:
        for slot in ("j1", "j2", "j3"):
            append_jsonl(
                run_dir / "judge_outbox" / "verdicts.jsonl",
                {
                    "pair_id": pair_id,
                    "judge_id": slot,
                    "winner": _winner_for(key, pair_id, slot, winning_arm),
                    "scores": _scores(),
                    "rationale": "",
                    "flags": [],
                },
            )
    return key


# ── validation ──────────────────────────────────────────────────────────────


def test_valid_verdicts_pass(run_dir):
    key = _write_unanimous_verdicts(run_dir)
    verdicts = read_jsonl(run_dir / "judge_outbox" / "verdicts.jsonl")
    validate_verdicts(key, verdicts)  # should not raise


def test_unknown_pair_rejected(run_dir):
    key = _write_unanimous_verdicts(run_dir)
    verdicts = read_jsonl(run_dir / "judge_outbox" / "verdicts.jsonl")
    verdicts[0]["pair_id"] = "pr-deadbeef"
    with pytest.raises(IngestError, match="pr-deadbeef"):
        validate_verdicts(key, verdicts)


def test_duplicate_judge_verdict_rejected(run_dir):
    key = _write_unanimous_verdicts(run_dir)
    verdicts = read_jsonl(run_dir / "judge_outbox" / "verdicts.jsonl")
    verdicts.append(dict(verdicts[0]))
    with pytest.raises(IngestError, match="duplicate"):
        validate_verdicts(key, verdicts)


def test_even_verdict_count_rejected(run_dir):
    key = _write_unanimous_verdicts(run_dir)
    verdicts = read_jsonl(run_dir / "judge_outbox" / "verdicts.jsonl")
    extra = dict(verdicts[0])
    extra["judge_id"] = "adv1"
    key["pairs"][extra["pair_id"]]["assignments"]["adv1"] = {"A": "control", "B": "treatment"}
    verdicts.append(extra)
    with pytest.raises(IngestError, match="odd"):
        validate_verdicts(key, verdicts)


def test_missing_pair_coverage_rejected(run_dir):
    key = _write_unanimous_verdicts(run_dir)
    verdicts = read_jsonl(run_dir / "judge_outbox" / "verdicts.jsonl")
    first_pair = verdicts[0]["pair_id"]
    verdicts = [v for v in verdicts if v["pair_id"] != first_pair]
    with pytest.raises(IngestError, match="missing"):
        validate_verdicts(key, verdicts)


def test_score_out_of_range_rejected(run_dir):
    key = _write_unanimous_verdicts(run_dir)
    verdicts = read_jsonl(run_dir / "judge_outbox" / "verdicts.jsonl")
    verdicts[0]["scores"]["depth"]["a"] = 6
    with pytest.raises(IngestError, match="depth"):
        validate_verdicts(key, verdicts)


def test_invalid_winner_rejected(run_dir):
    key = _write_unanimous_verdicts(run_dir)
    verdicts = read_jsonl(run_dir / "judge_outbox" / "verdicts.jsonl")
    verdicts[0]["winner"] = "C"
    with pytest.raises(IngestError, match="winner"):
        validate_verdicts(key, verdicts)


# ── analysis round trip ─────────────────────────────────────────────────────


def test_analyze_run_unanimous_treatment(run_dir):
    _write_unanimous_verdicts(run_dir, winning_arm="treatment")
    domains = {"p001": "coding", "p002": "writing"}
    analysis = analyze_run(run_dir, prompt_domains=domains, bootstrap_iters=200, seed=7)

    assert analysis["headline"]["wins"] == 2
    assert analysis["headline"]["losses"] == 0
    assert analysis["headline"]["ties"] == 0
    assert analysis["headline"]["preference_rate"] == pytest.approx(1.0)
    assert analysis["headline"]["ci95"] == [1.0, 1.0]
    assert analysis["breakdowns"]["by_domain"]["coding"]["treatment_win"] == 1
    assert analysis["breakdowns"]["by_model"]["model-x"]["treatment_win"] == 2
    assert analysis["judge_agreement"] == {"unanimous": 2, "split": 0}
    assert (run_dir / "analysis.json").exists()


def test_analyze_run_control_sweep(run_dir):
    _write_unanimous_verdicts(run_dir, winning_arm="control")
    analysis = analyze_run(run_dir, prompt_domains={}, bootstrap_iters=200, seed=7)
    assert analysis["headline"]["wins"] == 0
    assert analysis["headline"]["losses"] == 2
    assert analysis["headline"]["preference_rate"] == pytest.approx(0.0)


# ── inline judge ────────────────────────────────────────────────────────────


def _valid_judge_json(winner="A"):
    return json.dumps(
        {"winner": winner, "scores": _scores(4, 3), "rationale": "solid", "flags": []}
    )


def test_inline_judge_writes_all_verdicts(run_dir, monkeypatch):
    calls = []

    def fake_chat(api_url, api_key, model, prompt, timeout):
        calls.append(prompt)
        return _valid_judge_json()

    monkeypatch.setattr("rune.bench.judging._chat", fake_chat)
    n = judge_pairs_inline(run_dir, api_url="http://x", api_key="k", model="judge-1", judges=3)
    assert n == 6  # 2 pairs × 3 judges
    verdicts = read_jsonl(run_dir / "judge_outbox" / "verdicts.jsonl")
    assert len(verdicts) == 6
    assert {v["judge_id"] for v in verdicts} == {"j1", "j2", "j3"}
    assert len(calls) == 6


def test_inline_judge_retries_malformed_response(run_dir, monkeypatch):
    responses = iter(["not json at all", _valid_judge_json()] + [_valid_judge_json()] * 10)
    monkeypatch.setattr("rune.bench.judging._chat", lambda *a, **k: next(responses))
    n = judge_pairs_inline(run_dir, api_url="http://x", api_key="k", model="j", judges=1)
    assert n == 2
    verdicts = read_jsonl(run_dir / "judge_outbox" / "verdicts.jsonl")
    assert len(verdicts) == 2


def test_inline_judge_resumes_existing_verdicts(run_dir, monkeypatch):
    monkeypatch.setattr("rune.bench.judging._chat", lambda *a, **k: _valid_judge_json())
    judge_pairs_inline(run_dir, api_url="http://x", api_key="k", model="j", judges=1)
    n = judge_pairs_inline(run_dir, api_url="http://x", api_key="k", model="j", judges=1)
    assert n == 0  # everything already judged
    assert len(read_jsonl(run_dir / "judge_outbox" / "verdicts.jsonl")) == 2


def test_inline_judge_parses_fenced_json(run_dir, monkeypatch):
    fenced = "```json\n" + _valid_judge_json("B") + "\n```"
    monkeypatch.setattr("rune.bench.judging._chat", lambda *a, **k: fenced)
    n = judge_pairs_inline(run_dir, api_url="http://x", api_key="k", model="j", judges=1)
    assert n == 2
    verdicts = read_jsonl(run_dir / "judge_outbox" / "verdicts.jsonl")
    assert all(v["winner"] == "B" for v in verdicts)
