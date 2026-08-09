"""🪄 WAND Bench — reproducible A/B benchmark: raw vs RUNE-enhanced prompts.

Actions:
    smoke     1-prompt end-to-end dry run (verifies key, endpoint, enhance path)
    generate  run all prompts through both arms on all models (resumable)
    export    write blind per-judge inboxes + pairing key
    judge     inline OpenAI-compat judge (external judges: see JUDGE_PROTOCOL.md)
    ingest    validate verdicts, unblind, compute statistics
    report    render report.md (--publish also regenerates docs/BENCHMARKS.md)
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from rune.cli.helpers import (
    CONFIG,
    WAND_DIR,
    print_error,
    print_info,
    print_meta,
    print_success,
)

RESULTS_DIR = WAND_DIR / "benchmark" / "results"
DEFAULT_PROMPTSET = WAND_DIR / "benchmark" / "promptset_v1.jsonl"
BENCHMARKS_MD = WAND_DIR / "docs" / "BENCHMARKS.md"


def _git_sha() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=WAND_DIR,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if out.returncode == 0:
            return out.stdout.strip()
    except Exception:
        pass
    return "nogit00"


def _resolve_run_dir(args: argparse.Namespace) -> Path:
    if getattr(args, "run", None):
        run_dir = RESULTS_DIR / args.run
        if not run_dir.exists():
            print_error(f"Run not found: {run_dir}")
            sys.exit(1)
        return run_dir
    candidates = sorted(RESULTS_DIR.glob("bench-*")) + sorted(RESULTS_DIR.glob("smoke-*"))
    if not candidates:
        print_error("No runs found — start with: wand bench generate")
        sys.exit(1)
    return max(candidates, key=lambda p: p.stat().st_mtime)


def _load_prompts(args: argparse.Namespace, limit: int | None = None):
    from rune.bench.promptset import load_promptset

    prompts = load_promptset(args.promptset)
    limit = limit or getattr(args, "limit", None)
    return prompts[:limit] if limit else prompts


def _models(args: argparse.Namespace) -> list[str]:
    if getattr(args, "models", None):
        return [m.strip() for m in args.models.split(",") if m.strip()]
    return [CONFIG["model"]]


def _arms(args: argparse.Namespace):
    """Arms for a new run: the --arms file if given, otherwise the default pair."""
    from rune.bench.schemas import DEFAULT_ARMS, ArmSpecError, load_arms

    path = getattr(args, "arms", None)
    if not path:
        return list(DEFAULT_ARMS)
    try:
        return load_arms(path)
    except ArmSpecError as e:
        print_error(str(e))
        sys.exit(1)


def _arms_of_run(manifest: dict):
    """Arms of an existing run, read from its manifest so later stages cannot drift."""
    from rune.bench.schemas import DEFAULT_ARMS, arms_from_manifest

    entries = manifest.get("arms")
    return arms_from_manifest(entries) if entries else list(DEFAULT_ARMS)


def _do_generate(args: argparse.Namespace, smoke: bool = False) -> None:
    from datetime import datetime

    from rune.bench.promptset import promptset_sha256
    from rune.bench.runner import generate, make_run_id, preflight, write_manifest

    preflight()
    prompts = _load_prompts(args, limit=1 if smoke else None)
    models = _models(args)[:1] if smoke else _models(args)
    arms = _arms(args)
    sha = _git_sha()

    if getattr(args, "run", None):
        run_id = args.run  # resume an existing run
    else:
        run_id = make_run_id(git_sha=sha)
        if smoke:
            run_id = "smoke-" + run_id.removeprefix("bench-")
    run_dir = RESULTS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    write_manifest(
        run_dir,
        run_id=run_id,
        git_sha=sha,
        promptset_path=str(Path(args.promptset).relative_to(WAND_DIR))
        if str(args.promptset).startswith(str(WAND_DIR))
        else str(args.promptset),
        promptset_sha=promptset_sha256(args.promptset),
        models=models,
        seed=args.seed,
        n_prompts=len(prompts),
        arms=arms,
        base_dir=WAND_DIR,
        arms_file=getattr(args, "arms", None),
    )
    total = len(prompts) * len(models) * len(arms)
    arm_label = " vs ".join(a.arm_id for a in arms)
    print_info(
        f"🧪 Run {run_id}: {len(prompts)} prompts × {len(models)} models × "
        f"2 arms ({arm_label}) = {total} cells (delay {args.delay}s)"
    )
    started = datetime.now()
    records = generate(
        run_dir,
        prompts,
        models,
        delay=args.delay,
        progress=print_meta,
        arms=arms,
        base_dir=WAND_DIR,
    )
    errors = [r for r in records if r["error"]]
    print_success(
        f"Generation done in {datetime.now() - started}: "
        f"{len(records) - len(errors)} ok, {len(errors)} errored → {run_dir}"
    )
    if errors:
        for r in errors[:5]:
            print_meta(f"  ✗ {r['gen_id']}: {r['error']}")
        print_info("Re-run the same command to retry errored cells (resume).")


def _do_export(args: argparse.Namespace) -> None:
    import json

    from rune.bench.pairing import export_judge_inboxes
    from rune.bench.promptset import load_promptset
    from rune.bench.schemas import read_jsonl

    run_dir = _resolve_run_dir(args)
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    generations = read_jsonl(run_dir / "generations.jsonl")
    prompts = {p.prompt_id: p.prompt for p in load_promptset(args.promptset)}
    pairs = export_judge_inboxes(
        run_dir,
        run_id=manifest["run_id"],
        seed=manifest["seed"],
        generations=generations,
        prompts=prompts,
        judges=args.judges,
        arms=_arms_of_run(manifest),
    )
    print_success(
        f"Exported {len(pairs)} blind pairs × {args.judges} judges → {run_dir / 'judge_inbox'}"
    )
    print_info(
        "External judges: see benchmark/JUDGE_PROTOCOL.md. "
        "Inline judge: wand bench judge --api-url … --model …"
    )


def _do_judge(args: argparse.Namespace) -> None:
    from rune.bench.judging import judge_pairs_inline

    if not args.api_url:
        print_error(
            "--api-url is required for the inline judge "
            "(external judges follow JUDGE_PROTOCOL.md instead)"
        )
        sys.exit(1)
    run_dir = _resolve_run_dir(args)
    import os

    api_key = os.getenv("RUNE_JUDGE_API_KEY") or CONFIG.get("api_key", "")
    n = judge_pairs_inline(
        run_dir,
        api_url=args.api_url,
        api_key=api_key,
        model=args.model or CONFIG["model"],
        judges=args.judges,
        delay=args.delay,
    )
    print_success(f"Inline judge wrote {n} verdicts → {run_dir / 'judge_outbox'}")


def _do_ingest(args: argparse.Namespace) -> None:
    from rune.bench.judging import IngestError, analyze_run
    from rune.bench.promptset import load_promptset

    run_dir = _resolve_run_dir(args)
    domains = {p.prompt_id: p.domain for p in load_promptset(args.promptset)}
    try:
        analysis = analyze_run(run_dir, prompt_domains=domains, seed=args.seed)
    except IngestError as e:
        print_error(f"Ingest failed: {e}")
        sys.exit(1)
    h = analysis["headline"]
    rate = "n/a" if h["preference_rate"] is None else f"{h['preference_rate'] * 100:.1f}%"
    print_success(
        f"Ingested {h['n_pairs']} pairs: {h['wins']}W/{h['losses']}L/{h['ties']}T "
        f"→ preference {rate} (p={h['p_value']:.4g}) → {run_dir / 'analysis.json'}"
    )


def _do_report(args: argparse.Namespace) -> None:
    from rune.bench.report import write_report

    run_dir = _resolve_run_dir(args)
    publish_to = BENCHMARKS_MD if args.publish else None
    write_report(run_dir, publish_to=publish_to)
    print_success(f"Report → {run_dir / 'report.md'}")
    if publish_to:
        print_success(f"Published → {publish_to}")


def cmd_bench(args: argparse.Namespace) -> None:
    if not getattr(args, "promptset", None):
        args.promptset = DEFAULT_PROMPTSET
    actions = {
        "smoke": lambda a: _do_generate(a, smoke=True),
        "generate": _do_generate,
        "export": _do_export,
        "judge": _do_judge,
        "ingest": _do_ingest,
        "report": _do_report,
    }
    actions[args.action](args)
