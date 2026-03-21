"""
🐝 WAND Swarm Command — Multi-agent prompt evolution from CLI.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from rune.cli.helpers import (
    C, CONFIG,
    print_banner, print_error, print_info, print_meta, print_success,
    section,
)


def cmd_swarm(args: argparse.Namespace) -> None:
    """Run multi-agent swarm on a prompt."""
    print_banner()

    prompt = " ".join(args.prompt)
    model = args.model or CONFIG["model"]

    from rune.providers.openai_compat import create_provider_from_config
    from rune.swarm.orchestrator import SwarmOrchestrator
    from rune.swarm.agents import DEFAULT_AGENT_TYPES, ALL_AGENT_TYPES

    provider = create_provider_from_config(CONFIG)
    orchestrator = SwarmOrchestrator(provider, model=model)

    # Select agents
    if args.all:
        agents = ALL_AGENT_TYPES
    elif args.agents <= 3:
        agents = DEFAULT_AGENT_TYPES[:args.agents]
    else:
        agents = ALL_AGENT_TYPES[:min(args.agents, 6)]

    rounds = min(args.rounds, 3)

    # Header
    print(f"\n{C.BOLD}{C.CYAN}🐝 RUNE SWARM v2.0{C.RESET}")
    print(f"{C.DIM}One prompt enters. The best prompt survives.{C.RESET}\n")
    print(f"{C.BOLD}Prompt:{C.RESET}  {prompt[:100]}{'…' if len(prompt) > 100 else ''}")
    print(f"{C.BOLD}Agents:{C.RESET}  {len(agents)}  |  {C.BOLD}Model:{C.RESET} {model}  |  {C.BOLD}Rounds:{C.RESET} {rounds}")
    print(f"{'─' * 70}")
    print(f"\n{C.DIM}Spawning {len(agents)} agents...{C.RESET}")

    # Run swarm
    report = orchestrator.swarm(
        prompt=prompt,
        agent_types=agents,
        rounds=rounds,
        top_k=args.top_k,
    )

    # Display results
    print(f"\n{C.BOLD}📊 Tournament Results:{C.RESET}")
    for agent in report["agents"]:
        bar_len = int(agent["overall"] / 100 * 30)
        bar = f"{C.GREEN}{'█' * bar_len}{C.DIM}{'░' * (30 - bar_len)}{C.RESET}"

        medal = ""
        if agent["rank"] == 1: medal = f" {C.YELLOW}🏆{C.RESET}"
        elif agent["rank"] == 2: medal = f" 🥈"
        elif agent["rank"] == 3: medal = f" 🥉"

        scores = agent["scores"]
        print(f"\n  {'🎓' if agent['type'] == 'expert' else '🎨' if agent['type'] == 'creative' else '😈'} "
              f"{C.BOLD}#{agent['rank']} {agent['name']}{C.RESET}{medal}  "
              f"{C.DIM}({agent['time_sec']}s, {agent['tokens_out']} tok){C.RESET}")
        print(f"   {bar} {C.BOLD}{agent['overall']}{C.RESET}/100")
        print(f"   {C.DIM}C:{scores.get('conatus', 0)} R:{scores.get('ratio', 0)} "
              f"L:{scores.get('laetitia', 0)} N:{scores.get('natura', 0)}{C.RESET}")

        if args.verbose:
            preview = agent["response"][:300].replace('\n', '\n   ')
            print(f"   {C.DIM}{preview}{'…' if len(agent['response']) > 300 else ''}{C.RESET}")

    # Fusion result
    fusion = report["fusion"]
    print(f"\n{'═' * 70}")
    print(f"{C.BOLD}{C.MAGENTA}🔮 SWARM SYNTHESIS{C.RESET}")
    print(f"{'═' * 70}")

    improvement = fusion.get("improvement", 0)
    color = C.GREEN if improvement > 0 else C.RED
    print(f"   Score: {C.BOLD}{fusion['scores'].get('overall', 0)}{C.RESET}/100  "
          f"({color}{improvement:+.1f}% vs best agent{C.RESET})")
    print(f"{'─' * 70}")
    print(fusion["text"])
    print(f"{'─' * 70}")

    # Save report
    output_dir = Path(CONFIG["output_dir"]) / "swarm"
    output_dir.mkdir(parents=True, exist_ok=True)
    from datetime import datetime
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = output_dir / f"swarm_{ts}.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"\n{C.DIM}📁 Report saved: {report_path}{C.RESET}")

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
