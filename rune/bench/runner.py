"""Generation stage: run every prompt through both arms on every model.

What an arm does is defined by its ArmSpec, not hardcoded here — see schemas.py.
The default pair still measures the real runtime path — rune.cli.helpers.enhance_prompt
+ llm_call — exactly as `wand cast` uses it. helpers.llm_call prints and calls sys.exit(1)
on persistent failure, so every cell is wrapped: errors become records, the run
continues, and a rerun resumes from generations.jsonl instead of re-spending.
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Sequence

import rune.cli.helpers as helpers
from rune.bench.schemas import (
    DEFAULT_ARMS,
    ArmSpec,
    PromptRecord,
    append_jsonl,
    arm_to_manifest,
    read_jsonl,
    resolve_config_text,
    validate_arms,
    write_jsonl,
)

COMMAND_TIMEOUT_S = 300


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


def _prefix_text(arm: ArmSpec, base_dir: Path | str | None) -> str:
    """The `system` value of a prefix arm, read from disk when it names a file."""
    return resolve_config_text(arm.config["system"], base_dir, what=f"{arm.arm_id}.config.system")


def _run_command_arm(arm: ArmSpec, prompt_text: str, base_dir: Path | str | None) -> str:
    """Run an external command with the prompt on stdin; stdout is the response."""
    proc = subprocess.run(
        arm.config["cmd"],
        shell=True,
        input=prompt_text,
        capture_output=True,
        text=True,
        timeout=int(arm.config.get("timeout", COMMAND_TIMEOUT_S)),
        cwd=str(base_dir) if base_dir else None,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"command exited {proc.returncode}: {proc.stderr.strip()[-200:] or '(no stderr)'}"
        )
    return proc.stdout


def _run_cell(
    prompt: PromptRecord, model: str, arm: ArmSpec, base_dir: Path | str | None = None
) -> Dict[str, Any]:
    started = datetime.now().isoformat(timespec="seconds")
    t0 = time.monotonic()
    enhanced = None
    output = None
    error = None
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            if arm.kind == "rune_enhance":
                enhanced = helpers.enhance_prompt(
                    prompt.prompt, model, rune_name=arm.config.get("rune")
                )
                output = helpers.llm_call(enhanced, model=model, track=False)
            elif arm.kind == "prefix":
                enhanced = f"{_prefix_text(arm, base_dir).rstrip()}\n\n{prompt.prompt}"
                output = helpers.llm_call(enhanced, model=model, track=False)
            elif arm.kind == "command":
                output = _run_command_arm(arm, prompt.prompt, base_dir)
            else:  # raw
                output = helpers.llm_call(prompt.prompt, model=model, track=False)
    except SystemExit as e:
        error = f"llm_call exited (code {e.code}): {buf.getvalue().strip()[-200:]}"
    except Exception as e:  # noqa: BLE001 — any cell failure must not kill the run
        error = f"{type(e).__name__}: {e}"

    return {
        "gen_id": f"{prompt.prompt_id}|{model}|{arm.arm_id}",
        "prompt_id": prompt.prompt_id,
        "model": model,
        "arm": arm.arm_id,
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
    arms: Sequence[ArmSpec] = DEFAULT_ARMS,
    base_dir: Path | str | None = None,
) -> List[Dict[str, Any]]:
    """Run all cells, appending to generations.jsonl as each completes.

    Cells already present with no error are kept (resume); errored cells re-run.
    Returns the full, final record list.
    """
    validate_arms(arms)
    run_dir = Path(run_dir)
    gen_path = run_dir / "generations.jsonl"
    existing = {r["gen_id"]: r for r in read_jsonl(gen_path)}
    done = {gid: r for gid, r in existing.items() if r.get("error") is None}

    final: Dict[str, Dict[str, Any]] = dict(done)
    total = len(prompts) * len(models) * len(arms)
    cell_no = 0
    for prompt in prompts:
        for model in models:
            for arm in arms:
                cell_no += 1
                gen_id = f"{prompt.prompt_id}|{model}|{arm.arm_id}"
                if gen_id in done:
                    continue
                record = _run_cell(prompt, model, arm, base_dir)
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
    arms: Sequence[ArmSpec] = DEFAULT_ARMS,
    base_dir: Path | str | None = None,
    arms_file: str | None = None,
) -> Dict[str, Any]:
    from rune import __version__

    validate_arms(arms)

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
        "arms": [arm_to_manifest(a, base_dir) for a in arms],
        "seed": seed,
        "config_snapshot": config_snapshot,
        "enhancer": {
            "meta_prompt_sha256": hashlib.sha256(helpers.META_PROMPT.encode()).hexdigest()
        },
        "cells": {"total": n_prompts * len(models) * len(arms)},
        "note": (
            "llm_call does not expose token usage; cost is estimated from char counts. "
            "Benchmark traffic is excluded from ~/.rune/history.db (track=False)."
        ),
    }
    if arms_file:
        manifest["arms_file"] = arms_file
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return manifest
