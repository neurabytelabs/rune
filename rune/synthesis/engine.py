"""
🔮 SYNTHESIS Engine — Multi-Prompt Fusion

Fuses multiple prompts into a single, powerful mega-prompt.
Pure Python — no LLM calls. Uses string manipulation + templates.

Strategies:
  - layered: Each prompt becomes a distinct layer (L0, L1, ...)
  - merged:  All prompts blended into a single unified flow
  - chain:   Prompts linked sequentially (output of one feeds the next)
"""

from __future__ import annotations

import textwrap
from typing import Optional

# ── Templates ────────────────────────────────────────────────────────────────

LAYERED_TEMPLATE = """\
# 🔮 SYNTHESIZED PROMPT (Layered Fusion)
# {count} prompts fused into a multi-layer directive.

{layers}

---
⚡ All layers above are active simultaneously.
Apply each layer's directives in order of priority (Layer 0 = highest).
When layers conflict, higher-numbered layers refine — never override — lower ones.
"""

LAYER_BLOCK = """\
## Layer {index} — Directive #{human_index}
{content}
"""

MERGED_TEMPLATE = """\
# 🔮 SYNTHESIZED PROMPT (Merged Fusion)
# {count} prompts unified into a single directive.

You must embody ALL of the following roles and constraints simultaneously:

{merged_body}

---
⚡ Integrate all directives above into every response.
No directive is optional — they form a single unified identity.
"""

CHAIN_TEMPLATE = """\
# 🔮 SYNTHESIZED PROMPT (Chain Fusion)
# {count} prompts linked in sequential chain.

Follow these directives in strict sequential order.
Each step builds upon the previous one.

{chain_body}

---
⚡ Process each step sequentially. The output of each step
becomes the context for the next. Final output must reflect
all steps in the chain.
"""

CHAIN_STEP = """\
### Step {index}. {summary}
{content}
→ Apply this before proceeding to the next step.
"""

STRATEGIES = ("layered", "merged", "chain")


# ── Engine ───────────────────────────────────────────────────────────────────

class SynthesisEngine:
    """
    Fuses multiple prompts into one mega-prompt.

    Usage:
        engine = SynthesisEngine()
        result = engine.fuse([
            "Sen bir Python uzmanısın",
            "Güvenlik odaklı kod yaz",
            "Test driven development uygula",
        ], strategy="layered")
    """

    def fuse(
        self,
        prompts: list[str],
        strategy: str = "layered",
        validate: bool = True,
    ) -> "FusionResult":
        """
        Fuse multiple prompts into one.

        Args:
            prompts: List of prompt strings to fuse.
            strategy: "layered", "merged", or "chain".
            validate: Run Spinoza validation on the result.

        Returns:
            FusionResult with fused text and optional validation report.
        """
        if not prompts:
            raise ValueError("At least one prompt is required.")

        # Clean up
        prompts = [p.strip() for p in prompts if p.strip()]
        if not prompts:
            raise ValueError("All prompts are empty.")

        if strategy not in STRATEGIES:
            raise ValueError(
                f"Unknown strategy '{strategy}'. Choose from: {', '.join(STRATEGIES)}"
            )

        if strategy == "layered":
            fused = self._fuse_layered(prompts)
        elif strategy == "merged":
            fused = self._fuse_merged(prompts)
        elif strategy == "chain":
            fused = self._fuse_chain(prompts)

        # Spinoza validation
        report = None
        if validate:
            try:
                from rune.core.validator import SpinozaValidator
                v = SpinozaValidator()
                report = v.validate(fused)
            except ImportError:
                pass

        return FusionResult(
            text=fused,
            strategy=strategy,
            prompt_count=len(prompts),
            spinoza_report=report,
        )

    # ── Strategies ───────────────────────────────────────────────────────

    def _fuse_layered(self, prompts: list[str]) -> str:
        layers = []
        for i, p in enumerate(prompts):
            layers.append(LAYER_BLOCK.format(
                index=i, human_index=i + 1, content=p,
            ))
        return LAYERED_TEMPLATE.format(
            count=len(prompts),
            layers="\n".join(layers),
        )

    def _fuse_merged(self, prompts: list[str]) -> str:
        numbered = []
        for i, p in enumerate(prompts, 1):
            numbered.append(f"{i}. {p}")
        return MERGED_TEMPLATE.format(
            count=len(prompts),
            merged_body="\n\n".join(numbered),
        )

    def _fuse_chain(self, prompts: list[str]) -> str:
        steps = []
        for i, p in enumerate(prompts, 1):
            # Extract a short summary (first line or first 60 chars)
            summary = p.split("\n")[0][:60].rstrip(".")
            steps.append(CHAIN_STEP.format(
                index=i, summary=summary, content=p,
            ))
        return CHAIN_TEMPLATE.format(
            count=len(prompts),
            chain_body="\n".join(steps),
        )


# ── Result ───────────────────────────────────────────────────────────────────

class FusionResult:
    """Result of a prompt fusion operation."""

    def __init__(
        self,
        text: str,
        strategy: str,
        prompt_count: int,
        spinoza_report=None,
    ):
        self.text = text
        self.strategy = strategy
        self.prompt_count = prompt_count
        self.spinoza_report = spinoza_report

    @property
    def spinoza_score(self) -> Optional[float]:
        if self.spinoza_report:
            return self.spinoza_report.overall_score
        return None

    def __str__(self) -> str:
        return self.text
