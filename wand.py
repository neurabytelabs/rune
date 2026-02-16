#!/usr/bin/env python3
"""
🪄 WAND — The Sorcerer's CLI for RUNE
Every prompt is a spell.

Usage:
  wand cast "your prompt"              # Enhance + run through LLM
  wand inscribe "your prompt"          # Show enhanced prompt only (don't run)
  wand duel "your prompt"              # A/B compare: raw vs enhanced
  wand grimoire                        # List prompt library
  wand grimoire search "keyword"       # Search prompt library
  wand test "your prompt"              # Cross-model benchmark
  wand validate "text to validate"     # Run Spinoza validation
  wand forge                           # Interactive: create new rune template
  wand stats                           # Show usage statistics
  wand version                         # Show version info

Options:
  --model MODEL          Use specific model (default: gemini-3-pro)
  --rune RUNE_NAME       Use a specific rune from grimoire
  --raw                  Show raw (unenhanced) output
  --json                 Output as JSON
  --verbose              Show all layers being applied
  --no-color             Disable colored output
  --output FILE          Save output to file
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sys
import textwrap
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import requests
except ImportError:
    print("Error: 'requests' library required.  pip install requests")
    sys.exit(1)

# ──────────────────────────────────────────────
# Version
# ──────────────────────────────────────────────
__version__ = "1.0.0"

# ──────────────────────────────────────────────
# Paths
# ──────────────────────────────────────────────
WAND_DIR = Path(__file__).resolve().parent
PROMPTS_DIR = WAND_DIR / "prompts"
OUTPUT_DIR = WAND_DIR / "outputs"
CONFIG_PATH = Path.home() / ".rune" / "config.toml"

# ──────────────────────────────────────────────
# Default config
# ──────────────────────────────────────────────
DEFAULT_CONFIG: Dict[str, Any] = {
    "model": "gemini-3-pro",
    "api_url": os.getenv("RUNE_API_URL", "http://127.0.0.1:8045/v1/chat/completions"),
    "api_key": os.getenv("RUNE_API_KEY", ""),
    "template_version": "v4.3",
    "spinoza_threshold": 0.6,
    "output_dir": str(OUTPUT_DIR),
    "color": True,
}

# ──────────────────────────────────────────────
# ANSI Colors
# ──────────────────────────────────────────────
class C:
    """ANSI color codes — disabled when --no-color or non-TTY."""
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    GREEN = "\033[32m"
    RED = "\033[31m"
    YELLOW = "\033[33m"
    GRAY = "\033[90m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"

    @classmethod
    def disable(cls) -> None:
        for attr in ("MAGENTA", "CYAN", "GREEN", "RED", "YELLOW", "GRAY", "BOLD", "DIM", "RESET"):
            setattr(cls, attr, "")


# ──────────────────────────────────────────────
# Meta Prompt (RUNE Architect v1.0 — based on v4.3)
# ──────────────────────────────────────────────
META_PROMPT = """Sen "RUNE Architect v1.0"sun. Görevin: kullanıcının basit isteğini alıp
RUNE Framework'ün 8 katmanlı yapısına uygun bir prompt üretmek.

RUNE KATMANLARI:
L0 — System Core: Rol, persona, temel davranış kuralları
L1 — Context Identity: Domain bilgisi, bağlam, hedef kitle
L2 — Intent Scope: Görev tanımı, beklenen çıktı formatı
L3 — Governance: Kısıtlamalar, etik kurallar, sınırlar
L4 — Cognitive Engine: Düşünme stratejisi (CoT, ToT, vb.)
L5 — Capabilities Domain: Araçlar, entegrasyonlar, yetenekler
L6 — QA: Doğrulama kriterleri, kalite kontrol
L7 — Output Meta: Format, stil, uzunluk, dil

