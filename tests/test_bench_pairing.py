"""Tests for rune.bench.pairing — pair construction and blind per-judge A/B export."""

from __future__ import annotations

import json

from rune.bench.pairing import build_pairs, export_judge_inboxes, make_pair_id
from rune.bench.schemas import DEFAULT_ARMS, ArmSpec, arm_ids, read_jsonl

RUN_ID = "bench-20260704-1200-abc1234"

# The arm ids under test. Kept as names rather than literals so the blindness and
# balance assertions below stay true for any arm pair, not just control/treatment.
ARM_BASELINE, ARM_VARIANT = arm_ids(DEFAULT_ARMS)


def _gen(prompt_id, model, arm, output="some output", error=None):
    return {
        "gen_id": f"{prompt_id}|{model}|{arm}",
        "prompt_id": prompt_id,
        "model": model,
        "arm": arm,
        "enhanced_prompt": "enhanced!" if arm == "treatment" else None,
        "output": output if error is None else None,
        "started_at": "2026-07-04T10:00:00",
        "duration_s": 1.0,
        "chars_out": len(output) if error is None else 0,
        "error": error,
    }


def _full_generations(n_prompts=4, models=("model-x", "model-y")):
    gens = []
    for i in range(1, n_prompts + 1):
        pid = f"p{i:03d}"
        for m in models:
            gens.append(_gen(pid, m, "control", output=f"raw answer {pid} {m}"))
            gens.append(_gen(pid, m, "treatment", output=f"amplified answer {pid} {m}"))
    return gens


def _prompts_by_id(gens):
    return {g["prompt_id"]: f"task prompt for {g['prompt_id']}" for g in gens}


# ── pair construction ───────────────────────────────────────────────────────


def test_build_pairs_one_per_prompt_model():
    pairs = build_pairs(RUN_ID, _full_generations())
    assert len(pairs) == 8  # 4 prompts × 2 models
    assert {(p["prompt_id"], p["model"]) for p in pairs} == {
        (f"p{i:03d}", m) for i in range(1, 5) for m in ("model-x", "model-y")
    }


def test_build_pairs_skips_errored_arm():
    gens = _full_generations()
    gens[0] = _gen("p001", "model-x", "control", error="boom")
    pairs = build_pairs(RUN_ID, gens)
    assert len(pairs) == 7
    assert ("p001", "model-x") not in {(p["prompt_id"], p["model"]) for p in pairs}


def test_pair_id_stable_and_opaque():
    a = make_pair_id(RUN_ID, "p001", "model-x")
    b = make_pair_id(RUN_ID, "p001", "model-x")
    c = make_pair_id(RUN_ID, "p001", "model-y")
    assert a == b
    assert a != c
    assert a.startswith("pr-") and len(a) == 11
    assert "p001" not in a and "model" not in a


# ── export: determinism, blindness, balance ─────────────────────────────────


def test_export_is_deterministic(tmp_path):
    gens = _full_generations()
    prompts = _prompts_by_id(gens)
    d1, d2 = tmp_path / "r1", tmp_path / "r2"
    export_judge_inboxes(d1, RUN_ID, seed=7, generations=gens, prompts=prompts, judges=3)
    export_judge_inboxes(d2, RUN_ID, seed=7, generations=gens, prompts=prompts, judges=3)
    for j in (1, 2, 3):
        f1 = (d1 / "judge_inbox" / f"pairs_j{j}.jsonl").read_bytes()
        f2 = (d2 / "judge_inbox" / f"pairs_j{j}.jsonl").read_bytes()
        assert f1 == f2


def test_export_seed_changes_assignment(tmp_path):
    gens = _full_generations(n_prompts=10)
    prompts = _prompts_by_id(gens)
    d1, d2 = tmp_path / "r1", tmp_path / "r2"
    export_judge_inboxes(d1, RUN_ID, seed=7, generations=gens, prompts=prompts, judges=1)
    export_judge_inboxes(d2, RUN_ID, seed=8, generations=gens, prompts=prompts, judges=1)
    key1 = json.loads((d1 / "pairing_key.json").read_text())
    key2 = json.loads((d2 / "pairing_key.json").read_text())
    a1 = [v["assignments"]["j1"]["A"] for v in key1["pairs"].values()]
    a2 = [v["assignments"]["j1"]["A"] for v in key2["pairs"].values()]
    assert a1 != a2


