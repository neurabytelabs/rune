"""
ᚷ WAND Bind — The Alchemy Spell.

Transmutes two raw ideas into ONE emergent rune (a "bindrune") and inscribes
it into the grimoire. Unlike `fuse` (mechanical prompt concatenation), `bind`
is alchemical: an LLM finds the *tension* between two ideas and births a third
thing neither parent could produce alone.

    wand bind "minimalism" "CRM dashboard"
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Optional

from rune.cli.helpers import (
    C,
    CONFIG,
    PROMPTS_DIR,
    print_banner,
    print_error,
    print_info,
    print_success,
    print_warn,
    section,
    llm_call,
    spinoza_validate,
    print_spinoza_report,
)

# Bold alchemist: bind reaches for distant, surprising fusions.
BIND_TEMPERATURE = 0.9
# Headroom so a full 8-layer rune (verbose in TR) never truncates mid-tag.
BIND_MAX_TOKENS = 16000

# ── The heart of the spell ────────────────────────────────────────────────────
BIND_SYSTEM = r"""You are the BINDER — a runic alchemist in the RUNE grimoire tradition.

A bindrune is two runes carved into a single glyph: not stacked, but FUSED,
until a third meaning emerges that neither carried alone. That is your craft.

You receive two raw ideas. You do NOT combine them. You TRANSMUTE them —
forging a new rune whose essence lives in the *tension* between the two.

=== THE ONE LAW (read twice) ===
The output must be a genuine THIRD thing.
If a reader could split your rune back into "the A part" and "the B part,"
you have FAILED — you concatenated, you did not transmute.
The seam must vanish. 1 + 1 = a new 1.

=== TEMPERAMENT (you are a BOLD alchemist) ===
Favor the surprising over the safe. The further apart the two ideas seem,
the brighter the spark — distance is FUEL, not an obstacle.
A pairing that looks absurd hides the most original rune;
your job is to find it, not to flinch. Reach for the unexpected emergent essence,
not the obvious overlap.
You NEVER refuse and NEVER hedge. Every pairing yields a rune — no exceptions,
no apologies, no "these don't fit" caveats. If the bond is hard, that is the work.

=== THE THREE FIRES (your cognitive method — perform silently, then output) ===
FIRE 1 — DISTILL
  Strip each idea to its single core principle. Not its surface, its drive.
FIRE 2 — STRIKE
  Find where the two principles CLASH, and where they amplify.
  The clash is the spark — chase the boldest, least obvious collision,
  not the comfortable overlap. Name the central tension in one sentence.
FIRE 3 — EMERGE
  Resolve the tension into a NEW principle that needs both parents to exist.
  Give it an evocative single-concept name (NOT "a_b", NOT a hyphenation).

=== GROUNDING (Spinoza — the rune is scored on these; write toward them) ===
  Ratio    (35%) — logically coherent, well-structured.
  Conatus  (30%) — empowers action; a real expert could USE it today.
  Natura   (20%) — reads naturally, as if it always existed.
  Laetitia (15%) — clear, constructive, alive — not corporate sludge.

=== OUTPUT CONTRACT (emit ONLY this — a complete grimoire rune, no preamble) ===
---
domain: <one of: coding | writing | analysis | creative | aiml | hybrid>
version: "2.0"
born_from: ["<idea A>", "<idea B>"]
tension: "<the one-sentence central tension from FIRE 2>"
---

# <emoji> <Human Title of the Emergent Rune>

## Category: <DOMAIN UPPERCASE>
## Complexity: L<1-5>
## Description: <one line — what this rune does>

## Template

```xml
<system>
  <!-- L1: Identity --> <identity>...</identity>
  <!-- L2: Mission --> <mission>...</mission>
  <!-- L3: Constraints --> <constraints>...</constraints>
  <!-- L4: Methodology --> <methodology>...</methodology>
  <!-- L5: Output --> <output><format>...</format></output>
  <!-- L6: Error Taxonomy --> <errors>...</errors>
  <!-- L7: Personalization --> <personalization>{{TUNABLE}}</personalization>
  <!-- L8: Context --> <context>{{USER SUPPLIES}}</context>
</system>
```

---
*Bound by RUNE — <idea A> + <idea B>*

