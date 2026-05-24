"""
🔮 RUNE Oracle — Self-Improving Prompt Engine

Oracle provides:
1. Feedback loop — user rates outputs, feedback improves future enhances
2. Auto-refinement — if Spinoza score < threshold, auto re-enhance (max 2 rounds)
3. Lineage tracking — every prompt's ancestry chain
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
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
                has_feedback = data.get("feedback_grade")
                prompt_matches = domain.lower() in data.get("original_prompt", "").lower()
                if has_feedback and prompt_matches:
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

        return f"""The previous response to this prompt scored below threshold on quality
validation.

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
        lineage_id = (
            ts.strftime("%Y%m%d_%H%M%S")
            + f"_{abs(hash(original_prompt[:50])) % 10000:04d}"
        )

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
            chain.append(
                PromptLineage(
                    **{
                        k: v
                        for k, v in data.items()
                        if k in PromptLineage.__dataclass_fields__
                    }
                )
            )
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
                lines.append("  │")

        return "\n".join(lines)

    # ── GEPA-viz Export ─────────────────────────────────────────────────

    def export_gepa_run(
        self,
        lineage_id: Optional[str] = None,
        *,
        limit: int = 25,
        output_path: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """Export RUNE lineage as a GEPA-viz-compatible ``run.json``.

        GEPA-viz visualizes prompt-optimization candidates with this shape:
        ``examples`` plus a ``candidates`` map. RUNE is not GEPA, but its
        prompt lineage has the same useful primitives: candidate prompt,
        parent, score, model, feedback, and refinement strategy. This adapter
        keeps RUNE dependency-free while making prompt evolution inspectable
        with ``gepa-viz serve --run <file>``.
        """
        entries = self.get_lineage_chain(lineage_id) if lineage_id else [
            PromptLineage(**self._read_lineage(fp))
            for fp in sorted(self.lineage_dir.glob("*.json"), reverse=True)[:limit]
        ]

        # GEPA-viz expects parent references to candidate ids. RUNE lineage ids
        # are timestamp/hash strings, so map them to compact integer strings.
        entries = list(reversed(entries))
        id_map = {entry.id: str(i) for i, entry in enumerate(entries)}

        examples: list[dict[str, Any]] = []
        candidates: dict[str, dict[str, Any]] = {}

        for entry in entries:
            candidate_id = id_map[entry.id]
            parent = id_map.get(entry.parent_id) if entry.parent_id else None
            feedback_bits = []
            if entry.feedback_grade:
                feedback_bits.append(f"user feedback: {entry.feedback_grade}")
            if entry.feedback_note:
                feedback_bits.append(entry.feedback_note)
            if entry.refinement_round:
                feedback_bits.append(f"refinement round: {entry.refinement_round}")
            feedback = "; ".join(feedback_bits) or f"strategy: {entry.strategy}"

            examples.append({
                "lineage_id": entry.id,
                "prompt": entry.original_prompt,
                "ground_truth": {
                    "goal": "Higher Spinoza score with clearer RUNE structure",
                },
            })
            candidates[candidate_id] = {
                "prompt": entry.enhanced_prompt or entry.original_prompt,
                "parent": parent,
                "score": entry.spinoza_score,
                "predictions": [{
                    "prediction": {
                        "lineage_id": entry.id,
                        "grade": entry.grade,
                        "model": entry.model,
                        "strategy": entry.strategy,
                    },
                    "score": entry.spinoza_score,
                }],
                "minibatch": [{
                    "example": {"prompt": entry.original_prompt},
                    "parent_prediction": (
                        {"parent_id": entry.parent_id} if entry.parent_id else None
                    ),
                    "parent_score": None,
                    "prediction": {"enhanced_prompt": entry.enhanced_prompt},
                    "score": entry.spinoza_score,
                    "feedback": feedback,
                }],
            }

        run = {"examples": examples, "candidates": candidates}
        if output_path is not None:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps(run, indent=2, ensure_ascii=False), encoding="utf-8")
        return run

    def _read_lineage(self, fp: Path) -> Dict[str, Any]:
        data = json.loads(fp.read_text(encoding="utf-8"))
        return {k: v for k, v in data.items() if k in PromptLineage.__dataclass_fields__}
