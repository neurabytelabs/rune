"""
🪄 WAND Commands — All subcommands except cast.
inscribe, duel, grimoire, test, validate, forge, stats, cost, config, fuse, version
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

from rune import __version__
from rune.cli.helpers import (
    C, CONFIG, CONFIG_PATH, PROMPTS_DIR,
    print_banner, print_error, print_info, print_meta, print_success, print_warn,
    section, save_result,
    llm_call, enhance_prompt, spinoza_validate, print_spinoza_report,
    get_cost_tracker,
)


def cmd_inscribe(args: argparse.Namespace) -> None:
    """Enhance prompt only — show the enhanced version."""
    print_banner()
    prompt = " ".join(args.prompt)
    model = args.model or CONFIG["model"]

    enhanced = enhance_prompt(prompt, model, args.rune, verbose=True)
    section("📜 Enhanced Prompt (Inscribed)")
    print(f"{C.CYAN}{enhanced}{C.RESET}")

    if args.output:
        Path(args.output).write_text(enhanced, encoding="utf-8")
        print_success(f"Written to {args.output}")

    if args.json:
        print(json.dumps({"user_prompt": prompt, "enhanced_prompt": enhanced}, ensure_ascii=False, indent=2))


def cmd_duel(args: argparse.Namespace) -> None:
    """A/B compare: raw vs enhanced."""
    print_banner()
    prompt = " ".join(args.prompt)
    model = args.model or CONFIG["model"]
    print_meta(f"⚔️  Duel Mode | Model: {model}")

    enhanced = enhance_prompt(prompt, model, args.rune, args.verbose)

    section("🔴 RAW — Running original prompt")
    raw_output = llm_call(prompt, model=model)

    section("🟢 ENHANCED — Running enhanced prompt")
    enhanced_output = llm_call(enhanced, model=model)

    print_meta("\n🔍 Validating both outputs...")
    raw_report = spinoza_validate(raw_output)
    enh_report = spinoza_validate(enhanced_output)

    print_spinoza_report(raw_report, "Raw Output Scores")
    print_spinoza_report(enh_report, "Enhanced Output Scores")

    section("📊 Comparison")
    raw_score = raw_report.get("overall", 0)
    enh_score = enh_report.get("overall", 0)
    diff = enh_score - raw_score
    diff_color = C.GREEN if diff > 0 else C.RED if diff < 0 else C.YELLOW
    print(f"  Raw:      {raw_score:.2f}")
    print(f"  Enhanced: {enh_score:.2f}")
    print(f"  Delta:    {diff_color}{diff:+.2f}{C.RESET}")
    print(f"\n  Raw length:      {len(raw_output)} chars")
    print(f"  Enhanced length: {len(enhanced_output)} chars")

    data = {
        "timestamp": datetime.datetime.now().isoformat(),
        "model": model,
        "user_prompt": prompt,
        "enhanced_prompt": enhanced,
        "raw_output": raw_output,
        "enhanced_output": enhanced_output,
        "raw_spinoza": raw_report,
        "enhanced_spinoza": enh_report,
    }
    fp = save_result(data)
    print_success(f"Saved to {fp}")


def cmd_grimoire(args: argparse.Namespace) -> None:
    """List or search prompt library."""
    print_banner()
    search = " ".join(args.search) if hasattr(args, "search") and args.search else None

    if not PROMPTS_DIR.exists():
        print_warn(f"Prompts directory not found: {PROMPTS_DIR}")
        return

    files = sorted(PROMPTS_DIR.glob("*.md"))
    if not files:
        print_info("No runes found in grimoire.")
        return

    if search:
        search_lower = search.lower()
        filtered = []
        for f in files:
            if search_lower in f.name.lower() or search_lower in f.read_text(encoding="utf-8").lower():
                filtered.append(f)
        files = filtered
        if not files:
            print_info(f"No runes matching '{search}'.")
            return

    section("📚 Grimoire — Rune Library")
    print(f"  {C.BOLD}{'#':<4} {'Name':<35} {'Size':>8}{C.RESET}")
    print(f"  {'─'*4} {'─'*35} {'─'*8}")
    for i, f in enumerate(files, 1):
        size = f.stat().st_size
        name = f.stem
        size_str = f"{size:,}B" if size < 1024 else f"{size/1024:.1f}K"
        print(f"  {C.GRAY}{i:<4}{C.RESET} {C.CYAN}{name:<35}{C.RESET} {C.GRAY}{size_str:>8}{C.RESET}")
    print(f"\n  {C.GRAY}Total: {len(files)} runes{C.RESET}")


def cmd_test(args: argparse.Namespace) -> None:
    """Cross-model benchmark."""
    print_banner()
    prompt = " ".join(args.prompt)
    models = ["gemini-3-pro-preview", "gemini-3-flash-preview", "gpt-4o", "claude-sonnet-4-5", "claude-haiku-4"]
    if args.model:
        models = [args.model]

    enhanced = enhance_prompt(prompt, args.model or CONFIG["model"], args.rune, args.verbose)
    section(f"🧪 Cross-Model Test — {len(models)} models")

    results: List[Dict[str, Any]] = []
    for m in models:
        print(f"\n  {C.BOLD}Testing: {m}{C.RESET}")
        try:
            output = llm_call(enhanced, model=m, stream=False)
            report = spinoza_validate(output)
            score = report.get("overall", 0)
            results.append({"model": m, "score": score, "length": len(output), "output": output, "spinoza": report})
            color = C.GREEN if score >= 0.7 else C.YELLOW if score >= 0.5 else C.RED
            print(f"    {color}Score: {score:.2f}{C.RESET} | Length: {len(output)} chars")
        except Exception as e:
            print_error(f"  {m}: {e}")
            results.append({"model": m, "score": 0, "length": 0, "error": str(e)})

    section("📊 Results")
    print(f"  {C.BOLD}{'Model':<25} {'Score':>8} {'Length':>10}{C.RESET}")
    print(f"  {'─'*25} {'─'*8} {'─'*10}")
    for r in sorted(results, key=lambda x: x["score"], reverse=True):
        color = C.GREEN if r["score"] >= 0.7 else C.YELLOW if r["score"] >= 0.5 else C.RED
        print(f"  {C.CYAN}{r['model']:<25}{C.RESET} {color}{r['score']:>8.2f}{C.RESET} {r['length']:>10}")

    data = {
        "timestamp": datetime.datetime.now().isoformat(),
        "user_prompt": prompt,
        "enhanced_prompt": enhanced,
        "results": results,
    }
    fp = save_result(data)
    print_success(f"Saved to {fp}")


def cmd_validate(args: argparse.Namespace) -> None:
    """Run Spinoza validation on text using local validator (no LLM needed)."""
    print_banner()
    text = " ".join(args.text) if args.text else ""
    if not text:
        if not sys.stdin.isatty():
            text = sys.stdin.read()
        else:
            print_error("No text provided.")
            return

    print_meta(f"Validating {len(text)} characters...")
    try:
        from rune.core.validator import SpinozaValidator
        v = SpinozaValidator()
        report = v.validate(text)
        print(v.format_report(report))
        if args.json:
            from dataclasses import asdict
            print(json.dumps(asdict(report), ensure_ascii=False, indent=2, default=str))
    except ImportError:
        print_warn("Local validator not found, falling back to LLM-based validation...")
        report = spinoza_validate(text)
        print_spinoza_report(report)
        if args.json:
            print(json.dumps(report, ensure_ascii=False, indent=2))


def cmd_forge(args: argparse.Namespace) -> None:
    """Interactive: create new rune template."""
    print_banner()
    section("🔨 Forge — Create New Rune")

    try:
        domain = input(f"  {C.CYAN}Domain{C.RESET} (e.g., coding, writing, analysis): ").strip()
        objective = input(f"  {C.CYAN}Objective{C.RESET} (what should this rune do?): ").strip()
        constraints = input(f"  {C.CYAN}Constraints{C.RESET} (any limits or rules?): ").strip()
        name = input(f"  {C.CYAN}Rune name{C.RESET} (e.g., my_rune): ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nForge cancelled.")
        return

    if not domain or not objective or not name:
        print_error("Domain, objective, and name are required.")
        return

    ts = datetime.datetime.now().strftime("%Y%m%d")
    filename = f"{name}.md"
    content = f"""# 🪄 Rune: {name}