LANGUAGE: Detect the language of the two IDEAS themselves and write ALL prose
(title, description, identity, mission, etc.) in that language. Keep XML tag
names in English. No explanation before or after — the rune speaks for itself."""


# Transliterate diacritics so grimoire filenames stay ASCII (matches the
# existing convention, e.g. "Gölge Defter" -> "golge_defter").
_TRANSLIT = str.maketrans(
    {
        "ç": "c",
        "ğ": "g",
        "ı": "i",
        "ö": "o",
        "ş": "s",
        "ü": "u",
        "Ç": "c",
        "Ğ": "g",
        "İ": "i",
        "Ö": "o",
        "Ş": "s",
        "Ü": "u",
        "â": "a",
        "î": "i",
        "û": "u",
        "é": "e",
        "ñ": "n",
    }
)


def _slugify(title: str) -> str:
    """Turn a rune title into a grimoire filename stem."""
    # Strip leading emoji / non-word symbols and markdown heading marks.
    t = title.strip().lstrip("#").strip()
    t = re.sub(r"^[^\w]+", "", t)  # drop leading emoji/symbols
    t = t.lower().translate(_TRANSLIT)
    t = re.sub(r"^the\s+", "", t)  # "The Sovereign Collider" -> "sovereign collider"
    t = re.sub(r"[^a-z0-9]+", "_", t).strip("_")
    return t or "bound_rune"


def _derive_name(rune_text: str) -> str:
    """Pull a filename stem from the rune's `# Title` heading."""
    for line in rune_text.splitlines():
        line = line.strip()
        if line.startswith("# "):
            return _slugify(line)
    return "bound_rune"


def cmd_bind(args: argparse.Namespace) -> None:
    """Transmute two ideas into one emergent rune."""
    print_banner()

    idea_a = args.idea_a.strip()
    idea_b = args.idea_b.strip()
    if not idea_a or not idea_b:
        print_error("Bind needs two ideas.")
        print_info('Usage: wand bind "idea A" "idea B" [--name x] [--dry]')
        return

    model = args.model or CONFIG.get("model")
    section("ᚷ Bind — Transmutation")
    print(f"  {C.CYAN}{idea_a}{C.RESET}  {C.GRAY}⊕{C.RESET}  {C.CYAN}{idea_b}{C.RESET}")
    print(f"  {C.GRAY}Forging emergent rune… (bold alchemy, T={BIND_TEMPERATURE}){C.RESET}\n")

    # Language-neutral wrapper: the model infers language from the ideas.
    user_msg = f"IDEA A: {idea_a}\nIDEA B: {idea_b}\n\nTransmute."

    # Bold temperament + headroom for a full 8-layer rune — for this call only.
    prev_temp = CONFIG.get("temperature")
    prev_max = CONFIG.get("max_tokens")
    CONFIG["temperature"] = BIND_TEMPERATURE
    CONFIG["max_tokens"] = max(int(prev_max or 0), BIND_MAX_TOKENS)
    try:
        rune_text = llm_call(user_msg, model=model, system=BIND_SYSTEM, track=True).strip()
    except Exception as e:
        print_error(f"Transmutation failed: {e}")
        return
    finally:
        if prev_temp is not None:
            CONFIG["temperature"] = prev_temp
        if prev_max is not None:
            CONFIG["max_tokens"] = prev_max

    if not rune_text:
        print_error("The fires produced nothing. Try again.")
        return

    section("ᚷ Emergent Rune")
    print(f"{C.CYAN}{rune_text}{C.RESET}")

    # Spinoza score — the rune is graded like any spell.
    try:
        report = spinoza_validate(rune_text, model=model)
        print()
        print_spinoza_report(report)
    except Exception:
        pass  # scoring is informational; never block the bind

    if args.output:
        Path(args.output).write_text(rune_text, encoding="utf-8")
        print_success(f"Output written to {args.output}")

    if args.dry:
        print_info("Dry run — rune not inscribed into the grimoire.")
        return

    # Inscribe into the grimoire.
    name = args.name.strip() if args.name else _derive_name(rune_text)
    name = _slugify(name) if args.name else name
    PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
    fp = PROMPTS_DIR / f"{name}.md"
    if fp.exists():
        print_warn(f"A rune named '{name}' already exists — saving as '{name}_bound'.")
        fp = PROMPTS_DIR / f"{name}_bound.md"
    fp.write_text(rune_text + "\n", encoding="utf-8")
    print_success(f"ᚷ Rune inscribed into the grimoire: {fp.name}")
    print_info(f'Cast it: wand cast "…" --rune {fp.stem}')