KURALLAR:
1. v4.3 XML yapısını koru (L0-L7).
2. {{variable}} alanlarını göreve göre doldur.
3. Domain Preset seç: CODING / WRITING / ANALYSIS / CREATIVE / RESEARCH.
4. Complexity L1-L5 belirle. L1-L2'de gereksiz katmanları atla.
5. Observability için aktif katmanları belirt.
6. Kullanıcı Türkçe yazdıysa Türkçe, İngilizce yazdıysa İngilizce üret.
7. Her katmanın ne yaptığını kısa açıkla (verbose modda gösterilecek).

SADECE PROMPT'U VER. Açıklama ekleme."""

LAYER_NAMES = [
    "L0 — System Core",
    "L1 — Context Identity",
    "L2 — Intent Scope",
    "L3 — Governance",
    "L4 — Cognitive Engine",
    "L5 — Capabilities Domain",
    "L6 — QA",
    "L7 — Output Meta",
]

# ──────────────────────────────────────────────
# Config loader
# ──────────────────────────────────────────────
def load_config() -> Dict[str, Any]:
    """Load config from ~/.rune/config.toml or use defaults."""
    cfg = dict(DEFAULT_CONFIG)
    if CONFIG_PATH.exists():
        try:
            text = CONFIG_PATH.read_text()
            # Minimal TOML parser for flat key=value
            for line in text.splitlines():
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("["):
                    continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    k = k.strip().strip('"')
                    v = v.strip().strip('"')
                    if v.lower() == "true":
                        v = True
                    elif v.lower() == "false":
                        v = False
                    else:
                        try:
                            v = float(v) if "." in v else int(v)
                        except ValueError:
                            pass
                    cfg[k] = v
        except Exception:
            pass
    return cfg


CONFIG = load_config()

# ──────────────────────────────────────────────
# Banner
# ──────────────────────────────────────────────
BANNER = f"""{C.MAGENTA}{C.BOLD}╔══════════════════════════════════════╗
║  🪄 WAND — Prompt Sorcery Engine    ║
║  Every prompt is a spell.            ║
║  RUNE v1.0 | NeuraByte Labs         ║
╚══════════════════════════════════════╝{C.RESET}"""


def print_banner() -> None:
    print(BANNER)


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────
def ensure_output_dir() -> Path:
    today = datetime.date.today().isoformat()
    path = Path(CONFIG["output_dir"]) / today
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_result(data: Dict[str, Any]) -> Path:
    out = ensure_output_dir()
    ts = datetime.datetime.now().strftime("%H%M%S")
    slug = re.sub(r"[^a-zA-Z0-9_]", "_", data.get("user_prompt", "")[:40])
    fp = out / f"{ts}_{slug}.json"
    fp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return fp


def print_error(msg: str) -> None:
    print(f"{C.RED}✗ Error: {msg}{C.RESET}", file=sys.stderr)


def print_success(msg: str) -> None:
    print(f"{C.GREEN}✓ {msg}{C.RESET}")


def print_info(msg: str) -> None:
    print(f"{C.CYAN}ℹ {msg}{C.RESET}")


def print_warn(msg: str) -> None:
    print(f"{C.YELLOW}⚠ {msg}{C.RESET}")


def print_meta(msg: str) -> None:
    print(f"{C.GRAY}{msg}{C.RESET}")


def section(title: str) -> None:
    print(f"\n{C.MAGENTA}{C.BOLD}{'═'*60}{C.RESET}")
    print(f"{C.MAGENTA}{C.BOLD}  {title}{C.RESET}")
    print(f"{C.MAGENTA}{C.BOLD}{'═'*60}{C.RESET}")