def test_inbox_records_leak_nothing(tmp_path):
    gens = _full_generations()
    prompts = _prompts_by_id(gens)
    export_judge_inboxes(tmp_path, RUN_ID, seed=7, generations=gens, prompts=prompts, judges=3)
    for j in (1, 2, 3):
        for rec in read_jsonl(tmp_path / "judge_inbox" / f"pairs_j{j}.jsonl"):
            assert set(rec.keys()) == {"pair_id", "task_prompt", "response_a", "response_b"}
            blob = json.dumps(rec)
            # No arm id of this run may appear — asserting only on "treatment" would
            # keep passing for arm pairs like soul_v1/soul_v2 while leaking both.
            for arm_id in (ARM_BASELINE, ARM_VARIANT):
                assert arm_id not in blob
            assert "enhanced" not in blob


def test_inbox_leaks_no_custom_arm_ids(tmp_path):
    """The blindness guarantee has to hold for arbitrary arm ids, not just the default."""
    arms = [
        ArmSpec(arm_id="soul_v1", kind="prefix", config={"system": "policy one"}),
        ArmSpec(arm_id="soul_v2", kind="prefix", config={"system": "policy two"}),
    ]
    gens = []
    for pid in ("p001", "p002"):
        for arm in arms:
            gens.append(_gen(pid, "model-x", arm.arm_id, output=f"answer {pid} {arm.arm_id[-2:]}"))
    export_judge_inboxes(
        tmp_path,
        RUN_ID,
        seed=7,
        generations=gens,
        prompts=_prompts_by_id(gens),
        judges=3,
        arms=arms,
    )
    for j in (1, 2, 3):
        for rec in read_jsonl(tmp_path / "judge_inbox" / f"pairs_j{j}.jsonl"):
            blob = json.dumps(rec)
            for arm in arms:
                assert arm.arm_id not in blob
    key = json.loads((tmp_path / "pairing_key.json").read_text())
    assert key["arms"] == ["soul_v1", "soul_v2"]  # the one unblinding record


def test_ab_assignment_balanced_and_judge_independent(tmp_path):
    gens = _full_generations(n_prompts=30, models=("model-x",))
    prompts = _prompts_by_id(gens)
    export_judge_inboxes(tmp_path, RUN_ID, seed=7, generations=gens, prompts=prompts, judges=3)
    key = json.loads((tmp_path / "pairing_key.json").read_text())["pairs"]
    for j in ("j1", "j2", "j3"):
        arms_as_a = [v["assignments"][j]["A"] for v in key.values()]
        assert 5 <= arms_as_a.count(ARM_VARIANT) <= 25  # not degenerate
    j1_vs_j2 = [v["assignments"]["j1"]["A"] == v["assignments"]["j2"]["A"] for v in key.values()]
    assert not all(j1_vs_j2)  # judges get independent assignments


def test_pairing_key_maps_responses_correctly(tmp_path):
    gens = _full_generations(n_prompts=2, models=("model-x",))
    prompts = _prompts_by_id(gens)
    export_judge_inboxes(tmp_path, RUN_ID, seed=7, generations=gens, prompts=prompts, judges=1)
    key = json.loads((tmp_path / "pairing_key.json").read_text())["pairs"]
    inbox = {r["pair_id"]: r for r in read_jsonl(tmp_path / "judge_inbox" / "pairs_j1.jsonl")}
    outputs = {(g["prompt_id"], g["arm"]): g["output"] for g in gens}
    for pair_id, meta in key.items():
        rec = inbox[pair_id]
        arm_a = meta["assignments"]["j1"]["A"]
        arm_b = meta["assignments"]["j1"]["B"]
        assert rec["response_a"] == outputs[(meta["prompt_id"], arm_a)]
        assert rec["response_b"] == outputs[(meta["prompt_id"], arm_b)]
        assert rec["task_prompt"] == prompts[meta["prompt_id"]]
