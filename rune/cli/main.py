"""
🪄 WAND CLI — Main entry point.
Modular argument parser routing to command modules.
"""

from __future__ import annotations

import argparse
import sys

from rune.cli.helpers import C, BANNER_PLAIN


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

    # lineage
    p = sub.add_parser("lineage", help="View prompt ancestry and evolution")
    p.add_argument("lineage_id", nargs="?", help="Specific lineage ID to trace")
    p.add_argument("--limit", "-l", type=int, default=10, help="Number of recent entries")

    # swarm
    p = sub.add_parser("swarm", help="Multi-agent prompt evolution")
    p.add_argument("prompt", nargs="+", help="Your prompt")
    p.add_argument("--agents", "-a", type=int, default=3,
                   help="Number of agents (3-6, default: 3)")
    p.add_argument("--rounds", "-r", type=int, default=1,
                   help="Evolution rounds (default: 1, max: 3)")
    p.add_argument("--all", action="store_true",
                   help="Use all 6 agent types")
    p.add_argument("--top-k", type=int, default=2,
                   help="Top K agents to fuse (default: 2)")

    # version
    sub.add_parser("version", help="Show version info")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.no_color or not sys.stdout.isatty():
        C.disable()
        import rune.cli.helpers as h
        h.BANNER = BANNER_PLAIN

    # Lazy imports to keep startup fast
    from rune.cli.cast import cmd_cast
    from rune.cli.commands import (
        cmd_inscribe, cmd_duel, cmd_grimoire, cmd_test, cmd_validate,
        cmd_forge, cmd_stats, cmd_cost, cmd_config, cmd_fuse, cmd_version,
    )
    from rune.cli.swarm_cmd import cmd_swarm
    from rune.cli.lineage_cmd import cmd_lineage

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
        "swarm": cmd_swarm,
        "lineage": cmd_lineage,
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
