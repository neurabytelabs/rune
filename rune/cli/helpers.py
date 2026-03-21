"""
🪄 WAND CLI Helpers — Shared utilities, config, LLM integration, and display.
Extracted from the monolithic wand.py for RUNE v2.0.
"""

from __future__ import annotations

import datetime
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import requests
except ImportError:
    print("Error: 'requests' library required.  pip install requests")
    sys.exit(1)

from rune import __version__

# ──────────────────────────────────────────────
# Paths
# ──────────────────────────────────────────────
WAND_DIR = Path(__file__).resolve().parent.parent.parent  # rune/cli -> rune -> project root
PROMPTS_DIR = WAND_DIR / "prompts"
OUTPUT_DIR = WAND_DIR / "outputs"
CONFIG_PATH = Path.home() / ".rune" / "config.toml"

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


# ──────────────────────────────────────────────
# Default config
# ──────────────────────────────────────────────
DEFAULT_CONFIG: Dict[str, Any] = {
    "model": "gemini-3-flash-preview",
    "api_url": os.getenv("RUNE_API_URL", "http://127.0.0.1:8045/v1/chat/completions"),
    "api_key": os.getenv("RUNE_API_KEY", ""),
    "template_version": "v2.0",
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
# Config loader
# ──────────────────────────────────────────────
def load_config() -> Dict[str, Any]:
    """Load config from ~/.rune/config.toml or use defaults."""
    cfg = dict(DEFAULT_CONFIG)
    if CONFIG_PATH.exists():
        try:
            text = CONFIG_PATH.read_text()
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
║  RUNE v2.0 | NeuraByte Labs         ║
╚══════════════════════════════════════╝{C.RESET}"""

BANNER_PLAIN = """╔══════════════════════════════════════╗
║  🪄 WAND — Prompt Sorcery Engine    ║
║  Every prompt is a spell.            ║
║  RUNE v2.0 | NeuraByte Labs         ║
╚══════════════════════════════════════╝"""


def print_banner() -> None:
    print(BANNER)


# ──────────────────────────────────────────────
# Print helpers
# ──────────────────────────────────────────────
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
# File helpers
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


# ──────────────────────────────────────────────
# Meta Prompt (RUNE Architect)
# ──────────────────────────────────────────────
META_PROMPT = """You are "RUNE Architect v2.0". Your task: take the user's simple request and
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
1. Preserve the 8-layer XML structure (L0-L7).
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
# LLM Integration
# ──────────────────────────────────────────────
def llm_call(prompt: str, model: str, stream: bool = False,
             system: Optional[str] = None, track: bool = True) -> str:
    """Send prompt to LLM API. Returns full response text."""
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
    resp = None
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
            if resp is not None and resp.status_code in (429, 503) and attempt < max_retries - 1:
                import time; time.sleep(5 * (attempt + 1))
                continue
            print_error(f"API error: {e}")
            sys.exit(1)

    if resp is None:
        print_error("No response from LLM API.")
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
        print()
        result_text = "".join(full)
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
def enhance_prompt(user_prompt: str, model: str,
                   rune_name: Optional[str] = None,
                   verbose: bool = False) -> str:
    """Enhance a user prompt using the RUNE 8-layer meta-prompt."""
    extra = ""
    if rune_name:
        rune_path = PROMPTS_DIR / f"{rune_name}.md"
        if not rune_path.exists():
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
# Spinoza Validator (LLM-based, legacy)
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
    """Run Spinoza validation on text via LLM. Returns scores dict."""
    criteria_text = "\n".join(f"- {name}: {desc}" for name, desc in SPINOZA_CRITERIA)
    prompt = f"""You are SpinozaValidator v2.0. Evaluate the following text on these criteria.
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
# Intent Detection
# ──────────────────────────────────────────────
def detect_intent(prompt: str) -> Dict[str, Any]:
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
