"""Tests for rune.bench.report — run report and BENCHMARKS.md rendering."""

from __future__ import annotations

from rune.bench.report import render_benchmarks_md, render_report


def _manifest():
    return {
        "run_id": "bench-20260704-1530-abc1234",
        "created_at": "2026-07-04T15:30:00",
        "git_sha": "abc1234def",
        "harness_version": "2.1.0",
        "promptset": {"path": "benchmark/promptset_v1.jsonl", "sha256": "ff" * 32, "n": 25},
        "models": ["gemini-3.1-pro-preview", "gemini-3-flash-preview"],
        "arms": [
            {"arm_id": "control", "kind": "raw", "config": {}},
            {"arm_id": "treatment", "kind": "rune_enhance", "config": {}},
        ],
        "seed": 7,
        "config_snapshot": {"api_key": "<redacted>", "temperature": 0.7},
        "enhancer": {"meta_prompt_sha256": "aa" * 32},
        "cells": {"total": 100},
        "note": "",
    }


def _analysis():
    return {
        "run_id": "bench-20260704-1530-abc1234",
        "pairs": {},
        "headline": {
            "wins": 31,
            "losses": 12,
            "ties": 7,
            "preference_rate": 31 / 43,
            "ci95": [0.55, 0.85],
            "p_value": 0.0055,
            "n_pairs": 50,
        },
        "criterion_deltas": {
            "task_fulfillment": 0.42,
            "accuracy": 0.1,
            "depth": 0.65,
            "clarity": 0.3,
            "actionability": 0.5,
        },
        "breakdowns": {
            "by_domain": {
                "coding": {"treatment_win": 7, "control_win": 2, "tie": 1},
                "writing": {"treatment_win": 6, "control_win": 3, "tie": 1},
            },
            "by_model": {
                "gemini-3.1-pro-preview": {"treatment_win": 15, "control_win": 7, "tie": 3},
                "gemini-3-flash-preview": {"treatment_win": 16, "control_win": 5, "tie": 4},
            },
        },
        "judge_agreement": {"unanimous": 38, "split": 12},
    }


def test_report_contains_headline_and_diagnostics():
    md = render_report(_manifest(), _analysis())
    assert "72.1%" in md  # preference rate
    assert "[55.0%, 85.0%]" in md  # CI
    assert "p = 0.0055" in md
    assert "31" in md and "12" in md and "7" in md
    assert "label-blind" in md  # limitation section present
    assert "gemini-3.1-pro-preview" in md
    assert "unanimous" in md.lower() or "uyuşma" in md.lower()


def test_report_no_decided_pairs_degrades_gracefully():
    analysis = _analysis()
    analysis["headline"].update(
        {"wins": 0, "losses": 0, "ties": 50, "preference_rate": None, "p_value": 1.0}
    )
    md = render_report(_manifest(), analysis)
    assert "n/a" in md.lower()


def _custom_arm_analysis():
    """The same run shape, but for two prefix arms instead of the default pair."""
    analysis = _analysis()
    analysis["arms"] = {"baseline": "soul_v1", "variant": "soul_v2"}
    for section in analysis["breakdowns"].values():
        for row in section.values():
            row["soul_v2_win"] = row.pop("treatment_win")
            row["soul_v1_win"] = row.pop("control_win")
    return analysis


def test_report_labels_tables_with_arm_ids():
    md = render_report(_manifest(), _custom_arm_analysis())
    assert "| | soul_v2 wins | soul_v1 wins | ties |" in md
    assert "Per-criterion score delta (soul_v2 − soul_v1, 1–5 scale)" in md
    assert "`soul_v2` was preferred over `soul_v1`" in md
    assert "treatment" not in md and "RUNE-amplified" not in md
    assert "72.1%" in md  # the statistics are untouched by the relabelling


def test_report_without_arms_field_reads_as_the_default_pair():
    """Analyses written before arm specs carry no arms field and must still render."""
    md = render_report(_manifest(), _analysis())
    assert "| | treatment wins | control wins | ties |" in md
    assert "RUNE-amplified prompts were preferred" in md


def test_benchmarks_md_names_custom_arms():
    md = render_benchmarks_md(_manifest(), _custom_arm_analysis())
    assert "**soul_v1** and **soul_v2**" in md
    assert "8-layer enhancement" not in md  # methodology must not describe the wrong arms


def test_reproduce_block_carries_the_arms_file():
    manifest = _manifest()
    manifest["arms_file"] = "benchmark/arms/soul-ab.json"
    md = render_report(manifest, _custom_arm_analysis())
    assert "--arms benchmark/arms/soul-ab.json" in md


def test_benchmarks_md_is_honest_and_reproducible():
    md = render_benchmarks_md(_manifest(), _analysis())
    assert "72.1%" in md
    assert "wand bench" in md  # run-it-yourself section
    assert "arXiv" not in md  # no unsourced claims
    assert "45%" not in md  # the old unbacked number must not reappear
    assert "Limitations" in md or "Sınırlar" in md
