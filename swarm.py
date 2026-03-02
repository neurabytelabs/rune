#!/usr/bin/env python3
"""
🐝 RUNE SWARM — Multi-Agent Prompt Evolution Engine
One prompt enters. The best prompt survives.

Usage:
  python swarm.py "your prompt here"
  python swarm.py "your prompt" --agents 5
  python swarm.py "your prompt" --model grok-3 --verbose
  python swarm.py "your prompt" --rounds 2

NeuraByte Labs, 2026
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import textwrap
import concurrent.futures
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    import requests
except ImportError:
    print("pip install requests")
    sys.exit(1)

# ─── Load secrets ────────────────────────────────────────────────────────────
def _load_secrets():
    secrets = Path.home() / ".secrets"
    if secrets.exists():
        for line in secrets.read_text().splitlines():
            line = line.strip()
            if line.startswith("export "):
                line = line[7:]
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                v = v.strip().strip('"').strip("'")
                if k.strip() not in os.environ:
                    os.environ[k.strip()] = v

_load_secrets()

# ─── Config ──────────────────────────────────────────────────────────────────
API_URL = os.getenv("XAI_API_URL", "https://api.x.ai/v1/chat/completions")
API_KEY = os.getenv("XAI_API_KEY", "")
DEFAULT_MODEL = "grok-4-1-fast-non-reasoning"
FAST_MODEL = "grok-3-mini"

# ─── Colors ──────────────────────────────────────────────────────────────────
class C:
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    R = "\033[0m"

# ─── Agent Strategies ───────────────────────────────────────────────────────
STRATEGIES = {
    "expert": {
        "name": "Expert",
        "emoji": "🎓",
        "system": (
            "You are the world's foremost expert on this topic. "
            "Decades of experience, published research, deep practical knowledge.\n"
            "- Be technically precise and authoritative\n"
            "- Structure: overview → details → actionable steps\n"
            "- Include specific data, examples, references\n"
            "- Confident, professional tone\n"
            "- No hedging, no filler"
        ),
    },
    "creative": {
        "name": "Creative",
        "emoji": "🎨",
        "system": (
            "You are a wildly creative lateral thinker. "
            "You find unexpected connections between ideas.\n"
            "- Original and surprising — never the obvious answer\n"
            "- Rich metaphors, analogies, storytelling\n"
            "- Cross-domain connections that illuminate\n"
            "- Memorable and quotable\n"
            "- Still practical and actionable"
        ),
    },
    "devils_advocate": {
        "name": "Devil's Advocate",
        "emoji": "😈",
        "system": (
            "You are a rigorous critical thinker. "
            "Find the strongest answer by first destroying weak ones.\n"
            "- Question every assumption\n"
            "- Identify failure modes and blind spots\n"
            "- Then build a solution that survives scrutiny\n"
            "- Constructively critical, not cynical\n"
            "- End with a battle-tested recommendation"
        ),
    },
    "synthesizer": {
        "name": "Synthesizer",
        "emoji": "🔬",
        "system": (
            "You are a polymath who sees patterns across disciplines. "
            "Science, philosophy, art, business, technology.\n"
            "- Draw from 2-3+ different domains\n"
            "- Show how one field illuminates another\n"
            "- Create a unified integrative framework\n"
            "- Intellectually rich yet practical"
        ),
    },
    "minimalist": {
        "name": "Minimalist",
        "emoji": "✂️",
        "system": (
            "Radical clarity. Every word must earn its place.\n"
            "- As short as possible while complete\n"
            "- Crystal clear structure\n"
            "- Bullets/tables over prose\n"
            "- No filler, no hedging, no 'As an AI...'\n"
            "- Direct and actionable"
        ),
    },
    "wildcard": {
        "name": "Wild Card",
        "emoji": "🃏",
        "system": (
            "You combine unusual traits: philosopher + comedian + strategist. "
            "Break conventions.\n"
            "- Break at least one AI response convention\n"
            "- Include an insight no other approach would find\n"
            "- Memorable and quotable\n"
            "- Genuine value despite unconventional delivery"
        ),
    },
}

DEFAULT_AGENT_TYPES = ["expert", "creative", "devils_advocate"]
ALL_AGENT_TYPES = list(STRATEGIES.keys())

# ─── Data ────────────────────────────────────────────────────────────────────
@dataclass
class AgentResult:
    agent_type: str
    name: str
    emoji: str
    system_prompt: str
    response: str
    scores: dict = field(default_factory=dict)
    overall: float = 0.0
    rank: int = 0
    time_sec: float = 0.0
    tokens_in: int = 0
    tokens_out: int = 0

# ─── Spinoza Scorer ──────────────────────────────────────────────────────────
import re

def spinoza_score(text: str) -> dict:
    """Score text on Spinoza's 4 pillars (0-25 each, 0-100 total)."""

    # CONATUS — Actionability
    con = 10.0
    for w in ["implement","create","build","use","apply","run","execute",
              "start","deploy","write","design","step","yap","oluştur","kur"]:
        if w in text.lower(): con += 1.2
    con += min(len(re.findall(r'^\s*\d+[\.\)]\s', text, re.M)) * 0.8, 5)
    con += min(text.count('```') * 1.0, 4)
    con = min(con, 25)

    # RATIO — Logic & Structure
    rat = 12.0
    rat += min(len(re.findall(r'^#+\s', text, re.M)) * 1.2, 5)
    for w in ["because","therefore","however","since","thus","çünkü","dolayısıyla"]:
        if w in text.lower(): rat += 0.8
    words = len(text.split())
    if words < 50: rat -= 4
    elif words > 150: rat += 2
    rat = min(max(rat, 0), 25)

    # LAETITIA — Tone
    lae = 15.0
    for w in ["excellent","powerful","effective","best","optimal","key","mükemmel"]:
        if w in text.lower(): lae += 0.6
    for w in ["i'm sorry","i cannot","as an ai","unfortunately","maalesef"]:
        if w in text.lower(): lae -= 2
    lae = min(max(lae, 0), 25)

    # NATURA — Naturalness
    nat = 14.0
    sents = re.split(r'[.!?]\s+', text)
    if len(sents) > 3:
        lens = [len(s.split()) for s in sents if s.strip()]
        if lens:
            avg = sum(lens)/len(lens)
            var = sum((l-avg)**2 for l in lens)/len(lens)
            if 5 < var < 200: nat += 3
    for r in ["as an ai language model","i'd be happy to","certainly!","great question"]:
        if r in text.lower(): nat -= 3
    if 2 <= text.count('\n\n') <= 12: nat += 2
    nat = min(max(nat, 0), 25)

    total = con + rat + lae + nat
    return {"conatus": round(con,1), "ratio": round(rat,1),
            "laetitia": round(lae,1), "natura": round(nat,1),
            "overall": round(total,1)}

