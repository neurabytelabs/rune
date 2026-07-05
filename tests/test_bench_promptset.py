"""Tests for rune.bench.schemas JSONL helpers and rune.bench.promptset validation."""

from __future__ import annotations

import hashlib
import json

import pytest

from rune.bench.promptset import PromptSetError, load_promptset, promptset_sha256
from rune.bench.schemas import (
    ARMS,
    DOMAINS,
    RUBRIC_CRITERIA,
    append_jsonl,
    read_jsonl,
    write_jsonl,
)


def _valid_records():
    return [
        {
            "prompt_id": "p001",
            "domain": "coding",
            "lang": "en",
            "source": "historical",
            "length_class": "short",
            "prompt": "explain what a binary search tree is in 3 sentences",
        },
        {
            "prompt_id": "p002",
            "domain": "writing",
            "lang": "tr",
            "source": "authored",
            "length_class": "medium",
            "prompt": "Yapay zeka ajanları hakkında 500 kelimelik bir blog yazısı planla.",
        },
    ]


def _write_promptset(path, records):
    path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n",
        encoding="utf-8",
    )
    return path


# ── schemas: constants ──────────────────────────────────────────────────────


def test_domain_and_arm_constants():
    assert DOMAINS == ("coding", "writing", "analysis", "creative", "research")
    assert ARMS == ("control", "treatment")
    assert RUBRIC_CRITERIA == (
        "task_fulfillment",
        "accuracy",
        "depth",
        "clarity",
        "actionability",
    )


# ── schemas: JSONL helpers ──────────────────────────────────────────────────


def test_jsonl_roundtrip(tmp_path):
    fp = tmp_path / "data.jsonl"
    records = _valid_records()
    write_jsonl(fp, records)
    assert read_jsonl(fp) == records


def test_append_jsonl(tmp_path):
    fp = tmp_path / "data.jsonl"
    write_jsonl(fp, [_valid_records()[0]])
    append_jsonl(fp, _valid_records()[1])
    assert len(read_jsonl(fp)) == 2


def test_read_jsonl_tolerates_trailing_partial_line(tmp_path):
    fp = tmp_path / "data.jsonl"
    full = json.dumps(_valid_records()[0], ensure_ascii=False)
    fp.write_text(full + "\n" + '{"prompt_id": "p9', encoding="utf-8")
    records = read_jsonl(fp)
    assert len(records) == 1
    assert records[0]["prompt_id"] == "p001"


def test_read_jsonl_missing_file_returns_empty(tmp_path):
    assert read_jsonl(tmp_path / "nope.jsonl") == []


def test_read_jsonl_rejects_mid_file_corruption(tmp_path):
    fp = tmp_path / "data.jsonl"
    good = json.dumps(_valid_records()[0], ensure_ascii=False)
    fp.write_text('{"broken": \n' + good + "\n", encoding="utf-8")
    with pytest.raises(ValueError):
        read_jsonl(fp)


# ── promptset: validation ───────────────────────────────────────────────────


def test_load_valid_promptset(tmp_path):
    fp = _write_promptset(tmp_path / "ps.jsonl", _valid_records())
    prompts = load_promptset(fp)
    assert len(prompts) == 2
    assert prompts[0].prompt_id == "p001"
    assert prompts[0].domain == "coding"
    assert prompts[1].lang == "tr"


def test_duplicate_prompt_id_rejected(tmp_path):
    records = _valid_records()
    records[1]["prompt_id"] = "p001"
    fp = _write_promptset(tmp_path / "ps.jsonl", records)
    with pytest.raises(PromptSetError, match="p001"):
        load_promptset(fp)


def test_invalid_domain_rejected(tmp_path):
    records = _valid_records()
    records[0]["domain"] = "cooking"
    fp = _write_promptset(tmp_path / "ps.jsonl", records)
    with pytest.raises(PromptSetError, match="cooking"):
        load_promptset(fp)


def test_empty_prompt_rejected(tmp_path):
    records = _valid_records()
    records[0]["prompt"] = "   "
    fp = _write_promptset(tmp_path / "ps.jsonl", records)
    with pytest.raises(PromptSetError, match="p001"):
        load_promptset(fp)


def test_invalid_length_class_rejected(tmp_path):
    records = _valid_records()
    records[0]["length_class"] = "gigantic"
    fp = _write_promptset(tmp_path / "ps.jsonl", records)
    with pytest.raises(PromptSetError, match="gigantic"):
        load_promptset(fp)


def test_missing_field_rejected(tmp_path):
    records = _valid_records()
    del records[0]["lang"]
    fp = _write_promptset(tmp_path / "ps.jsonl", records)
    with pytest.raises(PromptSetError, match="lang"):
        load_promptset(fp)


def test_committed_promptset_v1_is_valid_and_stratified():
    """Guard for the versioned benchmark prompt set shipped in the repo."""
    from collections import Counter
    from pathlib import Path

    fp = Path(__file__).resolve().parent.parent / "benchmark" / "promptset_v1.jsonl"
    prompts = load_promptset(fp)
    assert len(prompts) == 25
    by_domain = Counter(p.domain for p in prompts)
    assert all(by_domain[d] == 5 for d in DOMAINS)
    turkish = [p for p in prompts if p.lang == "tr"]
    assert 3 <= len(turkish) <= 4


def test_promptset_sha256_matches_file_bytes(tmp_path):
    fp = _write_promptset(tmp_path / "ps.jsonl", _valid_records())
    expected = hashlib.sha256(fp.read_bytes()).hexdigest()
    assert promptset_sha256(fp) == expected