# ──────────────────────────────────────────────
# LLM Integration
# ──────────────────────────────────────────────
def llm_call(prompt: str, model: str, stream: bool = True, system: Optional[str] = None) -> str:
    """Send prompt to Antigravity proxy. Returns full response text."""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": stream,
    }
    headers = {
        "Authorization": f"Bearer {CONFIG['api_key']}",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(
            CONFIG["api_url"],
            json=payload,
            headers=headers,
            stream=stream,
            timeout=120,
        )
        resp.raise_for_status()
    except requests.ConnectionError:
        print_error("Cannot connect to Antigravity proxy at " + CONFIG["api_url"])
        print_info("Make sure the proxy is running: antigravity start")
        sys.exit(1)
    except requests.HTTPError as e:
        print_error(f"API error: {e}")
        sys.exit(1)

    if stream:
        full = []
        for line in resp.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data: "):
                continue
            data_str = line[6:]
            if data_str.strip() == "[DONE]":
                break
            try:
                chunk = json.loads(data_str)
                delta = chunk.get("choices", [{}])[0].get("delta", {})
                token = delta.get("content", "")
                if token:
                    print(token, end="", flush=True)
                    full.append(token)
            except json.JSONDecodeError:
                continue
        print()  # newline after streaming
        return "".join(full)
    else:
        data = resp.json()
        return data["choices"][0]["message"]["content"]


# ──────────────────────────────────────────────
# Enhancer
# ──────────────────────────────────────────────
def enhance_prompt(user_prompt: str, model: str, rune_name: Optional[str] = None, verbose: bool = False) -> str:
    """Enhance a user prompt using the RUNE 8-layer meta-prompt."""
    # If a specific rune template is requested, load it
    extra = ""
    if rune_name:
        rune_path = PROMPTS_DIR / f"{rune_name}.md"
        if not rune_path.exists():
            # Try partial match
            matches = list(PROMPTS_DIR.glob(f"*{rune_name}*"))
            if matches:
                rune_path = matches[0]
            else:
                print_warn(f"Rune '{rune_name}' not found, using default enhancer.")
                rune_path = None
        if rune_path and rune_path.exists():
            extra = f"\n\nRUNE TEMPLATE:\n{rune_path.read_text(encoding='utf-8')}"
            if verbose:
                print_info(f"Using rune template: {rune_path.name}")

    if verbose:
        print_info("Applying RUNE 8-layer enhancement...")
        for layer in LAYER_NAMES:
            print(f"  {C.CYAN}→ {layer}{C.RESET}")

    full_prompt = f"{META_PROMPT}{extra}\n\nKULLANICI İSTEĞİ:\n{user_prompt}"
    print_meta("⚡ Enhancing prompt...")
    enhanced = llm_call(full_prompt, model=model, stream=False)
    return enhanced


# ──────────────────────────────────────────────
# Spinoza Validator
# ──────────────────────────────────────────────
SPINOZA_CRITERIA = [
    ("clarity", "Is the text clear and unambiguous?"),
    ("coherence", "Is the text logically coherent and well-structured?"),
    ("completeness", "Does the text fully address the topic?"),
    ("accuracy", "Is the information accurate and well-reasoned?"),
    ("relevance", "Is the content relevant to the stated goal?"),
    ("depth", "Does the text show sufficient depth of analysis?"),
    ("actionability", "Are the suggestions/conclusions actionable?"),
]


def spinoza_validate(text: str, model: str = "gemini-3-flash") -> Dict[str, Any]:
    """Run Spinoza validation on text. Returns scores dict."""
    criteria_text = "\n".join(f"- {name}: {desc}" for name, desc in SPINOZA_CRITERIA)
    prompt = f"""You are SpinozaValidator v1.0. Evaluate the following text on these criteria.
For each criterion, give a score from 0.0 to 1.0 and a one-line reason.
Return ONLY valid JSON in this format:
{{
  "scores": {{
    "clarity": {{"score": 0.0, "reason": "..."}},
    ...
  }},
  "overall": 0.0,
  "summary": "one-line summary"
}}

CRITERIA:
{criteria_text}

TEXT TO EVALUATE:
{text[:3000]}"""

    try:
        raw = llm_call(prompt, model=model, stream=False)
        # Extract JSON from response
        match = re.search(r"\{[\s\S]*\}", raw)
        if match:
            return json.loads(match.group())
    except Exception as e:
        print_warn(f"Spinoza validation failed: {e}")

    return {"scores": {}, "overall": 0.0, "summary": "Validation failed"}


def print_spinoza_report(result: Dict[str, Any], label: str = "Spinoza Report") -> None:
    """Pretty-print a Spinoza validation report."""
    section(f"🔍 {label}")
    scores = result.get("scores", {})
    threshold = float(CONFIG.get("spinoza_threshold", 0.6))

    for name, data in scores.items():
        if isinstance(data, dict):
            score = data.get("score", 0)
            reason = data.get("reason", "")
        else:
            score = float(data) if data else 0
            reason = ""
        color = C.GREEN if score >= threshold else C.YELLOW if score >= 0.4 else C.RED
        bar = "█" * int(score * 10) + "░" * (10 - int(score * 10))
        print(f"  {name:<15} {color}{bar} {score:.1f}{C.RESET}  {C.GRAY}{reason}{C.RESET}")

    overall = result.get("overall", 0)
    color = C.GREEN if overall >= threshold else C.YELLOW if overall >= 0.4 else C.RED
    print(f"\n  {C.BOLD}Overall: {color}{overall:.2f}{C.RESET}")
    summary = result.get("summary", "")
    if summary:
        print(f"  {C.GRAY}{summary}{C.RESET}")


# ──────────────────────────────────────────────
# Commands
# ──────────────────────────────────────────────

def cmd_cast(args: argparse.Namespace) -> None:
    """Enhance + run prompt through LLM."""
    print_banner()
    prompt = " ".join(args.prompt)
    model = args.model or CONFIG["model"]
    print_meta(f"Model: {model} | Template: {CONFIG['template_version']}")

    if args.raw:
        # Skip enhancement, run raw
        section("🚀 Raw Output")
        output = llm_call(prompt, model=model)
    else:
        enhanced = enhance_prompt(prompt, model, args.rune, args.verbose)
        section("📋 Enhanced Prompt")
        print(f"{C.CYAN}{enhanced}{C.RESET}")
        section("🚀 Output")
        output = llm_call(enhanced, model=model)

    # Spinoza validation
    print_meta("\n🔍 Running Spinoza validation...")
    report = spinoza_validate(output, model="gemini-3-flash")
    print_spinoza_report(report)

    # Save
    data = {
        "timestamp": datetime.datetime.now().isoformat(),
        "model": model,
        "user_prompt": prompt,
        "enhanced_prompt": enhanced if not args.raw else None,
        "output": output,
        "spinoza": report,
    }
    fp = save_result(data)
    print_success(f"Saved to {fp}")

    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
        print_success(f"Output written to {args.output}")

    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))


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

    # Enhanced
    enhanced = enhance_prompt(prompt, model, args.rune, args.verbose)

    section("🔴 RAW — Running original prompt")
    raw_output = llm_call(prompt, model=model)

    section("🟢 ENHANCED — Running enhanced prompt")
    enhanced_output = llm_call(enhanced, model=model)

    # Validate both
    print_meta("\n🔍 Validating both outputs...")
    raw_report = spinoza_validate(raw_output)
    enh_report = spinoza_validate(enhanced_output)

    print_spinoza_report(raw_report, "Raw Output Scores")
    print_spinoza_report(enh_report, "Enhanced Output Scores")

    # Comparison summary
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
    models = ["gemini-3-pro", "gemini-3-flash", "gpt-4o", "claude-sonnet-4-5", "claude-haiku-4"]
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

    # Summary table
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
    text = " ".join(args.text)
    if not text:
        if not sys.stdin.isatty():
            text = sys.stdin.read()
        else:
            print_error("No text provided.")
            return

    print_meta(f"Validating {len(text)} characters...")
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
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
    """Show usage statistics."""
    print_banner()
    out_dir = Path(CONFIG["output_dir"])
    if not out_dir.exists():
        print_info("No output data yet. Run some spells first!")
        return

    section("📈 WAND Statistics")

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
                # Extract spinoza scores
                for key in ("spinoza", "enhanced_spinoza"):
                    sp = data.get(key, {})
                    if isinstance(sp, dict) and "overall" in sp:
                        spinoza_scores.append(sp["overall"])
                # Test results
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