# ─── LLM Call ────────────────────────────────────────────────────────────────
def call_llm(prompt: str, system: str, model: str) -> tuple[str, float, int, int]:
    """Call LLM, return (response, seconds, tok_in, tok_out)."""
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7,
        "max_tokens": 4000,
    }
    t0 = time.monotonic()
    resp = requests.post(API_URL, json=payload, headers=headers, timeout=120)
    elapsed = time.monotonic() - t0
    resp.raise_for_status()
    data = resp.json()
    content = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})
    return content, elapsed, usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0)

# ─── Orchestrator ────────────────────────────────────────────────────────────
def run_agent(agent_type: str, prompt: str, model: str, context: str = "") -> AgentResult:
    """Run a single agent."""
    strat = STRATEGIES[agent_type]
    system = strat["system"]
    if context:
        system += f"\n\nCONTEXT FROM OTHER AGENTS:\n{context}"

    try:
        response, sec, ti, to = call_llm(prompt, system, model)
    except Exception as e:
        response = f"[ERROR: {e}]"
        sec, ti, to = 0, 0, 0

    scores = spinoza_score(response)
    return AgentResult(
        agent_type=agent_type,
        name=strat["name"],
        emoji=strat["emoji"],
        system_prompt=system,
        response=response,
        scores=scores,
        overall=scores["overall"],
        time_sec=round(sec, 2),
        tokens_in=ti,
        tokens_out=to,
    )

