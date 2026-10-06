"""End-to-end pass over all five stages with two arbitrary arms.

Every other test file covers one stage. This one is the only place the stages are
checked against each other: that generate → export → judge → ingest → report agree
on arm ids the harness has never seen before, and that the arm labels reach the
report while never reaching a judge. Both the LLM and the judge endpoint are faked,
so the whole pipeline runs offline and deterministically.
"""

from __future__ import annotations

import hashlib
import json

import pytest

import rune.cli.helpers as helpers
from rune.bench.judging import analyze_run, judge_pairs_inline
from rune.bench.pairing import export_judge_inboxes
from rune.bench.report import write_report
from rune.bench.runner import generate, write_manifest
from rune.bench.schemas import ArmSpec, PromptRecord, read_jsonl

RUN_ID = "bench-20260727-1200-abc1234"

ARMS = [
    ArmSpec(arm_id="soul_v1", kind="prefix", config={"system": "POLICY ONE"}),
    ArmSpec(arm_id="soul_v2", kind="prefix", config={"system": "policies/soul_v2.md"}),
]

PROMPTS = [
    PromptRecord(
        prompt_id=f"p{i:03d}",
        domain=domain,
        lang="en",
        source="authored",
        length_class="short",
        prompt=f"task {i}",
    )
    for i, domain in enumerate(("coding", "writing", "analysis"), start=1)
]


@pytest.fixture
def run_dir(tmp_path, monkeypatch):
    """A full run over two prefix arms, generated and judged against fakes."""
    (tmp_path / "policies").mkdir()
    (tmp_path / "policies" / "soul_v2.md").write_text("POLICY TWO", encoding="utf-8")

    def llm_call(prompt, model, stream=False, system=None, track=True):
        # The response carries which policy produced it, so the judge fake below can
        # decide a winner the same way a real judge would — from the text alone.
        return f"answer produced under {prompt.splitlines()[0]}"

    monkeypatch.setattr(helpers, "llm_call", llm_call)
    monkeypatch.setitem(helpers.CONFIG, "api_key", "sk-test")

    write_manifest(
        tmp_path,
        run_id=RUN_ID,
        git_sha="abc1234def",
        promptset_path="benchmark/promptset_v1.jsonl",
        promptset_sha="ff" * 32,
        models=["model-x"],
        seed=7,
        n_prompts=len(PROMPTS),
        arms=ARMS,
        base_dir=tmp_path,
        arms_file="benchmark/arms/soul-ab.json",
    )
    generations = generate(
        tmp_path, PROMPTS, models=["model-x"], delay=0, arms=ARMS, base_dir=tmp_path
    )
    export_judge_inboxes(
        tmp_path,
        RUN_ID,
        seed=7,
        generations=generations,
        prompts={p.prompt_id: p.prompt for p in PROMPTS},
        judges=3,
        arms=ARMS,
    )

    def fake_chat(api_url, api_key, model, prompt, timeout):
        """Always prefer the response that came from POLICY TWO, whichever side it is on."""
        response_a = prompt.split("RESPONSE A:")[1].split("RESPONSE B:")[0]
        winner = "A" if "POLICY TWO" in response_a else "B"
        scores = {
            c: {"a": 4 if winner == "A" else 2, "b": 2 if winner == "A" else 4}
            for c in ("task_fulfillment", "accuracy", "depth", "clarity", "actionability")
        }
        return json.dumps({"winner": winner, "scores": scores, "rationale": "", "flags": []})

    monkeypatch.setattr("rune.bench.judging._chat", fake_chat)
    judge_pairs_inline(tmp_path, api_url="http://x", api_key="k", model="judge-1", judges=3)
    return tmp_path


def test_pipeline_runs_end_to_end_on_two_prefix_arms(run_dir):
    generations = read_jsonl(run_dir / "generations.jsonl")
    assert len(generations) == 6  # 3 prompts × 1 model × 2 arms
    assert all(g["error"] is None for g in generations)
    assert {g["arm"] for g in generations} == {"soul_v1", "soul_v2"}
    assert {g["gen_id"] for g in generations} == {
        f"p{i:03d}|model-x|{arm}" for i in (1, 2, 3) for arm in ("soul_v1", "soul_v2")
    }

    analysis = analyze_run(run_dir, prompt_domains={p.prompt_id: p.domain for p in PROMPTS})
    assert analysis["arms"] == {"baseline": "soul_v1", "variant": "soul_v2"}
    # The judge fake always prefers POLICY TWO, so soul_v2 must sweep — if the A/B
    # unblinding were wrong this would come out reversed rather than merely noisy.
    assert analysis["headline"]["wins"] == 3
    assert analysis["headline"]["losses"] == 0
    assert analysis["headline"]["preference_rate"] == pytest.approx(1.0)
    assert analysis["judge_agreement"] == {"unanimous": 3, "split": 0}
    assert analysis["criterion_deltas"]["accuracy"] == pytest.approx(2.0)

    report = write_report(run_dir)
    assert "| | soul_v2 wins | soul_v1 wins | ties |" in report
    assert "`soul_v2` was preferred over `soul_v1`" in report
    assert "--arms benchmark/arms/soul-ab.json" in report


def test_judges_never_saw_an_arm_id(run_dir):
    """Blindness across the whole pipeline: pairing_key.json is the only unblinding record."""
    for slot in ("j1", "j2", "j3"):
        blob = (run_dir / "judge_inbox" / f"pairs_{slot}.jsonl").read_text()
        for arm in ARMS:
            assert arm.arm_id not in blob
    assert "soul_v1" in (run_dir / "pairing_key.json").read_text()


def test_manifest_pins_the_policy_file_it_ran(run_dir):
    """A run that points at a policy file is only reproducible if the file is pinned."""
    manifest = json.loads((run_dir / "manifest.json").read_text())
    by_id = {a["arm_id"]: a for a in manifest["arms"]}

    assert by_id["soul_v2"]["config_files"]["system"]["path"] == "policies/soul_v2.md"
    assert by_id["soul_v2"]["config_files"]["system"]["sha256"] == (
        hashlib.sha256(b"POLICY TWO").hexdigest()
    )
    # An inline policy has nothing to pin — the text is already in the manifest.
    assert "config_files" not in by_id["soul_v1"]
    assert by_id["soul_v1"]["config"]["system"] == "POLICY ONE"
    assert manifest["cells"]["total"] == 6