# Created: {ts}
# Domain: {domain}

## Objective
{objective}

## Constraints
{constraints or "None specified."}

## Template

<system>
You are a {domain} expert. Your task is to {objective}.
</system>

<context>
Domain: {domain}
Constraints: {constraints or "None"}
</context>

<instructions>
1. Analyze the user's request carefully.
2. Apply domain expertise in {domain}.
3. Ensure output meets quality standards.
{f"4. Respect constraints: {constraints}" if constraints else ""}
</instructions>

<output>
Format: Structured response with clear sections.
Language: Match user's language.
</output>
"""

    PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
    fp = PROMPTS_DIR / filename
    fp.write_text(content, encoding="utf-8")
    print_success(f"Rune forged: {fp}")


def cmd_stats(args: argparse.Namespace) -> None:
    """Show usage statistics from memory store."""
    print_banner()

    try:
        from rune.memory.store import MemoryStore
        store = MemoryStore(db_path=CONFIG.get("history_db", "~/.rune/history.db"))
        stats = store.get_stats()
        evo_stats = store.get_evolution_stats()
        store.close()

        section("📈 WAND Statistics (from Memory 🧠)")
        print(store.format_stats(stats))

        section("🧬 Evolution Stats")
        print(f"  {C.BOLD}Total evolutions:{C.RESET}    {C.CYAN}{evo_stats['total_evolutions']}{C.RESET}")
        print(f"  {C.BOLD}Unique prompts:{C.RESET}      {C.CYAN}{evo_stats['unique_prompts']}{C.RESET}")
        print(f"  {C.BOLD}Avg score:{C.RESET}            {C.GREEN}{evo_stats['avg_score']:.4f}{C.RESET}")
        print(f"  {C.BOLD}Best score:{C.RESET}           {C.GREEN}{evo_stats['best_score']:.2f}{C.RESET}")
        print(f"  {C.BOLD}Top model:{C.RESET}            {C.CYAN}{evo_stats['top_model']}{C.RESET}")

        if evo_stats['models_used']:
            print(f"\n  {C.BOLD}Models (evolutions):{C.RESET}")
            for m, count in sorted(evo_stats['models_used'].items(), key=lambda x: -x[1]):
                print(f"    {C.CYAN}{m:<25}{C.RESET} {count} evolutions")

        best = store.get_best(5) if hasattr(store, 'get_best') else []
        if best:
            section("🏆 Top 5 Best Prompts")
            for i, r in enumerate(best, 1):
                orig = r['original_text'][:60] + "..." if len(r['original_text']) > 60 else r['original_text']
                print(f"  {C.BOLD}{i}.{C.RESET} {C.GREEN}{r['spinoza_score']:.2f}{C.RESET} | {C.CYAN}{r['model']}{C.RESET} | {orig}")

        return
    except Exception as e:
        print_warn(f"Memory store unavailable ({e}), falling back to file scan...")

    # Fallback: scan output files
    out_dir = Path(CONFIG["output_dir"])
    if not out_dir.exists():
        print_info("No output data yet. Run some spells first!")
        return

    section("📈 WAND Statistics (file scan)")

    total = 0
    models_used: Dict[str, int] = {}
    spinoza_scores: List[float] = []

    for day_dir in sorted(out_dir.iterdir()):
        if not day_dir.is_dir():
            continue
        for f in day_dir.glob("*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                total += 1
                model = data.get("model", "unknown")
                models_used[model] = models_used.get(model, 0) + 1
                for key in ("spinoza", "enhanced_spinoza"):
                    sp = data.get(key, {})
                    if isinstance(sp, dict) and "overall" in sp:
                        spinoza_scores.append(sp["overall"])
                for r in data.get("results", []):
                    if isinstance(r, dict):
                        models_used[r.get("model", "?")] = models_used.get(r.get("model", "?"), 0) + 1
                        if "score" in r:
                            spinoza_scores.append(r["score"])
            except Exception:
                continue

    print(f"  {C.BOLD}Total runs:{C.RESET}         {C.CYAN}{total}{C.RESET}")
    print(f"  {C.BOLD}Output days:{C.RESET}        {C.CYAN}{len(list(out_dir.iterdir()))}{C.RESET}")

    if spinoza_scores:
        avg = sum(spinoza_scores) / len(spinoza_scores)
        color = C.GREEN if avg >= 0.7 else C.YELLOW
        print(f"  {C.BOLD}Avg Spinoza:{C.RESET}        {color}{avg:.2f}{C.RESET} ({len(spinoza_scores)} evaluations)")

    if models_used:
        print(f"\n  {C.BOLD}Models Used:{C.RESET}")
        for m, count in sorted(models_used.items(), key=lambda x: -x[1]):
            print(f"    {C.CYAN}{m:<25}{C.RESET} {count} runs")

    tracker = get_cost_tracker()
    if tracker:
        total_cost = tracker.get_total_cost()
        if total_cost > 0:
            print(f"\n  {C.BOLD}💰 Total API Cost:{C.RESET}  {C.YELLOW}${total_cost:.4f}{C.RESET}")
            breakdown = tracker.get_breakdown()
            for m, info in breakdown.items():
                print(f"    {C.CYAN}{m:<25}{C.RESET} ${info['cost_usd']:.4f} ({info['calls']} calls)")


def cmd_fuse(args: argparse.Namespace) -> None:
    """Fuse multiple prompts into one mega-prompt."""
    print_banner()
    strategy = args.strategy or "layered"

    prompts: List[str] = []
    if args.files:
        for fp in args.files:
            p = Path(fp)
            if not p.exists():
                print_error(f"File not found: {fp}")
                return
            prompts.append(p.read_text(encoding="utf-8").strip())
    elif not sys.stdin.isatty():
        raw = sys.stdin.read().strip()
        parts = re.split(r"\n---\n|\n\n\n+", raw)
        prompts = [p.strip() for p in parts if p.strip()]
    else:
        print_error("Provide prompt files as arguments or pipe via stdin.")
        print_info("Usage: wand fuse prompt1.txt prompt2.txt --strategy layered")
        print_info("  or:  cat prompts.txt | wand fuse --strategy merged")
        return

    if not prompts:
        print_error("No prompts found.")
        return

    print_info(f"🔮 Fusing {len(prompts)} prompts | Strategy: {strategy}")
    for i, p in enumerate(prompts, 1):
        preview = p[:80].replace("\n", " ")
        print(f"  {C.GRAY}#{i}: {preview}{'…' if len(p) > 80 else ''}{C.RESET}")

    try:
        from rune.synthesis.engine import SynthesisEngine
        engine = SynthesisEngine()
        result = engine.fuse(prompts, strategy=strategy, validate=True)
    except Exception as e:
        print_error(f"Fusion failed: {e}")
        return

    section("🔮 Fused Prompt")
    print(f"{C.CYAN}{result.text}{C.RESET}")

    if result.spinoza_report:
        try:
            from rune.core.validator import SpinozaValidator
            v = SpinozaValidator()
            print(f"\n{v.format_report(result.spinoza_report)}")
        except ImportError:
            if result.spinoza_score is not None:
                color = C.GREEN if result.spinoza_score >= 0.6 else C.YELLOW
                print(f"\n  {C.BOLD}Spinoza Score: {color}{result.spinoza_score:.2f}{C.RESET}")

    if args.output:
        Path(args.output).write_text(result.text, encoding="utf-8")
        print_success(f"Output written to {args.output}")

    if args.json:
        data = {
            "strategy": result.strategy,
            "prompt_count": result.prompt_count,
            "spinoza_score": result.spinoza_score,
            "fused_prompt": result.text,
        }
        print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_cost(args: argparse.Namespace) -> None:
    """Show detailed cost report."""
    print_banner()
    tracker = get_cost_tracker()
    if not tracker:
        print_error("Cost tracker not available.")
        return

    total = tracker.get_total_cost()
    if total == 0:
        print_info("No usage recorded yet. Run some spells first!")
        return

    print(tracker.get_daily_report())

    section("💰 All-Time Cost Breakdown")
    breakdown = tracker.get_breakdown()
    print(f"  {C.BOLD}{'Model':<30} {'Calls':>6} {'In Tokens':>12} {'Out Tokens':>12} {'Cost':>10}{C.RESET}")
    print(f"  {'─'*30} {'─'*6} {'─'*12} {'─'*12} {'─'*10}")
    for m, info in breakdown.items():
        print(f"  {C.CYAN}{m:<30}{C.RESET} {info['calls']:>6} {info['input_tokens']:>12,} {info['output_tokens']:>12,} {C.YELLOW}${info['cost_usd']:>9.4f}{C.RESET}")
    print(f"\n  {C.BOLD}Total: {C.YELLOW}${total:.4f}{C.RESET}")

    if args.json:
        print(json.dumps({"total_cost": total, "breakdown": breakdown}, indent=2))


def cmd_config(args: argparse.Namespace) -> None:
    """Show current configuration."""
    print_banner()
    section("⚙️  Current Configuration")
    print(f"  {C.BOLD}Config file:{C.RESET}  {CONFIG_PATH}{' ✓' if CONFIG_PATH.exists() else ' (not found, using defaults)'}")
    print()
    for k, v in CONFIG.items():
        if k == "api_key":
            display = v[:8] + "..." if v and len(v) > 8 else "(not set)" if not v else v
        else:
            display = v
        print(f"  {C.CYAN}{k:<22}{C.RESET} {display}")


def cmd_version(args: argparse.Namespace) -> None:
    """Show version info."""
    print_banner()
    print(f"  {C.BOLD}WAND{C.RESET}     v{__version__}")
    print(f"  {C.BOLD}RUNE{C.RESET}     {CONFIG['template_version']}")
    print(f"  {C.BOLD}Model{C.RESET}    {CONFIG['model']}")
    print(f"  {C.BOLD}API{C.RESET}      {CONFIG['api_url']}")
    print(f"  {C.BOLD}Prompts{C.RESET}  {PROMPTS_DIR}")
    print(f"  {C.BOLD}Outputs{C.RESET}  {CONFIG['output_dir']}")
    print(f"  {C.BOLD}Config{C.RESET}   {CONFIG_PATH}{' ✓' if CONFIG_PATH.exists() else ' (not found)'}")