def fuse_responses(results: list[AgentResult], prompt: str, model: str) -> tuple[str, dict]:
    """Fuse top agent responses into a final synthesis."""
    fusion_system = (
        "You are the RUNE SWARM Synthesizer. You receive multiple expert responses "
        "to the same prompt, each from a different strategic angle. "
        "Your job: create the ULTIMATE response by combining the best elements.\n\n"
        "Rules:\n"
        "- Take the strongest insights from each agent\n"
        "- Resolve contradictions intelligently\n"
        "- The final output must be better than any individual response\n"
        "- Be concise — don't just concatenate, SYNTHESIZE\n"
        "- Structure for maximum clarity and impact"
    )

    agents_text = ""
    for r in results:
        agents_text += f"\n{'='*60}\n"
        agents_text += f"AGENT: {r.emoji} {r.name} (Score: {r.overall}/100)\n"
        agents_text += f"{'='*60}\n{r.response}\n"

    fusion_prompt = (
        f"ORIGINAL USER PROMPT:\n{prompt}\n\n"
        f"AGENT RESPONSES (ranked by Spinoza score):\n{agents_text}\n\n"
        "NOW: Create the definitive synthesis. Be better than any single agent."
    )

    try:
        response, _, _, _ = call_llm(fusion_prompt, fusion_system, model)
        scores = spinoza_score(response)
    except Exception as e:
        response = f"[FUSION ERROR: {e}]"
        scores = {"overall": 0}

    return response, scores

# ─── Display ─────────────────────────────────────────────────────────────────
def print_header(prompt: str, n_agents: int, model: str, rounds: int):
    print(f"\n{C.BOLD}{C.CYAN}🐝 RUNE SWARM v0.1{C.R}")
    print(f"{C.DIM}One prompt enters. The best prompt survives.{C.R}\n")
    print(f"{C.BOLD}Prompt:{C.R}  {prompt[:100]}{'…' if len(prompt)>100 else ''}")
    print(f"{C.BOLD}Agents:{C.R}  {n_agents}  |  {C.BOLD}Model:{C.R} {model}  |  {C.BOLD}Rounds:{C.R} {rounds}")
    print(f"{'─'*70}")

def print_agent_result(r: AgentResult, verbose: bool = False):
    bar_len = int(r.overall / 100 * 30)
    bar = f"{C.GREEN}{'█'*bar_len}{C.DIM}{'░'*(30-bar_len)}{C.R}"

    medal = ""
    if r.rank == 1: medal = f" {C.YELLOW}🏆{C.R}"
    elif r.rank == 2: medal = f" {C.WHITE}🥈{C.R}"
    elif r.rank == 3: medal = f" {C.RED}🥉{C.R}"

    print(f"\n{r.emoji} {C.BOLD}#{r.rank} {r.name}{C.R}{medal}  "
          f"{C.DIM}({r.time_sec}s, {r.tokens_out} tok){C.R}")
    print(f"   {bar} {C.BOLD}{r.overall}{C.R}/100")
    print(f"   {C.DIM}C:{r.scores['conatus']} R:{r.scores['ratio']} "
          f"L:{r.scores['laetitia']} N:{r.scores['natura']}{C.R}")

    if verbose:
        preview = r.response[:300].replace('\n', '\n   ')
        print(f"   {C.DIM}{preview}{'…' if len(r.response)>300 else ''}{C.R}")

def print_fusion(text: str, scores: dict, agents_best: float):
    print(f"\n{'═'*70}")
    print(f"{C.BOLD}{C.MAGENTA}🔮 SWARM SYNTHESIS{C.R}")
    print(f"{'═'*70}")

    improvement = ((scores['overall'] - agents_best) / agents_best * 100) if agents_best > 0 else 0
    color = C.GREEN if improvement > 0 else C.RED
    print(f"   Score: {C.BOLD}{scores['overall']}{C.R}/100  "
          f"({color}{improvement:+.1f}% vs best agent{C.R})")
    print(f"{'─'*70}")
    print(text)
    print(f"{'─'*70}")

