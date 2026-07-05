"""Pair construction and blind, per-judge A/B anonymization.

Blindness model: judges see only {pair_id, task_prompt, response_a, response_b}.
Which arm is "A" is decided by a seeded coin flip drawn independently per judge
slot, so no judge's assignment reveals another's. The only unblinding record is
pairing_key.json, which judges must never read.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List

from rune.bench.schemas import write_jsonl


def make_pair_id(run_id: str, prompt_id: str, model: str) -> str:
    digest = hashlib.sha256(f"{run_id}|{prompt_id}|{model}".encode()).hexdigest()
    return f"pr-{digest[:8]}"


def build_pairs(run_id: str, generations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """One pair per (prompt_id, model) where both arms produced output."""
    ok: Dict[tuple, Dict[str, Any]] = {}
    for g in generations:
        if g.get("error") is None and g.get("output"):
            ok[(g["prompt_id"], g["model"], g["arm"])] = g

    pairs = []
    keys = sorted({(pid, m) for pid, m, _ in ok})
    for prompt_id, model in keys:
        if (prompt_id, model, "control") in ok and (prompt_id, model, "treatment") in ok:
            pairs.append(
                {
                    "pair_id": make_pair_id(run_id, prompt_id, model),
                    "prompt_id": prompt_id,
                    "model": model,
                }
            )
    return pairs


def _arm_as_a(seed: int, judge_slot: str, pair_id: str) -> str:
    digest = hashlib.sha256(f"{seed}|{judge_slot}|{pair_id}".encode()).digest()
    return "control" if digest[0] % 2 == 0 else "treatment"


def export_judge_inboxes(
    run_dir: Path | str,
    run_id: str,
    seed: int,
    generations: List[Dict[str, Any]],
    prompts: Dict[str, str],
    judges: int = 3,
) -> List[Dict[str, Any]]:
    """Write judge_inbox/pairs_j{n}.jsonl (blind) + pairing_key.json (unblinding).

    Args:
        run_dir: benchmark/results/<run_id> directory.
        prompts: prompt_id -> original task prompt text.

    Returns:
        The pair list (for logging/inspection).
    """
    run_dir = Path(run_dir)
    pairs = build_pairs(run_id, generations)
    outputs = {
        (g["prompt_id"], g["model"], g["arm"]): g["output"]
        for g in generations
        if g.get("error") is None and g.get("output")
    }

    key: Dict[str, Any] = {"run_id": run_id, "seed": seed, "judges": judges, "pairs": {}}
    inboxes: Dict[str, List[Dict[str, Any]]] = {f"j{n}": [] for n in range(1, judges + 1)}

    for pair in pairs:
        pid, model, pair_id = pair["prompt_id"], pair["model"], pair["pair_id"]
        assignments = {}
        for slot in inboxes:
            arm_a = _arm_as_a(seed, slot, pair_id)
            arm_b = "treatment" if arm_a == "control" else "control"
            assignments[slot] = {"A": arm_a, "B": arm_b}
            inboxes[slot].append(
                {
                    "pair_id": pair_id,
                    "task_prompt": prompts[pid],
                    "response_a": outputs[(pid, model, arm_a)],
                    "response_b": outputs[(pid, model, arm_b)],
                }
            )
        key["pairs"][pair_id] = {"prompt_id": pid, "model": model, "assignments": assignments}

    for slot, records in inboxes.items():
        write_jsonl(run_dir / "judge_inbox" / f"pairs_{slot}.jsonl", records)

    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "pairing_key.json").write_text(
        json.dumps(key, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return pairs
