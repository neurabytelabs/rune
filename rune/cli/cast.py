"""
🪄 WAND Cast — Interactive prompt enhancement + execution.
The primary command of WAND CLI.
"""

from __future__ import annotations

import argparse
import datetime
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

from rune.cli.helpers import (
    C, CONFIG, PROMPTS_DIR,
    print_banner, print_error, print_info, print_meta, print_success, print_warn,
    section, save_result,
    llm_call, enhance_prompt, spinoza_validate, print_spinoza_report,
    detect_intent,
)


# ──────────────────────────────────────────────
# Interactive Q&A
# ──────────────────────────────────────────────
def _interactive_qa(intent: Dict[str, Any], model: str) -> Dict[str, str]:
    """Compact or step-by-step interactive Q&A based on complexity."""
    answers: Dict[str, str] = {}
    domain = intent["domain"]
    lang = intent["lang"]
    is_tr = (lang == "tr")

    questions: Dict[str, List[Dict[str, Any]]] = {
        "WRITING": [
            {"key": "audience", "label": "Hedef kitle?" if is_tr else "Audience?",
             "options": [("Developer", "technical"), ("Genel", "general"), ("C-level", "business")], "custom": True},
            {"key": "tone", "label": "Ton?" if is_tr else "Tone?",
             "options": [("Teknik", "academic"), ("Blog", "conversational"), ("Manifesto", "provocative"), ("Tutorial", "tutorial")], "custom": True},
            {"key": "length", "label": "Uzunluk?" if is_tr else "Length?",
             "options": [("~500", "short"), ("~1500", "medium"), ("~3000+", "long")], "custom": False},
        ],
        "CODING": [
            {"key": "language", "label": "Dil?" if is_tr else "Language?",
             "options": [("Python", "python"), ("TypeScript", "typescript"), ("Elixir", "elixir"), ("Rust", "rust")], "custom": True},
            {"key": "scope", "label": "Kapsam?" if is_tr else "Scope?",
             "options": [("Snippet", "snippet"), ("Module", "module"), ("Project", "project")], "custom": False},
        ],
        "CREATIVE": [
            {"key": "style", "label": "Stil?" if is_tr else "Style?",
             "options": [("Minimalist", "minimalist"), ("Dark fantasy", "dark_fantasy"), ("Retro", "retro"), ("Modern", "modern")], "custom": True},
        ],
        "ANALYSIS": [
            {"key": "depth", "label": "Derinlik?" if is_tr else "Depth?",
             "options": [("Ozet", "quick"), ("Detayli", "detailed"), ("Karsilastirmali", "comparative")], "custom": False},
        ],
    }

    q_set = questions.get(domain, [
        {"key": "goal", "label": "Hedef?" if is_tr else "Goal?",
         "options": [("Bilgi", "info"), ("Karar", "decision"), ("Yaratici", "creative")], "custom": True},
    ])

    sep = C.MAGENTA + "\u2500" * 40 + C.RESET
    print("\n" + sep)
    print(C.BOLD + "\U0001f52e Spell Analysis" + C.RESET)
    print(C.GRAY + "Domain: " + domain + " | Lang: " + lang.upper() + C.RESET)
    print(sep + "\n")

    is_compact = len(q_set) <= 3

    if is_compact:
        for i, q in enumerate(q_set, 1):
            opt_str = "  ".join(chr(96 + j + 1) + ") " + text for j, (text, _) in enumerate(q["options"]))
            if q.get("custom"):
                opt_str += "  " + chr(96 + len(q["options"]) + 1) + ") " + ("Ozel..." if is_tr else "Custom...")
            print(C.BOLD + str(i) + ") " + q["label"] + C.RESET)
            print("   " + opt_str)
        example = " ".join(str(i + 1) + "a" for i in range(len(q_set)))
        print("\n" + C.GRAY + ("Ornek" if is_tr else "Example") + ": " + example + C.RESET)

        while True:
            try:
                raw = input("\n" + C.GREEN + "\u25b8 " + C.RESET).strip()
                if not raw:
                    for q in q_set:
                        answers[q["key"]] = q["options"][0][1]
                    break

                import re
                parts = re.findall(r"(\d+)\s*([a-z])", raw.lower().replace(",", " "))
                if parts:
                    for num_str, letter in parts:
                        idx = int(num_str) - 1
                        opt_idx = ord(letter) - ord("a")
                        if 0 <= idx < len(q_set):
                            q = q_set[idx]
                            if 0 <= opt_idx < len(q["options"]):
                                answers[q["key"]] = q["options"][opt_idx][1]
                            elif q.get("custom") and opt_idx == len(q["options"]):
                                custom = input("  " + C.GREEN + "\u25b8 " + q["label"] + " " + C.RESET).strip()
                                answers[q["key"]] = custom or q["options"][0][1]
                    for q in q_set:
                        if q["key"] not in answers:
                            answers[q["key"]] = q["options"][0][1]
                    break
                else:
                    print(C.RED + ("Ornek: 1a 2b" if is_tr else "Example: 1a 2b") + C.RESET)
            except (EOFError, KeyboardInterrupt):
                print("\n" + C.YELLOW + "Cancelled." + C.RESET)
                sys.exit(130)
    else:
        for q in q_set:
            print(C.BOLD + q["label"] + C.RESET)
            for i, (text, _) in enumerate(q["options"], 1):
                print("  " + C.CYAN + str(i) + ")" + C.RESET + " " + text)
            if q.get("custom"):
                print("  " + C.CYAN + str(len(q["options"]) + 1) + ")" + C.RESET + " " + ("Ozel..." if is_tr else "Custom..."))

            while True:
                try:
                    choice = input("\n  " + C.GREEN + "\u25b8" + C.RESET + " ").strip()
                    if not choice:
                        answers[q["key"]] = q["options"][0][1]
                        print("  " + C.GRAY + "\u2192 " + q["options"][0][0] + C.RESET)
                        break
                    try:
                        idx = int(choice) - 1
                    except ValueError:
                        answers[q["key"]] = choice
                        break
                    if 0 <= idx < len(q["options"]):
                        answers[q["key"]] = q["options"][idx][1]
                        print("  " + C.GRAY + "\u2192 " + q["options"][idx][0] + C.RESET)
                        break
                    elif q.get("custom") and idx == len(q["options"]):
                        custom = input("  " + C.GREEN + "\u25b8 " + ("Yaz: " if is_tr else "Type: ") + C.RESET).strip()
                        answers[q["key"]] = custom or q["options"][0][1]
                        break
                except (EOFError, KeyboardInterrupt):
                    print("\n" + C.YELLOW + "Cancelled." + C.RESET)
                    sys.exit(130)
            print()

    print("\n" + C.GREEN + "\u2713" + C.RESET + " ", end="")
    print(" | ".join(C.GRAY + k.title() + ": " + C.RESET + v for k, v in answers.items()))

    return answers


