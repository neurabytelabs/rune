"""Tests for arm specs — the two-arm contract, arm files, and config pinning.

An arm is one side of the blind A/B. These tests cover the parts that decide whether
a run means anything: that exactly two arms are enforced, that a mistyped policy path
fails loudly instead of becoming the system prompt, and that file-backed config is
pinned by digest in the manifest.
"""

from __future__ import annotations

import hashlib
import json

import pytest

from rune.bench.schemas import (
    DEFAULT_ARMS,
    ArmSpec,
    ArmSpecError,
    arm_ids,
    arm_to_manifest,
    arms_from_manifest,
    load_arms,
    resolve_config_text,
    validate_arms,
)

REPO_ARMS = ("benchmark/arms/default.json", "benchmark/arms/soul-ab.json")


def _write_arms(tmp_path, arms, name="arms.json"):
    path = tmp_path / name
    path.write_text(json.dumps({"arms": arms}), encoding="utf-8")
    return path


# ── the two-arm contract ────────────────────────────────────────────────────


def test_defaults_are_valid():
    validate_arms(DEFAULT_ARMS)
    assert arm_ids(DEFAULT_ARMS) == ["control", "treatment"]


@pytest.mark.parametrize("n", [0, 1, 3, 4])
def test_arm_count_must_be_exactly_two(n):
    arms = [ArmSpec(arm_id=f"a{i}", kind="raw") for i in range(n)]
    with pytest.raises(ArmSpecError) as exc:
        validate_arms(arms)
    assert f"got {n}" in str(exc.value)


def test_arm_count_error_explains_why_it_is_not_arbitrary():
    """A bare limit invites the next reader to raise it; the reason has to travel with it."""
    arms = [ArmSpec(arm_id=f"a{i}", kind="raw") for i in range(3)]
    with pytest.raises(ArmSpecError) as exc:
        validate_arms(arms)
    message = str(exc.value)
    assert "not an arbitrary cap" in message
    assert "binomial sign test" in message
    assert "multiple-comparison" in message
    assert "N-1 separate two-arm benchmarks" in message


def test_duplicate_arm_ids_rejected():
    arms = [ArmSpec(arm_id="a", kind="raw"), ArmSpec(arm_id="a", kind="raw")]
    with pytest.raises(ArmSpecError, match="unique"):
        validate_arms(arms)


def test_unknown_kind_rejected():
    arms = [ArmSpec(arm_id="a", kind="raw"), ArmSpec(arm_id="b", kind="telepathy")]
    with pytest.raises(ArmSpecError, match="unknown kind"):
        validate_arms(arms)


def test_arm_id_with_pipe_rejected():
    """gen_id is prompt_id|model|arm_id — a pipe in an arm id would corrupt every record."""
    arms = [ArmSpec(arm_id="a", kind="raw"), ArmSpec(arm_id="b|c", kind="raw")]
    with pytest.raises(ArmSpecError, match="invalid arm_id"):
        validate_arms(arms)


@pytest.mark.parametrize("kind,key", [("prefix", "system"), ("command", "cmd")])
def test_kind_requires_its_config(kind, key):
    arms = [ArmSpec(arm_id="a", kind="raw"), ArmSpec(arm_id="b", kind=kind)]
    with pytest.raises(ArmSpecError, match=f"requires config.{key}"):
        validate_arms(arms)


# ── arm files ───────────────────────────────────────────────────────────────


def test_load_arms_roundtrip(tmp_path):
    path = _write_arms(
        tmp_path,
        [
            {"arm_id": "soul_v1", "kind": "prefix", "config": {"system": "be brief"}},
            {"arm_id": "soul_v2", "kind": "prefix", "config": {"system": "be thorough"}},
        ],
    )
    arms = load_arms(path)
    assert arm_ids(arms) == ["soul_v1", "soul_v2"]
    assert arms[1].config["system"] == "be thorough"


def test_load_arms_accepts_bare_list(tmp_path):
    path = tmp_path / "arms.json"
    path.write_text(
        json.dumps([{"arm_id": "a", "kind": "raw"}, {"arm_id": "b", "kind": "rune_enhance"}]),
        encoding="utf-8",
    )
    assert arm_ids(load_arms(path)) == ["a", "b"]


