"""
🔮 RUNE Oracle — Self-Improving Prompt Engine

Oracle provides:
1. Feedback loop — user rates outputs, feedback improves future enhances
2. Auto-refinement — if Spinoza score < threshold, auto re-enhance (max 2 rounds)
3. Lineage tracking — every prompt's ancestry chain
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from rune.core.validator import SpinozaValidator


@dataclass
class PromptLineage:
    """Tracks the ancestry of an enhanced prompt."""
    id: str
    timestamp: str
    original_prompt: str
    enhanced_prompt: str
    model: str
    spinoza_score: float
    grade: str
    parent_id: Optional[str] = None
    feedback_grade: Optional[str] = None  # User feedback A-F
    feedback_note: Optional[str] = None
    rune_template: Optional[str] = None
    refinement_round: int = 0
    strategy: str = "default"  # default, oracle-refined, swarm-best


class Oracle:
    """Self-improving prompt engine with feedback loops and auto-refinement."""

    def __init__(
        self,
        lineage_dir: Optional[Path] = None,
        spinoza_threshold: float = 0.6,
        max_refinement_rounds: int = 2,
    ):
        self.lineage_dir = lineage_dir or Path.home() / ".rune" / "lineage"
        self.lineage_dir.mkdir(parents=True, exist_ok=True)
        self.spinoza_threshold = spinoza_threshold
        self.max_rounds = max_refinement_rounds
        self.validator = SpinozaValidator()

    # ── Feedback ─────────────────────────────────────────────────────────

    def record_feedback(
        self,
        lineage_id: str,
        grade: str,
        note: str = "",
    ) -> None:
        """Record user feedback for a prompt result."""
        fp = self.lineage_dir / f"{lineage_id}.json"
        if fp.exists():
            data = json.loads(fp.read_text())
            data["feedback_grade"] = grade.upper()
            data["feedback_note"] = note
            fp.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    def get_domain_feedback(self, domain: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recent feedback for a domain to inform future enhancements."""
        results = []
        for fp in sorted(self.lineage_dir.glob("*.json"), reverse=True):
            try:
                data = json.loads(fp.read_text())
                if data.get("feedback_grade") and domain.lower() in data.get("original_prompt", "").lower():
                    results.append({
                        "grade": data["feedback_grade"],
                        "note": data.get("feedback_note", ""),
                        "strategy": data.get("strategy", ""),
                        "spinoza": data.get("spinoza_score", 0),
                    })
                    if len(results) >= limit:
                        break
            except Exception:
                continue
        return results

    # ── Auto-Refinement ──────────────────────────────────────────────────

    def should_refine(self, text: str) -> bool:
        """Check if the output quality warrants auto-refinement."""
        report = self.validator.validate(text)
        return report.overall < self.spinoza_threshold

    def build_refinement_prompt(
        self,
        original_prompt: str,
        output: str,
        report_summary: str,
        round_num: int,
    ) -> str:
        """Build a refinement prompt that addresses weak areas."""
        strategies = [
            "Focus on making the response more actionable with concrete steps and examples.",
            "Restructure for better logical flow with clear sections and transitions.",
            "Improve naturalness — avoid AI-slop phrases, vary sentence length.",
        ]
        strategy = strategies[round_num % len(strategies)]

        return f"""The previous response to this prompt scored below threshold on quality validation.

ORIGINAL PROMPT:
{original_prompt}

PREVIOUS OUTPUT (needs improvement):
{output[:2000]}

QUALITY ISSUES:
{report_summary}

REFINEMENT STRATEGY (Round {round_num + 1}):
{strategy}

Generate an improved version that addresses these quality issues.
Be concrete, structured, and natural. Avoid filler phrases."""

    # ── Lineage ──────────────────────────────────────────────────────────

    def create_lineage(
        self,
        original_prompt: str,
        enhanced_prompt: str,
        model: str,
        spinoza_score: float,
        grade: str,
        parent_id: Optional[str] = None,
        rune_template: Optional[str] = None,
        refinement_round: int = 0,
        strategy: str = "default",
    ) -> PromptLineage:
        """Create and save a lineage record."""
        ts = datetime.now()
        lineage_id = ts.strftime("%Y%m%d_%H%M%S") + f"_{abs(hash(original_prompt[:50])) % 10000:04d}"

        lineage = PromptLineage(
            id=lineage_id,
            timestamp=ts.isoformat(),
            original_prompt=original_prompt,
            enhanced_prompt=enhanced_prompt[:3000],  # Cap storage
            model=model,
            spinoza_score=spinoza_score,
            grade=grade,
            parent_id=parent_id,
            rune_template=rune_template,
            refinement_round=refinement_round,
            strategy=strategy,
        )

        fp = self.lineage_dir / f"{lineage_id}.json"
        fp.write_text(json.dumps(asdict(lineage), indent=2, ensure_ascii=False))

        return lineage

    def get_lineage_chain(self, lineage_id: str) -> List[PromptLineage]:
        """Walk up the ancestry chain of a prompt."""
        chain = []
        current_id = lineage_id

        while current_id:
            fp = self.lineage_dir / f"{current_id}.json"
            if not fp.exists():
                break
            data = json.loads(fp.read_text())
            chain.append(PromptLineage(**{k: v for k, v in data.items() if k in PromptLineage.__dataclass_fields__}))
            current_id = data.get("parent_id")

        return chain

    def get_recent_lineage(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent lineage records."""
        results = []
        for fp in sorted(self.lineage_dir.glob("*.json"), reverse=True):
            if len(results) >= limit:
                break
            try:
                data = json.loads(fp.read_text())
                results.append({
                    "id": data["id"],
                    "timestamp": data["timestamp"],
                    "prompt": data["original_prompt"][:80],
                    "score": data["spinoza_score"],
                    "grade": data["grade"],
                    "model": data["model"],
                    "strategy": data.get("strategy", "default"),
                    "feedback": data.get("feedback_grade"),
                })
            except Exception:
                continue
        return results

    def format_lineage_chain(self, chain: List[PromptLineage]) -> str:
        """Format a lineage chain for terminal display."""
        if not chain:
            return "  No lineage found."

        lines = []
        for i, entry in enumerate(chain):
            prefix = "  └─" if i == len(chain) - 1 else "  ├─"
            connector = "    " if i == len(chain) - 1 else "  │ "

            prompt_preview = entry.original_prompt[:60].replace("\n", " ")
            feedback = f" [User: {entry.feedback_grade}]" if entry.feedback_grade else ""
            strategy = f" ({entry.strategy})" if entry.strategy != "default" else ""

            lines.append(
                f"{prefix} Round {entry.refinement_round} | "
                f"Score: {entry.spinoza_score:.2f} ({entry.grade}){feedback}{strategy}"
            )
            lines.append(f"{connector} {entry.model} | {entry.timestamp[:16]}")
            lines.append(f"{connector} \"{prompt_preview}...\"")
            if i < len(chain) - 1:
                lines.append(f"  │")

        return "\n".join(lines)
