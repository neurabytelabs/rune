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
__version__ = "1.8.0"

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
# ──────────────────────────────────────────────
# Cost Tracker (lazy init)
# ──────────────────────────────────────────────
_cost_tracker = None

def get_cost_tracker():
    global _cost_tracker
    if _cost_tracker is None:
        try:
            from rune.analytics.tracker import CostTracker
            _cost_tracker = CostTracker()
        except Exception:
            pass
    return _cost_tracker

DEFAULT_CONFIG: Dict[str, Any] = {
    "model": "gemini-3-flash-preview",
    "api_url": os.getenv("RUNE_API_URL", "http://127.0.0.1:8045/v1/chat/completions"),
    "api_key": os.getenv("RUNE_API_KEY", ""),
    "template_version": "v4.4",
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
META_PROMPT = """You are "RUNE Architect v1.0". Your task: take the user's simple request and
produce a prompt that conforms to the RUNE Framework's 8-layer structure.

RUNE LAYERS:
L0 — System Core: Role, persona, core behavioral rules
L1 — Context Identity: Domain knowledge, context, target audience
L2 — Intent Scope: Task definition, expected output format
L3 — Governance: Constraints, ethical rules, boundaries
L4 — Cognitive Engine: Thinking strategy (CoT, ToT, etc.)
L5 — Capabilities Domain: Tools, integrations, capabilities
L6 — QA: Validation criteria, quality control
L7 — Output Meta: Format, style, length, language

RULES:
1. Preserve the v4.3 XML structure (L0-L7).
2. Fill {{variable}} fields according to the task.
3. Select a Domain Preset: CODING / WRITING / ANALYSIS / CREATIVE / RESEARCH.
4. Determine Complexity L1-L5; skip unnecessary layers for L1-L2.
5. Specify active layers for Observability.
6. Detect the user's language and generate the prompt in that language.
7. Briefly explain what each layer does (shown in verbose mode).

OUTPUT THE PROMPT ONLY. Do not add explanations."""

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
            # Section-aware minimal TOML parser
            section = ""
            for line in text.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("["):
                    section = line.strip("[]").strip()
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
                    # Map [llm] keys to flat config
                    if section == "llm":
                        if k == "default_model":
                            cfg["model"] = v
                        else:
                            cfg[k] = v
                    elif section == "spinoza":
                        if k == "threshold":
                            cfg["spinoza_threshold"] = v
                    elif section == "general":
                        cfg[k] = v
                    else:
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
║  RUNE v1.8 | NeuraByte Labs         ║
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
def llm_call(prompt: str, model: str, stream: bool = False, system: Optional[str] = None, track: bool = True) -> str:
    """Send prompt to Antigravity proxy. Returns full response text."""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": stream,
        "max_tokens": CONFIG.get("max_tokens", 8000),
        "temperature": CONFIG.get("temperature", 0.7),
    }
    headers = {
        "Authorization": f"Bearer {CONFIG['api_key']}",
        "Content-Type": "application/json",
    }

    max_retries = 3
    for attempt in range(max_retries):
        try:
            resp = requests.post(
                CONFIG["api_url"],
                json=payload,
                headers=headers,
                stream=stream,
                timeout=CONFIG.get("timeout", 180),
            )
            resp.raise_for_status()
            break
        except requests.ConnectionError:
            if attempt == max_retries - 1:
                print_error("Cannot connect to LLM API at " + CONFIG["api_url"])
                print_info("Check your API endpoint and network connection.")
                sys.exit(1)
            import time; time.sleep(2 * (attempt + 1))
        except requests.HTTPError as e:
            if resp.status_code in (429, 503) and attempt < max_retries - 1:
                import time; time.sleep(5 * (attempt + 1))
                continue
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
        result_text = "".join(full)
        # Estimate tokens for streaming (no usage data available)
        if track:
            tracker = get_cost_tracker()
            if tracker:
                est_in = len(prompt) // 4
                est_out = len(result_text) // 4
                tracker.track(model, est_in, est_out)
        return result_text
    else:
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        # Track cost from usage data
        if track:
            tracker = get_cost_tracker()
            if tracker:
                usage = data.get("usage", {})
                in_tok = usage.get("prompt_tokens", len(prompt) // 4)
                out_tok = usage.get("completion_tokens", len(content) // 4)
                tracker.track(model, in_tok, out_tok)
        return content


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

    full_prompt = f"{META_PROMPT}{extra}\n\nUSER REQUEST:\n{user_prompt}"
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


def spinoza_validate(text: str, model: str = "gemini-3-flash-preview") -> Dict[str, Any]:
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


# ──────────────────────────────────────────────
# Interactive Q&A (rünle)
# ──────────────────────────────────────────────
def _detect_intent(prompt: str) -> Dict[str, Any]:
    """Detect prompt intent for interactive Q&A."""
    prompt_lower = prompt.lower()
    domain = "GENERAL"
    hints = {
        "CODING": ["code", "function", "api", "bug", "refactor", "script", "implement", "debug", "deploy", "kod"],
        "WRITING": ["blog", "article", "write", "essay", "story", "content", "post", "draft", "yaz", "makale"],
        "ANALYSIS": ["analyze", "compare", "evaluate", "review", "assess", "report", "analiz"],
        "CREATIVE": ["design", "create", "imagine", "visual", "logo", "brand", "tasarla", "gorsel"],
        "RESEARCH": ["research", "study", "investigate", "explore", "survey", "arastir", "incele"],
    }
    for d, kws in hints.items():
        if any(k in prompt_lower for k in kws):
            domain = d
            break
    tr_detect = any(c in "\u00e7\u011f\u0131\u00f6\u015f\u00fc\u00c7\u011e\u0130\u00d6\u015e\u00dc" for c in prompt)
    tr_words = any(w in prompt_lower for w in ["yaz", "olustur", "hakkinda", "icin"])
    lang = "tr" if (tr_detect or tr_words) else "en"
    return {"domain": domain, "lang": lang, "prompt": prompt}


def _interactive_qa(intent: Dict[str, Any], model: str) -> Dict[str, str]:
    """Claude Code-style interactive Q&A with multiple choice."""
    answers: Dict[str, str] = {}
    domain = intent["domain"]
    lang = intent["lang"]
    is_tr = (lang == "tr")

    questions: Dict[str, List[Dict[str, Any]]] = {
        "WRITING": [
            {"key": "audience",
             "label": "\U0001f4cc Hedef kitle kim?" if is_tr else "\U0001f4cc Target audience?",
             "options": [("Teknik (developer)" if is_tr else "Technical (developers)", "technical"),
                         ("Genel okuyucu" if is_tr else "General audience", "general"),
                         ("\u0130\u015f d\u00fcnyas\u0131 / C-level" if is_tr else "Business / C-level", "business")],
             "custom": True},
            {"key": "tone",
             "label": "\U0001f3ad Ton/Stil?" if is_tr else "\U0001f3ad Tone/Style?",
             "options": [("Akademik" if is_tr else "Academic", "academic"),
                         ("Blog / sohbet" if is_tr else "Blog / conversational", "conversational"),
                         ("Manifesto" if is_tr else "Manifesto / provocative", "provocative"),
                         ("Tutorial / how-to", "tutorial")],
             "custom": True},
            {"key": "length",
             "label": "\U0001f4cf Uzunluk?" if is_tr else "\U0001f4cf Length?",
             "options": [("~500", "short"), ("~1500", "medium"), ("~3000+", "long")],
             "custom": False},
        ],
        "CODING": [
            {"key": "language",
             "label": "\U0001f4bb Programlama dili?" if is_tr else "\U0001f4bb Programming language?",
             "options": [("Python", "python"), ("TypeScript", "typescript"),
                         ("Elixir", "elixir"), ("Rust", "rust")],
             "custom": True},
            {"key": "scope",
             "label": "\U0001f3af Kapsam?" if is_tr else "\U0001f3af Scope?",
             "options": [("Snippet", "snippet"), ("Module", "module"), ("Project", "project")],
             "custom": False},
        ],
        "CREATIVE": [
            {"key": "style",
             "label": "\U0001f3a8 Stil?" if is_tr else "\U0001f3a8 Style?",
             "options": [("Minimalist", "minimalist"), ("Dark fantasy", "dark_fantasy"),
                         ("Retro / terminal", "retro"), ("Modern", "modern")],
             "custom": True},
        ],
        "ANALYSIS": [
            {"key": "depth",
             "label": "\U0001f52c Derinlik?" if is_tr else "\U0001f52c Depth?",
             "options": [("Hizli ozet" if is_tr else "Quick summary", "quick"),
                         ("Detayli" if is_tr else "Detailed", "detailed"),
                         ("Karsilastirmali" if is_tr else "Comparative", "comparative")],
             "custom": False},
        ],
    }

    q_set = questions.get(domain, [
        {"key": "goal",
         "label": "\U0001f3af Ana hedef?" if is_tr else "\U0001f3af Main goal?",
         "options": [("Bilgi" if is_tr else "Information", "info"),
                     ("Karar destegi" if is_tr else "Decision support", "decision"),
                     ("Yaratici" if is_tr else "Creative", "creative")],
         "custom": True},
    ])

    sep = C.MAGENTA + "\u2500" * 40 + C.RESET
    print("\n" + sep)
    print(C.BOLD + "\U0001f52e Spell Analysis" + C.RESET)
    print(C.GRAY + "Domain: " + domain + " | Lang: " + lang.upper() + C.RESET)
    print(sep + "\n")

    for q in q_set:
        print(C.BOLD + q["label"] + C.RESET)
        opts = q["options"]
        for i, (text, _val) in enumerate(opts, 1):
            print("  " + C.CYAN + str(i) + ")" + C.RESET + " " + text)
        if q.get("custom"):
            print("  " + C.CYAN + str(len(opts) + 1) + ")" + C.RESET + " " + ("Ozel..." if is_tr else "Custom..."))

        while True:
            try:
                choice = input("\n  " + C.GREEN + "\u25b8" + C.RESET + " ").strip()
                if not choice:
                    answers[q["key"]] = opts[0][1]
                    print("  " + C.GRAY + "\u2192 " + opts[0][0] + C.RESET)
                    break
                try:
                    idx = int(choice) - 1
                except ValueError:
                    answers[q["key"]] = choice
                    break
                if 0 <= idx < len(opts):
                    answers[q["key"]] = opts[idx][1]
                    print("  " + C.GRAY + "\u2192 " + opts[idx][0] + C.RESET)
                    break
                elif q.get("custom") and idx == len(opts):
                    custom = input("  " + C.GREEN + "\u25b8 " + ("Yaz: " if is_tr else "Type: ") + C.RESET).strip()
                    answers[q["key"]] = custom or opts[0][1]
                    break
            except (EOFError, KeyboardInterrupt):
                print("\n" + C.YELLOW + "Cancelled." + C.RESET)
                sys.exit(130)
        print()

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

def cmd_cast(args: argparse.Namespace) -> None:
    """Enhance + run prompt through LLM."""
    print_banner()
    prompt = " ".join(args.prompt)
    model = args.model or CONFIG["model"]
    quick_mode = getattr(args, "quick", False) or prompt.rstrip().endswith("!")

    # Strip trailing ! for quick mode
    if prompt.rstrip().endswith("!"):
        prompt = prompt.rstrip()[:-1].rstrip()

    print_info(f"🧙 Model: {model} | Template: {CONFIG['template_version']}")

    if args.raw:
        # Skip enhancement, run raw
        section("🚀 Raw Output")
        output = llm_call(prompt, model=model)
    elif quick_mode:
        # Quick mode (rünle!) — no Q&A, straight to enhancement
        print_info("⚡ Quick mode — skipping Q&A")
        enhanced = enhance_prompt(prompt, model, args.rune, args.verbose)
        section("📋 Enhanced Prompt")
        print(f"{C.CYAN}{enhanced}{C.RESET}")
        section("🚀 Output")
        output = llm_call(enhanced, model=model)
    else:
        # Interactive mode (rünle) — Q&A then confirm
        intent = _detect_intent(prompt)
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

    # Save to memory (evolution tracking)
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
    """Show usage statistics from memory store."""
    print_banner()

    # Try memory store first
    try:
        from rune.memory.store import MemoryStore
        store = MemoryStore(db_path=CONFIG.get("history_db", "~/.rune/history.db"))
        stats = store.get_stats()
        evo_stats = store.get_evolution_stats()
        store.close()

        section("📈 WAND Statistics (from Memory 🧠)")
        print(store.format_stats(stats))

        # Evolution stats
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

        # Show top 5 best prompts
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

    # Cost info from tracker
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

    # Collect prompts from files or stdin
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
        # Split on --- or empty lines for multiple prompts
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
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from rune.synthesis.engine import SynthesisEngine
        engine = SynthesisEngine()
        result = engine.fuse(prompts, strategy=strategy, validate=True)
    except Exception as e:
        print_error(f"Fusion failed: {e}")
        return

    section("🔮 Fused Prompt")
    print(f"{C.CYAN}{result.text}{C.RESET}")

    # Spinoza report
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

    # Daily report
    print(tracker.get_daily_report())

    # Full breakdown
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
    p.add_argument("prompt", nargs="+", help="Your prompt (add ! at end for quick mode)")
    p.add_argument("--quick", "-q", action="store_true", help="Skip interactive Q&A (same as trailing !)")

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

    # cost
    p = sub.add_parser("cost", help="Detailed cost report")
    p.add_argument("--json", action="store_true", help="Output as JSON")

    # config
    sub.add_parser("config", help="Show current configuration")

    # fuse
    p = sub.add_parser("fuse", help="Fuse multiple prompts into one mega-prompt")
    p.add_argument("files", nargs="*", help="Prompt files to fuse")
    p.add_argument("--strategy", "-s", choices=["layered", "merged", "chain"],
                   default="layered", help="Fusion strategy (default: layered)")

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
║  RUNE v1.8 | NeuraByte Labs         ║
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
        "cost": cmd_cost,
        "config": cmd_config,
        "fuse": cmd_fuse,
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
