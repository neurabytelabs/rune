"""Tests for rune.bench.runner — generation stage with mocked LLM calls."""

from __future__ import annotations

import pytest

import rune.cli.helpers as helpers
from rune.bench.runner import RunnerError, generate, make_run_id, preflight, write_manifest
from rune.bench.schemas import ArmSpec, ArmSpecError, PromptRecord, read_jsonl, write_jsonl


def _prompts(n=2):
    return [
        PromptRecord(
            prompt_id=f"p{i:03d}",
            domain="coding",
            lang="en",
            source="authored",
            length_class="short",
            prompt=f"task {i}",
        )
        for i in range(1, n + 1)
    ]


@pytest.fixture
def fake_llm(monkeypatch):
    calls = []

    def llm_call(prompt, model, stream=False, system=None, track=True):
        calls.append({"prompt": prompt, "model": model, "track": track})
        return f"answer to: {prompt[:30]}"

    def enhance_prompt(user_prompt, model, rune_name=None, verbose=False):
        return f"ENHANCED[{user_prompt}]"

    monkeypatch.setattr(helpers, "llm_call", llm_call)
    monkeypatch.setattr(helpers, "enhance_prompt", enhance_prompt)
    return calls


# ── run id / preflight ──────────────────────────────────────────────────────


def test_make_run_id_format():
    rid = make_run_id(git_sha="abc1234def", stamp="20260704-1530")
    assert rid == "bench-20260704-1530-abc1234"


def test_preflight_rejects_missing_api_key(monkeypatch):
    monkeypatch.setitem(helpers.CONFIG, "api_key", "")
    with pytest.raises(RunnerError, match="RUNE_API_KEY"):
        preflight()


def test_preflight_passes_with_key(monkeypatch):
    monkeypatch.setitem(helpers.CONFIG, "api_key", "sk-test")
    preflight()


# ── generation ──────────────────────────────────────────────────────────────


def test_generate_both_arms(tmp_path, fake_llm):
    records = generate(tmp_path, _prompts(2), models=["model-x"], delay=0)
    assert len(records) == 4  # 2 prompts × 1 model × 2 arms

    by_key = {(r["prompt_id"], r["arm"]): r for r in records}
    control = by_key[("p001", "control")]
    treatment = by_key[("p001", "treatment")]
    assert control["enhanced_prompt"] is None
    assert control["output"] == "answer to: task 1"
    assert treatment["enhanced_prompt"] == "ENHANCED[task 1]"
    assert treatment["output"].startswith("answer to: ENHANCED[task 1]"[:20])
    assert all(r["error"] is None for r in records)
    assert len(read_jsonl(tmp_path / "generations.jsonl")) == 4
    # benchmark traffic must not pollute the cost tracker
    assert all(c["track"] is False for c in fake_llm)


def test_generate_survives_systemexit(tmp_path, monkeypatch):
    def llm_call(prompt, model, stream=False, system=None, track=True):
        if "task 1" in prompt:
            raise SystemExit(1)
        return "ok"

    monkeypatch.setattr(helpers, "llm_call", llm_call)
    monkeypatch.setattr(helpers, "enhance_prompt", lambda p, m, **k: f"E[{p}]")

    records = generate(tmp_path, _prompts(2), models=["model-x"], delay=0)
    errored = [r for r in records if r["error"]]
    ok = [r for r in records if r["error"] is None]
    assert len(errored) == 2  # both arms of p001
    assert len(ok) == 2
    assert all(r["output"] is None for r in errored)


def test_generate_resumes_completed_cells(tmp_path, fake_llm):
    existing = {
        "gen_id": "p001|model-x|control",
        "prompt_id": "p001",
        "model": "model-x",
        "arm": "control",
        "enhanced_prompt": None,
        "output": "cached answer",
        "started_at": "2026-07-04T09:00:00",
        "duration_s": 1.0,
        "chars_out": 13,
        "error": None,
    }
    write_jsonl(tmp_path / "generations.jsonl", [existing])

    records = generate(tmp_path, _prompts(1), models=["model-x"], delay=0)
    by_key = {(r["prompt_id"], r["arm"]): r for r in records}
    assert by_key[("p001", "control")]["output"] == "cached answer"  # not re-run
    assert len(fake_llm) == 1  # only the treatment arm's output call (enhance is faked)


def test_generate_retries_errored_cells(tmp_path, fake_llm):
    errored = {
        "gen_id": "p001|model-x|control",
        "prompt_id": "p001",
        "model": "model-x",
        "arm": "control",
        "enhanced_prompt": None,
        "output": None,
        "started_at": "2026-07-04T09:00:00",
        "duration_s": 0.0,
        "chars_out": 0,
        "error": "boom",
    }
    write_jsonl(tmp_path / "generations.jsonl", [errored])

    records = generate(tmp_path, _prompts(1), models=["model-x"], delay=0)
    by_key = {(r["prompt_id"], r["arm"]): r for r in records}
    assert by_key[("p001", "control")]["error"] is None
    assert by_key[("p001", "control")]["output"] == "answer to: task 1"


# ── arm kinds ───────────────────────────────────────────────────────────────


