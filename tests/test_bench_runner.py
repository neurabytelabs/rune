"""Tests for rune.bench.runner — generation stage with mocked LLM calls."""

from __future__ import annotations

import pytest

import rune.cli.helpers as helpers
from rune.bench.runner import RunnerError, generate, make_run_id, preflight, write_manifest
from rune.bench.schemas import PromptRecord, read_jsonl, write_jsonl


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
    assert manifest["arms"] == ["control", "treatment"]