def test_load_arms_rejects_three(tmp_path):
    path = _write_arms(tmp_path, [{"arm_id": f"a{i}", "kind": "raw"} for i in range(3)])
    with pytest.raises(ArmSpecError, match="not an arbitrary cap"):
        load_arms(path)


def test_load_arms_rejects_unknown_field(tmp_path):
    path = _write_arms(
        tmp_path,
        [{"arm_id": "a", "kind": "raw", "weight": 2}, {"arm_id": "b", "kind": "raw"}],
    )
    with pytest.raises(ArmSpecError, match="unknown arm field"):
        load_arms(path)


def test_missing_arm_file_is_an_error(tmp_path):
    with pytest.raises(ArmSpecError, match="not found"):
        load_arms(tmp_path / "nope.json")


@pytest.mark.parametrize("relpath", REPO_ARMS)
def test_committed_arm_files_load(relpath):
    """The shipped examples must actually run, including their referenced policy files."""
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[1]
    arms = load_arms(repo_root / relpath)
    assert len(arms) == 2
    for arm in arms:
        if arm.kind == "prefix":
            assert resolve_config_text(arm.config["system"], repo_root).strip()


# ── config resolution and pinning ───────────────────────────────────────────


def test_inline_text_stays_inline(tmp_path):
    assert resolve_config_text("You are a careful assistant.", tmp_path) == (
        "You are a careful assistant."
    )


def test_file_backed_value_is_read(tmp_path):
    policy = tmp_path / "soul.md"
    policy.write_text("be exact", encoding="utf-8")
    assert resolve_config_text("soul.md", tmp_path) == "be exact"


def test_pathish_value_with_no_file_raises(tmp_path):
    """The silent-failure case: a typo'd path must not become the system prompt."""
    with pytest.raises(ArmSpecError, match="looks like a file path"):
        resolve_config_text("policies/soul_v9.md", tmp_path)


def test_multiline_text_is_never_probed_as_a_path(tmp_path):
    text = "line one\nline two"
    assert resolve_config_text(text, tmp_path) == text


def test_manifest_pins_file_backed_config(tmp_path):
    policy = tmp_path / "soul.md"
    policy.write_text("be exact", encoding="utf-8")
    arm = ArmSpec(arm_id="soul_v1", kind="prefix", config={"system": "soul.md"})

    entry = arm_to_manifest(arm, tmp_path)
    assert entry["config"]["system"] == "soul.md"  # recorded as written, stays portable
    assert entry["config_files"]["system"]["sha256"] == hashlib.sha256(b"be exact").hexdigest()


def test_manifest_omits_digests_for_inline_config(tmp_path):
    arm = ArmSpec(arm_id="soul_v1", kind="prefix", config={"system": "be exact"})
    assert "config_files" not in arm_to_manifest(arm, tmp_path)


def test_manifest_digest_changes_with_file_contents(tmp_path):
    policy = tmp_path / "soul.md"
    arm = ArmSpec(arm_id="soul_v1", kind="prefix", config={"system": "soul.md"})

    policy.write_text("v1", encoding="utf-8")
    first = arm_to_manifest(arm, tmp_path)["config_files"]["system"]["sha256"]
    policy.write_text("v2", encoding="utf-8")
    second = arm_to_manifest(arm, tmp_path)["config_files"]["system"]["sha256"]
    assert first != second


# ── replaying older runs ────────────────────────────────────────────────────


def test_arms_from_legacy_manifest_strings():
    """Manifests written before arm specs stored plain arm_id strings."""
    arms = arms_from_manifest(["control", "treatment"])
    assert arm_ids(arms) == ["control", "treatment"]
    assert [a.kind for a in arms] == ["raw", "rune_enhance"]


def test_arms_from_current_manifest_entries():
    entries = [
        {"arm_id": "soul_v1", "kind": "prefix", "config": {"system": "a"}},
        {"arm_id": "soul_v2", "kind": "prefix", "config": {"system": "b"}},
    ]
    arms = arms_from_manifest(entries)
    assert arm_ids(arms) == ["soul_v1", "soul_v2"]
    assert arms[0].config == {"system": "a"}
