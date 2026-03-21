"""
📜 WAND Lineage Command — View prompt ancestry and evolution history.
"""

from __future__ import annotations

import argparse
import json

from rune.cli.helpers import (
    C, print_banner, print_info, print_error, print_meta, section,
)


def cmd_lineage(args: argparse.Namespace) -> None:
    """View prompt lineage and evolution history."""
    print_banner()

    from rune.core.oracle import Oracle
    oracle = Oracle()

    if hasattr(args, "lineage_id") and args.lineage_id:
        # Show specific lineage chain
        lineage_id = args.lineage_id
        chain = oracle.get_lineage_chain(lineage_id)
        if not chain:
            print_error(f"Lineage '{lineage_id}' not found.")
            return

        section(f"📜 Lineage Chain: {lineage_id}")
        print(oracle.format_lineage_chain(chain))
    else:
        # Show recent lineage
        limit = getattr(args, "limit", 10) or 10
        recent = oracle.get_recent_lineage(limit=limit)

        if not recent:
            print_info("No lineage records yet. Run 'wand cast' to start tracking.")
            return

        section(f"📜 Recent Prompt Lineage ({len(recent)} entries)")
        print(f"  {C.BOLD}{'ID':<28} {'Score':>6} {'Grade':>5} {'Feedback':>8} {'Model':<20} {'Prompt'}{C.RESET}")
        print(f"  {'─'*28} {'─'*6} {'─'*5} {'─'*8} {'─'*20} {'─'*30}")

        for entry in recent:
            score = entry["score"]
            color = C.GREEN if score >= 0.7 else C.YELLOW if score >= 0.5 else C.RED
            fb = entry.get("feedback") or "—"
            prompt_preview = entry["prompt"][:30].replace("\n", " ")

            print(
                f"  {C.DIM}{entry['id']:<28}{C.RESET} "
                f"{color}{score:>6.2f}{C.RESET} "
                f"{entry['grade']:>5} "
                f"{fb:>8} "
                f"{C.CYAN}{entry['model']:<20}{C.RESET} "
                f"{prompt_preview}"
            )

    if getattr(args, "json", False):
        recent = oracle.get_recent_lineage(limit=50)
        print(json.dumps(recent, indent=2, ensure_ascii=False))
