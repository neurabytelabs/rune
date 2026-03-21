"""
🔮 Spinoza Validator — Local heuristic validation (no LLM needed).

Scores text on Spinoza's 4 pillars:
  Conatus  (30%) — Actionability, drive, empowerment
  Ratio    (35%) — Logic, structure, coherence
  Laetitia (15%) — Tone, clarity, constructive energy
  Natura   (20%) — Naturalness, flow, authenticity
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class PillarScore:
    """Score for a single Spinoza pillar."""
    name: str
    score: float  # 0.0 – 1.0
    weight: float
    reason: str = ""


@dataclass
class ValidationReport:
    """Full Spinoza validation report."""
    scores: Dict[str, PillarScore]
    overall: float  # 0.0 – 1.0
    grade: str
    summary: str
    word_count: int = 0
    char_count: int = 0


# ── Grade boundaries ─────────────────────────────────────────────────────────

GRADE_SCALE = [
    (0.90, "A"),
    (0.85, "A-"),
    (0.80, "B+"),
    (0.75, "B"),
    (0.70, "B-"),
    (0.65, "C+"),
    (0.60, "C"),
    (0.50, "D"),
    (0.00, "F"),
]


def _grade(score: float) -> str:
    for threshold, grade in GRADE_SCALE:
        if score >= threshold:
            return grade
    return "F"


# ── Pillar scorers ───────────────────────────────────────────────────────────

def _score_conatus(text: str) -> PillarScore:
    """Conatus — actionability, drive, empowerment."""
    score = 0.40
    reasons = []

    # Action words
    action_words = [
        "implement", "create", "build", "use", "apply", "run", "execute",
        "start", "deploy", "write", "design", "step", "install", "configure",
        "define", "set up", "launch", "test", "verify", "ensure",
        "yap", "oluştur", "kur", "uygula", "başla", "tanımla", "dene",
    ]
    found = sum(1 for w in action_words if w in text.lower())
    if found >= 5:
        score += 0.20
        reasons.append(f"{found} action words")
    elif found >= 2:
        score += 0.10
        reasons.append(f"{found} action words")

    # Numbered steps
    steps = len(re.findall(r'^\s*\d+[\.\)]\s', text, re.M))
    if steps >= 5:
        score += 0.15
        reasons.append(f"{steps} numbered steps")
    elif steps >= 2:
        score += 0.08
        reasons.append(f"{steps} steps")

    # Code blocks
    code_blocks = text.count('```')
    if code_blocks >= 4:
        score += 0.10
        reasons.append("code examples")
    elif code_blocks >= 2:
        score += 0.05

    # Bullet points
    bullets = len(re.findall(r'^\s*[-*]\s', text, re.M))
    if bullets >= 3:
        score += 0.05

    # Imperative mood indicators
    imperatives = len(re.findall(r'(?:^|\.\s+)[A-Z][a-z]+\s', text))
    if imperatives >= 3:
        score += 0.05

    return PillarScore(
        name="conatus",
        score=min(score, 1.0),
        weight=0.30,
        reason=", ".join(reasons) if reasons else "moderate actionability",
    )


def _score_ratio(text: str) -> PillarScore:
    """Ratio — logic, structure, coherence."""
    score = 0.45
    reasons = []

    # Headings
    headings = len(re.findall(r'^#+\s', text, re.M))
    if headings >= 4:
        score += 0.15
        reasons.append(f"{headings} sections")
    elif headings >= 2:
        score += 0.08
        reasons.append(f"{headings} sections")

    # Logical connectors
    connectors = [
        "because", "therefore", "however", "since", "thus", "consequently",
        "furthermore", "moreover", "although", "nevertheless", "specifically",
        "in contrast", "as a result", "for example", "in particular",
        "çünkü", "dolayısıyla", "ancak", "bununla birlikte", "özellikle",
        "sonuç olarak", "örneğin", "bu nedenle",
    ]
    found = sum(1 for c in connectors if c in text.lower())
    if found >= 5:
        score += 0.15
        reasons.append(f"{found} logical connectors")
    elif found >= 2:
        score += 0.08
        reasons.append(f"{found} connectors")

    # Word count — too short = low structure potential
    words = len(text.split())
    if words < 30:
        score -= 0.15
        reasons.append("very short")
    elif words < 80:
        score -= 0.05
    elif words > 200:
        score += 0.05

    # Paragraphs (double newlines)
    paras = text.count('\n\n')
    if 3 <= paras <= 15:
        score += 0.05
        reasons.append("well-paragraphed")
    elif paras > 20:
        score -= 0.05

    # Lists (ordered or unordered)
    lists = len(re.findall(r'^\s*[-*\d]\s', text, re.M))
    if lists >= 3:
        score += 0.05

    return PillarScore(
        name="ratio",
        score=min(max(score, 0.0), 1.0),
        weight=0.35,
        reason=", ".join(reasons) if reasons else "moderate structure",
    )


def _score_laetitia(text: str) -> PillarScore:
    """Laetitia — tone, clarity, constructive energy."""
    score = 0.60
    reasons = []

    # Positive / constructive tone
    positive = [
        "excellent", "powerful", "effective", "best", "optimal", "key",
        "important", "essential", "valuable", "benefit", "advantage",
        "improve", "enhance", "strengthen", "succeed", "achieve",
        "mükemmel", "güçlü", "etkili", "önemli", "değerli", "başarılı",
    ]
    found = sum(1 for w in positive if w in text.lower())
    if found >= 4:
        score += 0.15
        reasons.append("constructive tone")
    elif found >= 2:
        score += 0.08

    # Negative / hedging / AI-slop
    negative = [
        "i'm sorry", "i cannot", "as an ai", "unfortunately", "i apologize",
        "i don't have", "i'm not able", "maalesef", "yapamam",
    ]
    neg_found = sum(1 for w in negative if w in text.lower())
    if neg_found >= 2:
        score -= 0.20
        reasons.append("excessive hedging")
    elif neg_found == 1:
        score -= 0.08

    # Exclamation overuse
    excl = text.count('!')
    if excl > 10:
        score -= 0.10
        reasons.append("exclamation overuse")

    # ALL CAPS sections (shouting)
    caps_words = len(re.findall(r'\b[A-Z]{4,}\b', text))
    if caps_words > 5:
        score -= 0.05

    return PillarScore(
        name="laetitia",
        score=min(max(score, 0.0), 1.0),
        weight=0.15,
        reason=", ".join(reasons) if reasons else "balanced tone",
    )


def _score_natura(text: str) -> PillarScore:
    """Natura — naturalness, flow, authenticity."""
    score = 0.55
    reasons = []

    # Sentence length variety (good writing has varied sentence lengths)
    sentences = re.split(r'[.!?]\s+', text)
    if len(sentences) > 3:
        lengths = [len(s.split()) for s in sentences if s.strip()]
        if lengths:
            avg = sum(lengths) / len(lengths)
            variance = sum((l - avg) ** 2 for l in lengths) / len(lengths)
            if 5 < variance < 200:
                score += 0.15
                reasons.append("natural sentence variety")
            elif variance <= 5:
                score -= 0.05
                reasons.append("monotonous rhythm")

    # AI-slop detection
    slop_phrases = [
        "as an ai language model", "i'd be happy to", "certainly!",
        "great question", "absolutely!", "sure thing", "of course!",
        "let me help you", "here's a comprehensive",
        "in today's rapidly evolving", "it's worth noting that",
        "delve", "tapestry", "landscape", "in conclusion",
    ]
    slop_found = sum(1 for p in slop_phrases if p in text.lower())
    if slop_found >= 3:
        score -= 0.25
        reasons.append(f"{slop_found} AI-slop phrases")
    elif slop_found >= 1:
        score -= 0.10
        reasons.append("minor AI patterns")

    # Paragraph distribution
    if 2 <= text.count('\n\n') <= 12:
        score += 0.10
        reasons.append("good flow")

    # Not starting with "I" (more natural for expert content)
    if not text.strip().startswith("I ") and not text.strip().startswith("I'"):
        score += 0.05

    # Conversational markers (natural)
    natural_markers = ["—", "–", "...", "(", ":", ";"]
    marker_count = sum(text.count(m) for m in natural_markers)
    if 3 <= marker_count <= 20:
        score += 0.10
        reasons.append("natural punctuation")

    return PillarScore(
        name="natura",
        score=min(max(score, 0.0), 1.0),
        weight=0.20,
        reason=", ".join(reasons) if reasons else "moderate naturalness",
    )


# ── Main Validator ───────────────────────────────────────────────────────────

class SpinozaValidator:
    """Heuristic Spinoza validator — no LLM calls needed."""

    def validate(self, text: str) -> ValidationReport:
        """Validate text and return a full report."""
        if not text or not text.strip():
            empty_scores = {
                "conatus": PillarScore("conatus", 0.0, 0.30, "empty text"),
                "ratio": PillarScore("ratio", 0.0, 0.35, "empty text"),
                "laetitia": PillarScore("laetitia", 0.0, 0.15, "empty text"),
                "natura": PillarScore("natura", 0.0, 0.20, "empty text"),
            }
            return ValidationReport(
                scores=empty_scores, overall=0.0, grade="F",
                summary="Empty or whitespace-only text.",
                word_count=0, char_count=0,
            )

        scores = {
            "conatus": _score_conatus(text),
            "ratio": _score_ratio(text),
            "laetitia": _score_laetitia(text),
            "natura": _score_natura(text),
        }

        overall = sum(s.score * s.weight for s in scores.values())
        grade = _grade(overall)
        words = len(text.split())

        # Build summary
        best = max(scores.values(), key=lambda s: s.score)
        worst = min(scores.values(), key=lambda s: s.score)
        summary = f"Strongest: {best.name} ({best.score:.2f}), Weakest: {worst.name} ({worst.score:.2f})"

        return ValidationReport(
            scores=scores,
            overall=round(overall, 4),
            grade=grade,
            summary=summary,
            word_count=words,
            char_count=len(text),
        )

    def format_report(self, report: ValidationReport) -> str:
        """Format a validation report for terminal display."""
        lines = []
        lines.append("  ╔══════════════════════════════════════╗")
        lines.append("  ║  🔮 Spinoza Validation Report        ║")
        lines.append("  ╚══════════════════════════════════════╝")
        lines.append("")

        for name, pillar in report.scores.items():
            bar_len = int(pillar.score * 10)
            bar = "█" * bar_len + "░" * (10 - bar_len)
            weight_pct = int(pillar.weight * 100)
            lines.append(
                f"  {name:<12} {bar} {pillar.score:.2f}  "
                f"(w:{weight_pct}%)  {pillar.reason}"
            )

        lines.append("")
        lines.append(f"  Overall: {report.overall:.2f}  Grade: {report.grade}")
        lines.append(f"  {report.summary}")
        lines.append(f"  Words: {report.word_count}  Chars: {report.char_count}")

        return "\n".join(lines)
