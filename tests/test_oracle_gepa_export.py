"""Tests for RUNE lineage export into GEPA-viz run.json shape."""

import json

from rune.core.oracle import Oracle


def test_export_gepa_run_writes_candidates_with_parent(tmp_path):
    oracle = Oracle(lineage_dir=tmp_path)
    parent = oracle.create_lineage(
        original_prompt="Write a product brief",
        enhanced_prompt="L0 role\nL1 context\nL2 intent",
        model="test-model",
        spinoza_score=0.71,
        grade="B-",
    )
    child = oracle.create_lineage(
        original_prompt="Write a product brief with clearer constraints",
        enhanced_prompt="L0 role\nL1 context\nL2 intent\nL3 governance",
        model="test-model",
        spinoza_score=0.84,
        grade="B+",
        parent_id=parent.id,
        refinement_round=1,
        strategy="oracle-refined",
    )

    out = tmp_path / "run.json"
    run = oracle.export_gepa_run(child.id, output_path=out)

    assert out.exists()
    loaded = json.loads(out.read_text())
    assert loaded == run
    assert set(run.keys()) == {"examples", "candidates"}
    assert len(run["examples"]) == 2
    assert len(run["candidates"]) == 2
    assert run["candidates"]["0"]["parent"] is None
    assert run["candidates"]["1"]["parent"] == "0"
    assert run["candidates"]["1"]["score"] == 0.84
    assert run["candidates"]["1"]["predictions"][0]["prediction"]["lineage_id"] == child.id
    assert "refinement round: 1" in run["candidates"]["1"]["minibatch"][0]["feedback"]


def test_export_gepa_run_empty_lineage_is_valid_shape(tmp_path):
    oracle = Oracle(lineage_dir=tmp_path)
    run = oracle.export_gepa_run(output_path=tmp_path / "empty.json")

    assert run == {"examples": [], "candidates": {}}