def _build_enriched_prompt(prompt: str, intent: Dict[str, Any], answers: Dict[str, str]) -> str:
    """Enrich original prompt with Q&A answers."""
    parts = [prompt, "", "--- RUNE Context (from interactive Q&A) ---"]
    labels = {"audience": "Target Audience", "tone": "Tone/Style", "length": "Length",
              "language": "Programming Language", "scope": "Scope", "style": "Visual Style",
              "goal": "Main Goal", "depth": "Analysis Depth"}
    for key, value in answers.items():
        parts.append(labels.get(key, key.title()) + ": " + value)
    parts.append("Domain: " + intent["domain"])
    parts.append("Language: " + intent["lang"].upper())
    return "\n".join(parts)


def _print_summary(prompt: str, intent: Dict[str, Any], answers: Dict[str, str], model: str) -> bool:
    """Print spell summary and ask for confirmation."""
    is_tr = (intent["lang"] == "tr")
    sep = C.MAGENTA + "\u2500" * 40 + C.RESET
    print("\n" + sep)
    title = "Buyu Ozeti" if is_tr else "Spell Summary"
    print(C.BOLD + "\U0001f4cb " + title + C.RESET + "\n")
    short = prompt[:80] + ("..." if len(prompt) > 80 else "")
    print("  " + C.GRAY + "Prompt:" + C.RESET + " " + short)
    print("  " + C.GRAY + "Domain:" + C.RESET + " " + intent["domain"])
    print("  " + C.GRAY + "Model:" + C.RESET + " " + model)
    for key, value in answers.items():
        print("  " + C.GRAY + key.title() + ":" + C.RESET + " " + value)
    print("\n  " + C.CYAN + "8 RUNE layers will be applied \u2728" + C.RESET)
    print(sep)

    try:
        label = "Onayliyor musun" if is_tr else "Confirm"
        confirm = input("\n" + C.GREEN + "\u2705 " + label + "? [E/h] " + C.RESET).strip().lower()
        return confirm in ("", "e", "y", "yes", "evet")
    except (EOFError, KeyboardInterrupt):
        print("\n" + C.YELLOW + "Cancelled." + C.RESET)
        return False