def cmd_version(args: argparse.Namespace) -> None:
    """Show version info."""
    print_banner()
    print(f"  {C.BOLD}WAND{C.RESET}     v{__version__}")
    print(f"  {C.BOLD}RUNE{C.RESET}     {CONFIG['template_version']}")
    print(f"  {C.BOLD}Model{C.RESET}    {CONFIG['model']}")
    print(f"  {C.BOLD}API{C.RESET}      {CONFIG['api_url']}")
    print(f"  {C.BOLD}Prompts{C.RESET}  {PROMPTS_DIR}")
    print(f"  {C.BOLD}Outputs{C.RESET}  {CONFIG['output_dir']}")


# ──────────────────────────────────────────────
# Argument Parser
# ──────────────────────────────────────────────
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="wand",
        description="🪄 WAND — The Sorcerer's CLI for RUNE",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Every prompt is a spell. ✨",
    )

    # Global options
    parser.add_argument("--model", "-m", help="LLM model to use")
    parser.add_argument("--rune", "-r", help="Use a specific rune from grimoire")
    parser.add_argument("--raw", action="store_true", help="Show raw (unenhanced) output")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show all layers being applied")
    parser.add_argument("--no-color", action="store_true", help="Disable colored output")
    parser.add_argument("--output", "-o", help="Save output to file")

    sub = parser.add_subparsers(dest="command", help="Available commands")

    # cast
    p = sub.add_parser("cast", help="Enhance + run prompt through LLM")
    p.add_argument("prompt", nargs="+", help="Your prompt")

    # inscribe
    p = sub.add_parser("inscribe", help="Show enhanced prompt only")
    p.add_argument("prompt", nargs="+", help="Your prompt")

    # duel
    p = sub.add_parser("duel", help="A/B compare: raw vs enhanced")
    p.add_argument("prompt", nargs="+", help="Your prompt")

    # grimoire
    p = sub.add_parser("grimoire", help="List prompt library")
    p.add_argument("search", nargs="*", help="Search keyword")

    # test
    p = sub.add_parser("test", help="Cross-model benchmark")
    p.add_argument("prompt", nargs="+", help="Your prompt")

    # validate
    p = sub.add_parser("validate", help="Run Spinoza validation")
    p.add_argument("text", nargs="*", help="Text to validate")

    # forge
    sub.add_parser("forge", help="Interactive: create new rune template")

    # stats
    sub.add_parser("stats", help="Show usage statistics")

    # version
    sub.add_parser("version", help="Show version info")

    return parser


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────
def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.no_color or not sys.stdout.isatty():
        C.disable()
        # Rebuild banner without colors
        global BANNER
        BANNER = """╔══════════════════════════════════════╗
║  🪄 WAND — Prompt Sorcery Engine    ║
║  Every prompt is a spell.            ║
║  RUNE v1.0 | NeuraByte Labs         ║
╚══════════════════════════════════════╝"""

    commands = {
        "cast": cmd_cast,
        "inscribe": cmd_inscribe,
        "duel": cmd_duel,
        "grimoire": cmd_grimoire,
        "test": cmd_test,
        "validate": cmd_validate,
        "forge": cmd_forge,
        "stats": cmd_stats,
        "version": cmd_version,
    }

    if not args.command:
        parser.print_help()
        return

    fn = commands.get(args.command)
    if fn:
        try:
            fn(args)
        except KeyboardInterrupt:
            print(f"\n{C.YELLOW}Interrupted.{C.RESET}")
            sys.exit(130)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
