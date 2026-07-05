"""Generation stage: run every prompt through both arms on every model.

Measures the real runtime path — rune.cli.helpers.enhance_prompt + llm_call —
exactly as `wand cast` uses it. helpers.llm_call prints and calls sys.exit(1)
on persistent failure, so every cell is wrapped: errors become records, the run
continues, and a rerun resumes from generations.jsonl instead of re-spending.
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import rune.cli.helpers as helpers
from rune.bench.schemas import ARMS, PromptRecord, append_jsonl, read_jsonl, write_jsonl


class RunnerError(RuntimeError):
    """Raised on preflight failures before any money is spent."""


def make_run_id(git_sha: str, stamp: str | None = None) -> str:
    stamp = stamp or datetime.now().strftime("%Y%m%d-%H%M")
    return f"bench-{stamp}-{git_sha[:7]}"


def preflight() -> None:
    if not helpers.CONFIG.get("api_key"):
        raise RunnerError(
            "CONFIG['api_key'] is empty — export RUNE_API_KEY before running "
            "(hint: export RUNE_API_KEY=$GEMINI_API_KEY, see ~/.secrets)"
        )
    if not helpers.CONFIG.get("api_url"):
        raise RunnerError("CONFIG['api_url'] is empty — check ~/.rune/config.toml")


def _run_cell(prompt: PromptRecord, model: str, arm: str) -> Dict[str, Any]:
    started = datetime.now().isoformat(timespec="seconds")
    t0 = time.monotonic()
    enhanced = None
    output = None
    error = None
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            if arm == "treatment":
                enhanced = helpers.enhance_prompt(prompt.prompt, model)
                output = helpers.llm_call(enhanced, model=model, track=False)
            else:
                output = helpers.llm_call(prompt.prompt, model=model, track=False)
    except SystemExit as e:
        error = f"llm_call exited (code {e.code}): {buf.getvalue().strip()[-200:]}"
    except Exception as e:  # noqa: BLE001 — any cell failure must not kill the run
        error = f"{type(e).__name__}: {e}"

    return {
        "gen_id": f"{prompt.prompt_id}|{model}|{arm}",
        "prompt_id": prompt.prompt_id,
        "model": model,
        "arm": arm,
        "enhanced_prompt": enhanced,
        "output": output if error is None else None,
        "started_at": started,
        "duration_s": round(time.monotonic() - t0, 2),
        "chars_out": len(output) if output and error is None else 0,
        "error": error,
    }


def generate(
    run_dir: Path | str,
    prompts: List[PromptRecord],
    models: List[str],
    delay: float = 2.0,
    progress: Any = None,
) -> List[Dict[str, Any]]:
    """Run all cells, appending to generations.jsonl as each completes.

    Cells already present with no error are kept (resume); errored cells re-run.
    Returns the full, final record list.
    """
    run_dir = Path(run_dir)
    gen_path = run_dir / "generations.jsonl"
    existing = {r["gen_id"]: r for r in read_jsonl(gen_path)}
    done = {gid: r for gid, r in existing.items() if r.get("error") is None}

    final: Dict[str, Dict[str, Any]] = dict(done)
    total = len(prompts) * len(models) * len(ARMS)
    cell_no = 0
    for prompt in prompts:
        for model in models:
            for arm in ARMS:
                cell_no += 1
                gen_id = f"{prompt.prompt_id}|{model}|{arm}"
                if gen_id in done:
                    continue
                record = _run_cell(prompt, model, arm)
                final[gen_id] = record
                _rewrite_or_append(gen_path, existing, record)
                if progress:
                    status = "✗" if record["error"] else "✓"
                    progress(f"[{cell_no}/{total}] {status} {gen_id}")
                if delay:
                    time.sleep(delay)

    return list(final.values())


def _rewrite_or_append(
    gen_path: Path, existing: Dict[str, Dict[str, Any]], record: Dict[str, Any]
) -> None:
    """Append new cells; a retried (previously errored) cell rewrites the file once."""
    if record["gen_id"] in existing:
        existing[record["gen_id"]] = record
        write_jsonl(gen_path, list(existing.values()))
    else:
        existing[record["gen_id"]] = record
        append_jsonl(gen_path, record)


def write_manifest(
    run_dir: Path | str,
    run_id: str,
    git_sha: str,
    promptset_path: str,
    promptset_sha: str,
    models: List[str],
    seed: int,
    n_prompts: int,
) -> Dict[str, Any]:
    from rune import __version__

    config_snapshot = dict(helpers.CONFIG)
    if config_snapshot.get("api_key"):
        config_snapshot["api_key"] = "<redacted>"

    manifest = {
        "run_id": run_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "git_sha": git_sha,
        "harness_version": __version__,
        "promptset": {"path": promptset_path, "sha256": promptset_sha, "n": n_prompts},
        "models": models,
        "arms": list(ARMS),
        "seed": seed,
        "config_snapshot": config_snapshot,
        "enhancer": {
            "meta_prompt_sha256": hashlib.sha256(helpers.META_PROMPT.encode()).hexdigest()
        },
        "cells": {"total": n_prompts * len(models) * len(ARMS)},
        "note": (
            "llm_call does not expose token usage; cost is estimated from char counts. "
            "Benchmark traffic is excluded from ~/.rune/history.db (track=False)."
        ),
    }
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return manifest