# ──────────────────────────────────────────────
# Cast Command
# ──────────────────────────────────────────────
def cmd_cast(args: argparse.Namespace) -> None:
    """Enhance + run prompt through LLM."""
    print_banner()
    prompt = " ".join(args.prompt)
    model = args.model or CONFIG["model"]
    quick_mode = getattr(args, "quick", False) or prompt.rstrip().endswith("!")

    if prompt.rstrip().endswith("!"):
        prompt = prompt.rstrip()[:-1].rstrip()

    print_info(f"🧙 Model: {model} | Template: {CONFIG['template_version']}")

    enhanced = prompt  # default for raw mode

    if args.raw:
        section("🚀 Raw Output")
        output = llm_call(prompt, model=model)
    elif quick_mode:
        print_info("⚡ Quick mode — skipping Q&A")
        enhanced = enhance_prompt(prompt, model, args.rune, args.verbose)
        section("📋 Enhanced Prompt")
        print(f"{C.CYAN}{enhanced}{C.RESET}")
        section("🚀 Output")
        output = llm_call(enhanced, model=model)
    else:
        intent = detect_intent(prompt)
        answers = _interactive_qa(intent, model)
        enriched = _build_enriched_prompt(prompt, intent, answers)

        if not _print_summary(prompt, intent, answers, model):
            print_info("🚫 Spell cancelled.")
            return

        enhanced = enhance_prompt(enriched, model, args.rune, args.verbose)
        section("📋 Enhanced Prompt")
        print(f"{C.CYAN}{enhanced}{C.RESET}")
        section("🚀 Output")
        output = llm_call(enhanced, model=model)

    # Spinoza validation
    report = {}
    try:
        print_meta("\n🔍 Running Spinoza validation...")
        report = spinoza_validate(output, model="gemini-3-flash-preview")
        print_spinoza_report(report)
    except Exception as e:
        print_warn(f"Spinoza validation skipped: {e}")

    # Save to memory
    overall_score = report.get("overall", 0.0) if isinstance(report, dict) else 0.0
    try:
        from rune.memory.store import MemoryStore
        store = MemoryStore(db_path=CONFIG.get("history_db", "~/.rune/history.db"))
        store.track_evolution(
            original=prompt,
            enhanced=enhanced if not args.raw else prompt,
            model=model,
            score=overall_score,
        )
        store.log_enhancement(
            original=prompt,
            enhanced=enhanced if not args.raw else prompt,
            model=model,
            spinoza_score=overall_score,
        )
        store.close()
        print_success("Saved to memory 🧠")
    except Exception as e:
        print_warn(f"Memory save failed: {e}")

    # Oracle: auto-refinement if score is low
    overall_score = report.get("overall", 0.0) if isinstance(report, dict) else 0.0
    lineage_id = None
    try:
        from rune.core.oracle import Oracle
        oracle = Oracle(spinoza_threshold=float(CONFIG.get("spinoza_threshold", 0.6)))

        # Auto-refine if below threshold (max 2 rounds)
        refinement_round = 0
        while oracle.should_refine(output) and refinement_round < oracle.max_rounds:
            refinement_round += 1
            print_warn(f"Score below threshold — auto-refining (round {refinement_round})...")
            report_summary = report.get("summary", "Quality below threshold")
            refine_prompt = oracle.build_refinement_prompt(prompt, output, str(report_summary), refinement_round)
            output = llm_call(refine_prompt, model=model)
            report = spinoza_validate(output, model="gemini-3-flash-preview")
            print_spinoza_report(report, f"Refined Output (Round {refinement_round})")
            overall_score = report.get("overall", 0.0)

        # Track lineage
        from rune.core.validator import _grade
        lineage = oracle.create_lineage(
            original_prompt=prompt,
            enhanced_prompt=enhanced,
            model=model,
            spinoza_score=overall_score,
            grade=_grade(overall_score) if isinstance(overall_score, (int, float)) else "?",
            refinement_round=refinement_round,
        )
        lineage_id = lineage.id
        print_meta(f"📜 Lineage: {lineage_id}")
    except Exception as e:
        print_warn(f"Oracle unavailable: {e}")

    # Feedback prompt (interactive only, not quick mode)
    if lineage_id and not quick_mode and sys.stdin.isatty():
        try:
            fb = input(f"\n{C.GREEN}📝 Rate this output [A-F / skip]: {C.RESET}").strip().upper()
            if fb and fb in ("A", "B", "C", "D", "F"):
                from rune.core.oracle import Oracle
                oracle = Oracle()
                oracle.record_feedback(lineage_id, fb)
                print_success(f"Feedback recorded: {fb}")
        except (EOFError, KeyboardInterrupt):
            pass

    # Save to file
    data = {
        "timestamp": datetime.datetime.now().isoformat(),
        "model": model,
        "user_prompt": prompt,
        "enhanced_prompt": enhanced if not args.raw else None,
        "output": output,
        "spinoza": report,
        "lineage_id": lineage_id,
    }
    fp = save_result(data)
    print_success(f"Saved to {fp}")

    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
        print_success(f"Output written to {args.output}")

    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
