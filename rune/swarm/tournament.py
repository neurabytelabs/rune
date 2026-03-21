"""
🏆 Swarm Tournament — Spinoza-based scoring and ranking.
Uses the local heuristic validator (no LLM needed for scoring).
"""

from __future__ import annotations

from rune.core.validator import SpinozaValidator


_validator = SpinozaValidator()


def score_response(text: str) -> dict:
    """Score a response using the Spinoza validator.
    Returns dict with pillar scores and overall (0-100 scale for swarm compat).
    """
    report = _validator.validate(text)

    return {
        "conatus": round(report.scores["conatus"].score * 25, 1),
        "ratio": round(report.scores["ratio"].score * 25, 1),
        "laetitia": round(report.scores["laetitia"].score * 25, 1),
        "natura": round(report.scores["natura"].score * 25, 1),
        "overall": round(report.overall * 100, 1),
        "grade": report.grade,
    }