# ─── Main ────────────────────────────────────────────────────────────────────
def swarm(prompt: str, agent_types: list[str], model: str,
          rounds: int = 1, top_k: int = 2, verbose: bool = False) -> dict:
    """Run the full SWARM pipeline."""

    print_header(prompt, len(agent_types), model, rounds)

    all_results = []
    prev_context = ""

    for rnd in range(1, rounds + 1):
        if rounds > 1:
            print(f"\n{C.BOLD}{C.BLUE}── Round {rnd}/{rounds} ──{C.R}")

        # Run agents in parallel
        print(f"\n{C.DIM}Spawning {len(agent_types)} agents...{C.R}")
        results = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=len(agent_types)) as executor:
            futures = {
                executor.submit(run_agent, at, prompt, model, prev_context): at
                for at in agent_types
            }
            for future in concurrent.futures.as_completed(futures):
                r = future.result()
                results.append(r)
                sys.stdout.write(f"  {r.emoji} {r.name} done ({r.time_sec}s)\n")
                sys.stdout.flush()

        # Rank
        results.sort(key=lambda r: -r.overall)
        for i, r in enumerate(results, 1):
            r.rank = i

        # Display
        print(f"\n{C.BOLD}📊 Tournament Results (Round {rnd}):{C.R}")
        for r in results:
            print_agent_result(r, verbose)

        all_results = results

        # Build context for next round (cross-pollination)
        if rnd < rounds:
            top = results[:top_k]
            prev_context = "\n".join(
                f"[{r.name} - Score {r.overall}]: {r.response[:500]}"
                for r in top
            )

    # Fusion
    top = all_results[:top_k]
    print(f"\n{C.DIM}Fusing top {len(top)} agents...{C.R}")
    fused_text, fused_scores = fuse_responses(top, prompt, model)
    best_agent_score = all_results[0].overall if all_results else 0
    print_fusion(fused_text, fused_scores, best_agent_score)

    # Save report
    output_dir = Path(__file__).parent / "outputs" / "swarm"
    output_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    report = {
        "timestamp": datetime.now().isoformat(),
        "prompt": prompt,
        "model": model,
        "rounds": rounds,
        "agents": [
            {
                "rank": r.rank, "type": r.agent_type, "name": r.name,
                "scores": r.scores, "overall": r.overall,
                "time_sec": r.time_sec, "tokens_out": r.tokens_out,
                "response": r.response,
            }
            for r in all_results
        ],
        "fusion": {
            "text": fused_text,
            "scores": fused_scores,
        },
    }
    report_path = output_dir / f"swarm_{ts}.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"\n{C.DIM}📁 Report saved: {report_path}{C.R}")

    return report

# ─── CLI ─────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="🐝 RUNE SWARM — Multi-Agent Prompt Evolution",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("prompt", help="The prompt to swarm")
    parser.add_argument("--agents", "-a", type=int, default=3,
                       help="Number of agents (3-6, default: 3)")
    parser.add_argument("--model", "-m", default=DEFAULT_MODEL,
                       help=f"LLM model (default: {DEFAULT_MODEL})")
    parser.add_argument("--rounds", "-r", type=int, default=1,
                       help="Evolution rounds (default: 1, max: 3)")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Show response previews")
    parser.add_argument("--all", action="store_true",
                       help="Use all 6 agent types")
    parser.add_argument("--top-k", type=int, default=2,
                       help="Top K agents to fuse (default: 2)")

    args = parser.parse_args()

    if not API_KEY:
        print(f"{C.RED}Error: XAI_API_KEY not set. Add to ~/.secrets{C.R}")
        sys.exit(1)

    # Select agents
    if args.all:
        agents = ALL_AGENT_TYPES
    elif args.agents <= 3:
        agents = DEFAULT_AGENT_TYPES[:args.agents]
    else:
        agents = ALL_AGENT_TYPES[:min(args.agents, 6)]

    rounds = min(args.rounds, 3)

    swarm(args.prompt, agents, args.model, rounds=rounds,
          top_k=args.top_k, verbose=args.verbose)

if __name__ == "__main__":
    main()