def test_prefix_arms_put_their_system_text_first(tmp_path, fake_llm):
    arms = [
        ArmSpec(arm_id="soul_v1", kind="prefix", config={"system": "POLICY ONE"}),
        ArmSpec(arm_id="soul_v2", kind="prefix", config={"system": "POLICY TWO"}),
    ]
    records = generate(tmp_path, _prompts(1), models=["model-x"], delay=0, arms=arms)

    by_arm = {r["arm"]: r for r in records}
    assert set(by_arm) == {"soul_v1", "soul_v2"}
    assert by_arm["soul_v1"]["enhanced_prompt"] == "POLICY ONE\n\ntask 1"
    assert by_arm["soul_v2"]["enhanced_prompt"] == "POLICY TWO\n\ntask 1"
    assert by_arm["soul_v1"]["gen_id"] == "p001|model-x|soul_v1"
    assert all(r["error"] is None for r in records)


def test_prefix_arm_reads_its_system_file(tmp_path, fake_llm):
    (tmp_path / "soul.md").write_text("FROM FILE", encoding="utf-8")
    arms = [
        ArmSpec(arm_id="a", kind="prefix", config={"system": "soul.md"}),
        ArmSpec(arm_id="b", kind="prefix", config={"system": "INLINE"}),
    ]
    records = generate(
        tmp_path, _prompts(1), models=["model-x"], delay=0, arms=arms, base_dir=tmp_path
    )
    by_arm = {r["arm"]: r for r in records}
    assert by_arm["a"]["enhanced_prompt"] == "FROM FILE\n\ntask 1"


def test_prefix_arm_with_missing_file_errors_the_cell(tmp_path, fake_llm):
    """A typo'd policy path must fail the cell, not silently become the prompt."""
    arms = [
        ArmSpec(arm_id="a", kind="prefix", config={"system": "policies/absent.md"}),
        ArmSpec(arm_id="b", kind="prefix", config={"system": "INLINE"}),
    ]
    records = generate(
        tmp_path, _prompts(1), models=["model-x"], delay=0, arms=arms, base_dir=tmp_path
    )
    by_arm = {r["arm"]: r for r in records}
    assert "looks like a file path" in by_arm["a"]["error"]
    assert by_arm["a"]["output"] is None
    assert by_arm["b"]["error"] is None


def test_command_arm_pipes_prompt_through_stdin(tmp_path, fake_llm):
    arms = [
        ArmSpec(arm_id="raw", kind="raw"),
        ArmSpec(arm_id="upper", kind="command", config={"cmd": "tr '[:lower:]' '[:upper:]'"}),
    ]
    records = generate(tmp_path, _prompts(1), models=["model-x"], delay=0, arms=arms)

    by_arm = {r["arm"]: r for r in records}
    assert by_arm["upper"]["output"] == "TASK 1"
    assert by_arm["raw"]["output"] == "answer to: task 1"
    # a command arm never touches the LLM path
    assert len(fake_llm) == 1


def test_command_arm_failure_becomes_a_cell_error(tmp_path, fake_llm):
    arms = [
        ArmSpec(arm_id="ok", kind="raw"),
        ArmSpec(arm_id="broken", kind="command", config={"cmd": "echo nope >&2; exit 3"}),
    ]
    records = generate(tmp_path, _prompts(1), models=["model-x"], delay=0, arms=arms)
    broken = next(r for r in records if r["arm"] == "broken")
    assert "exited 3" in broken["error"]
    assert "nope" in broken["error"]


def test_rune_enhance_arm_passes_its_template(tmp_path, monkeypatch):
    seen = {}

    def enhance_prompt(user_prompt, model, rune_name=None, verbose=False):
        seen["rune_name"] = rune_name
        return f"E[{user_prompt}]"

    monkeypatch.setattr(helpers, "enhance_prompt", enhance_prompt)
    monkeypatch.setattr(
        helpers, "llm_call", lambda prompt, model, stream=False, system=None, track=True: "ok"
    )
    arms = [
        ArmSpec(arm_id="control", kind="raw"),
        ArmSpec(arm_id="tuned", kind="rune_enhance", config={"rune": "architect"}),
    ]
    generate(tmp_path, _prompts(1), models=["model-x"], delay=0, arms=arms)
    assert seen["rune_name"] == "architect"


def test_generate_rejects_three_arms(tmp_path, fake_llm):
    arms = [ArmSpec(arm_id=f"a{i}", kind="raw") for i in range(3)]
    with pytest.raises(ArmSpecError, match="not an arbitrary cap"):
        generate(tmp_path, _prompts(1), models=["model-x"], delay=0, arms=arms)


# ── manifest ────────────────────────────────────────────────────────────────


def test_manifest_redacts_api_key(tmp_path, monkeypatch):
    monkeypatch.setitem(helpers.CONFIG, "api_key", "sk-super-secret")
    manifest = write_manifest(
        tmp_path,
        run_id="bench-20260704-1530-abc1234",
        git_sha="abc1234def",
        promptset_path="benchmark/promptset_v1.jsonl",
        promptset_sha="ff" * 32,
        models=["model-x"],
        seed=7,
        n_prompts=25,
    )
    raw = (tmp_path / "manifest.json").read_text()
    assert "sk-super-secret" not in raw
    assert manifest["config_snapshot"]["api_key"] == "<redacted>"
    assert manifest["enhancer"]["meta_prompt_sha256"]
    assert manifest["git_sha"] == "abc1234def"
    assert [a["arm_id"] for a in manifest["arms"]] == ["control", "treatment"]
    assert [a["kind"] for a in manifest["arms"]] == ["raw", "rune_enhance"]
    assert all("config" in a for a in manifest["arms"])
