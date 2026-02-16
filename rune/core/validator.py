"""
🏛️ Spinoza Validator — "The Judge of Quality"

Validates prompt outputs against Spinoza's Ethics principles.
Port from panpsychism-cli (Rust) to Python.

Based on Baruch Spinoza's "Ethica Ordine Geometrico Demonstrata" (1677):
  - Conatus: "Each thing, as far as it lies in itself, strives to persevere
    in its being." (Ethics III, Prop. 6)
  - Ratio: The geometric method — knowledge through reason and logical order.
  - Laetitia: "Joy is a person's transition from a lesser to a greater
    perfection." (Ethics III, Prop. 11, Scholium)
  - Natura: "Deus sive Natura" — God or Nature as unified substance.

No external dependencies. Pure Python 3.10+.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


# ── Principles ───────────────────────────────────────────────────────────────

class SpinozaPrinciple(Enum):
    """The four validation axes drawn from Spinoza's Ethics."""
    CONATUS = "conatus"      # Self-preservation, growth drive
    RATIO = "ratio"          # Logical coherence, reason
    LAETITIA = "laetitia"    # Joy, positive transformation
    NATURA = "natura"         # Natural harmony, balance


# ── Keyword Dictionaries ─────────────────────────────────────────────────────

PRINCIPLE_KEYWORDS: dict[SpinozaPrinciple, list[str]] = {
    SpinozaPrinciple.CONATUS: [
        "grow", "learn", "create", "nurture", "protect", "evolve", "improve",
        "develop", "build", "achieve", "persist", "sustain", "advance",
        "progress", "empower", "enable", "strengthen", "cultivate", "flourish",
        "thrive",
        # Turkish
        "geliştir", "evrim", "büyü", "güçlen", "ilerle", "başar", "sürdür",
        "yarat", "kur", "inşa", "öğren", "koruma", "ilerleme", "güçlendir",
        "gelişim", "potansiyel", "hedef", "azim", "kararlılık", "motivasyon",
    ],
    SpinozaPrinciple.RATIO: [
        "therefore", "because", "thus", "consequently", "logically", "hence",
        "reasoning", "analysis", "evidence", "proof", "consistent", "coherent",
        "structured", "systematic", "rational", "deductive", "conclusion",
        "premise", "valid", "sound",
        # Turkish
        "çünkü", "dolayısıyla", "analiz", "mantık", "yapı", "sıra", "liste",
        "adım", "strateji", "plan", "sonuç", "neden", "kanıt", "tutarlı",
        "sistematik", "öncelikle", "ardından", "bundan dolayı", "mantıklı",
        "yapısal",
    ],
    SpinozaPrinciple.LAETITIA: [
        "hope", "inspire", "achieve", "joy", "delight", "satisfaction",
        "fulfillment", "clarity", "insight", "discovery", "breakthrough",
        "elegant", "beautiful", "harmonious", "enlighten", "illuminate",
        "uplift", "transcend", "wonder", "gratitude",
        # Turkish
        "mutluluk", "başarı", "harika", "mükemmel", "güzel", "ışık", "ilham",
        "keşif", "neşe", "pozitif", "umut", "sevgi", "tatmin", "heyecan",
        "muhteşem", "olağanüstü", "keyif", "huzur", "coşku", "şükran",
    ],
    SpinozaPrinciple.NATURA: [
        "balance", "harmony", "natural", "organic", "flow", "ecosystem",
        "symbiosis", "equilibrium", "integrate", "holistic", "unified",
        "connected", "sustainable", "resilient", "adaptive", "emergent",
        "synergy", "wholeness", "complement", "align",
        # Turkish
        "doğal", "tutarlı", "uyumlu", "akıcı", "bağlam", "bütün", "sistem",
        "ekosistem", "denge", "organik", "sürdürülebilir", "bütünsel",
        "entegre", "birleşik", "uyum", "akış", "dayanıklı", "adaptif",
        "sinerji", "tamamlayıcı",
    ],
}

# Turkish positive/negative words for sentiment analysis
_POSITIVE_WORDS_TR = frozenset([
    "iyi", "harika", "mükemmel", "muhteşem", "güzel", "başarılı", "etkili",
    "verimli", "güçlü", "açık", "basit", "yararlı", "faydalı", "olumlu",
    "ideal", "hoş", "olağanüstü", "süper", "pozitif", "sevgi", "mutlu",
    "keyifli", "huzurlu", "ilham", "umut", "neşe", "coşku", "tatmin",
])

_NEGATIVE_WORDS_TR = frozenset([
    "kötü", "berbat", "korkunç", "rezalet", "çirkin", "başarısız", "hata",
    "sorun", "problem", "zor", "karmaşık", "kafa karıştırıcı", "belirsiz",
    "dağınık", "kaos", "acı", "sinir", "can sıkıcı", "işe yaramaz", "zayıf",
    "olumsuz", "sıkıntı", "mutsuz", "üzücü",
])

# Turkish connectives for coherence analysis
_CONNECTIVES_TR = frozenset([
    "ancak", "ayrıca", "bunun yanı sıra", "ek olarak", "dolayısıyla",
    "sonuç olarak", "böylece", "bu nedenle", "bu yüzden", "öte yandan",
    "bununla birlikte", "benzer şekilde", "aynı zamanda", "aksine",
    "özellikle", "önemli olarak", "son olarak", "ilk olarak", "ikinci olarak",
    "ardından", "daha sonra", "aynı şekilde", "dahası", "üstelik", "öncelikle",
])

# Simple sentiment word lists for LAETITIA analysis
_POSITIVE_WORDS = frozenset([
    "good", "great", "excellent", "amazing", "wonderful", "fantastic",
    "brilliant", "perfect", "best", "happy", "love", "beautiful", "elegant",
    "success", "successful", "effective", "efficient", "powerful", "clear",
    "simple", "useful", "helpful", "better", "improve", "ideal", "pleasant",
    "remarkable", "outstanding", "superb", "exceptional", "positive",
])

_NEGATIVE_WORDS = frozenset([
    "bad", "terrible", "awful", "horrible", "worst", "poor", "ugly", "fail",
    "failure", "broken", "wrong", "error", "problem", "issue", "bug",
    "difficult", "complex", "confusing", "unclear", "messy", "chaos",
    "painful", "frustrating", "annoying", "useless", "weak", "negative",
])

# Transition / connective words for coherence analysis
_CONNECTIVES = frozenset([
    "however", "moreover", "furthermore", "additionally", "therefore",
    "consequently", "thus", "hence", "meanwhile", "nevertheless",
    "nonetheless", "similarly", "likewise", "conversely", "alternatively",
    "specifically", "particularly", "notably", "importantly", "finally",
    "first", "second", "third", "next", "then", "also", "besides",
])


# ── Data Classes ─────────────────────────────────────────────────────────────

@dataclass
class ValidationResult:
    """Result of validating text against a single Spinoza principle."""
    principle: SpinozaPrinciple
    score: float                # 0.0 – 1.0
    keywords_found: list[str]
    keyword_density: float
    explanation: str


@dataclass
class SpinozaReport:
    """Complete Spinoza validation report across all principles."""
    overall_score: float                                    # weighted average
    principle_scores: dict[SpinozaPrinciple, ValidationResult]
    passed: bool                                            # overall_score >= threshold
    grade: str                                              # A/B/C/D/F
    summary: str                                            # human-readable summary
    recommendations: list[str]                              # improvement suggestions
    timestamp: str


# ── Validator ────────────────────────────────────────────────────────────────

class SpinozaValidator:
    """
    Validates text against Spinoza's philosophical principles.

    Each principle is scored 0.0–1.0 using keyword analysis, structural
    heuristics, sentiment detection, and coherence checking. Scores are
    combined via configurable weights into an overall quality grade.

    Usage:
        validator = SpinozaValidator()
        report = validator.validate("Your text here...")
        print(validator.format_report(report))
    """

    DEFAULT_WEIGHTS: dict[SpinozaPrinciple, float] = {
        SpinozaPrinciple.CONATUS: 0.30,
        SpinozaPrinciple.RATIO: 0.35,
        SpinozaPrinciple.LAETITIA: 0.15,
        SpinozaPrinciple.NATURA: 0.20,
    }

    # Scaling factor so typical good text scores 0.6–0.8 on keywords alone
    _KEYWORD_SCALE: float = 25.0

    def __init__(
        self,
        threshold: float = 0.6,
        weights: Optional[dict[SpinozaPrinciple, float]] = None,
    ) -> None:
        self.threshold = threshold
        self.weights = weights or dict(self.DEFAULT_WEIGHTS)

    # ── Public API ───────────────────────────────────────────────────────

    def validate(self, text: str) -> SpinozaReport:
        """Run full Spinoza validation and return a report."""
        results: dict[SpinozaPrinciple, ValidationResult] = {}
        for principle in SpinozaPrinciple:
            results[principle] = self.validate_principle(text, principle)

        overall = sum(
            self.weights[p] * results[p].score for p in SpinozaPrinciple
        )
        overall = round(min(1.0, max(0.0, overall)), 4)
        grade = self._grade(overall)
        passed = overall >= self.threshold

        status = "PASSED ✅" if passed else "FAILED ❌"
        summary = (
            f"Spinoza validation {status} with score {overall:.2f} "
            f"(Grade {grade}, threshold {self.threshold:.2f})"
        )

        return SpinozaReport(
            overall_score=overall,
            principle_scores=results,
            passed=passed,
            grade=grade,
            summary=summary,
            recommendations=self._generate_recommendations(results),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def validate_principle(
        self, text: str, principle: SpinozaPrinciple
    ) -> ValidationResult:
        """Validate text against a single principle."""
        keywords = PRINCIPLE_KEYWORDS[principle]
        kw_score, found = self._calculate_keyword_score(text, keywords)
        words = text.lower().split()
        total_words = max(len(words), 1)
        density = len(found) / total_words

        # Blend keyword score with principle-specific heuristic
        if principle == SpinozaPrinciple.RATIO:
            bonus = self._structural_analysis(text)
            score = 0.5 * kw_score + 0.5 * bonus
        elif principle == SpinozaPrinciple.LAETITIA:
            bonus = self._sentiment_analysis(text)
            score = 0.5 * kw_score + 0.5 * bonus
        elif principle == SpinozaPrinciple.NATURA:
            bonus = self._coherence_check(text)
            score = 0.5 * kw_score + 0.5 * bonus
        else:  # CONATUS — pure keyword driven
            score = kw_score

        score = round(min(1.0, max(0.0, score)), 4)

        explanation = self._explain(principle, score, found)
        return ValidationResult(
            principle=principle,
            score=score,
            keywords_found=found,
            keyword_density=round(density, 4),
            explanation=explanation,
        )

    def format_report(self, report: SpinozaReport) -> str:
        """Format the report as a terminal-friendly box with bar charts."""
        w = 43  # inner width
        lines: list[str] = []
        lines.append(f"┌{'─' * w}┐")
        lines.append(f"│  🏛️  SPINOZA VALIDATION REPORT{' ' * (w - 32)}│")
        lines.append(f"├{'─' * w}┤")

        for p in SpinozaPrinciple:
            r = report.principle_scores[p]
            name = p.name.ljust(9)
            filled = round(r.score * 10)
            bar = "█" * filled + "░" * (10 - filled)
            icon = "✅" if r.score >= self.threshold else "❌"
            line = f"  {name} {bar}  {r.score:.2f}  {icon}"
            lines.append(f"│{line.ljust(w)}│")

        lines.append(f"├{'─' * w}┤")
        status = "PASSED" if report.passed else "FAILED"
        bottom = f"  OVERALL: {report.overall_score:.2f} | Grade: {report.grade} | {status}"
        lines.append(f"│{bottom.ljust(w)}│")

        if report.recommendations:
            lines.append(f"├{'─' * w}┤")
            for rec in report.recommendations[:4]:
                rec_line = f"  💡 {rec}"
                if len(rec_line) > w:
                    rec_line = rec_line[: w - 1] + "…"
                lines.append(f"│{rec_line.ljust(w)}│")

        lines.append(f"└{'─' * w}┘")
        return "\n".join(lines)

    # ── Private Helpers ──────────────────────────────────────────────────

    @staticmethod
    def _casefold_turkish(text: str) -> str:
        """Turkish-aware case folding: I→ı, İ→i (standard casefold mishandles these)."""
        text = text.replace("I", "ı").replace("İ", "i")
        return text.casefold()

    def _calculate_keyword_score(
        self, text: str, keywords: list[str]
    ) -> tuple[float, list[str]]:
        """Score based on keyword presence and density."""
        lower = self._casefold_turkish(text)
        words = lower.split()
        total = max(len(words), 1)

        found: list[str] = []
        match_count = 0
        for kw in keywords:
            kw_lower = self._casefold_turkish(kw)
            # Use unicode-aware word boundary; for multi-word keywords use simple 'in'
            if " " in kw_lower:
                hits = lower.count(kw_lower)
            else:
                pattern = rf"(?<!\w){re.escape(kw_lower)}[\w]*(?!\w)"
                hits = len(re.findall(pattern, lower, re.UNICODE))
            if hits:
                found.append(kw)
                match_count += hits

        density = match_count / total
        density_score = min(1.0, density * self._KEYWORD_SCALE)
        diversity_score = min(1.0, len(found) / max(len(keywords) * 0.15, 1))
        score = 0.6 * density_score + 0.4 * diversity_score
        return min(1.0, score), sorted(set(found))

    def _structural_analysis(self, text: str) -> float:
        """Heuristic structural quality score for RATIO.

        Rewards: paragraphs, bullet/numbered lists, headers, code blocks,
        longer well-structured text.
        """
        score = 0.0
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        if len(paragraphs) >= 2:
            score += 0.25
        if len(paragraphs) >= 4:
            score += 0.15

        # Lists (-, *, 1.)
        list_items = len(re.findall(r"^\s*[-*•]\s+", text, re.MULTILINE))
        list_items += len(re.findall(r"^\s*\d+[.)]\s+", text, re.MULTILINE))
        if list_items >= 2:
            score += 0.2

        # Headers (markdown)
        if re.search(r"^#{1,6}\s+", text, re.MULTILINE):
            score += 0.15

        # Code blocks
        if "```" in text or re.search(r"^    \S", text, re.MULTILINE):
            score += 0.15

        # Turkish structural keywords that imply logical ordering
        lower = self._casefold_turkish(text)
        tr_ordering = ["adım", "öncelikle", "ardından", "son olarak", "ilk olarak",
                        "ikinci olarak", "sonuç olarak", "sırasıyla"]
        tr_hits = sum(1 for kw in tr_ordering if kw in lower)
        if tr_hits >= 2:
            score += 0.2

        # Length bonus
        word_count = len(text.split())
        if word_count >= 50:
            score += 0.1

        return min(1.0, score)

    def _sentiment_analysis(self, text: str) -> float:
        """Simple positive/negative word ratio for LAETITIA (EN + TR)."""
        lower = self._casefold_turkish(text)
        words = re.findall(r"\b\w+\b", lower, re.UNICODE)
        if not words:
            return 0.5

        pos = sum(1 for w in words if w in _POSITIVE_WORDS or w in _POSITIVE_WORDS_TR)
        neg = sum(1 for w in words if w in _NEGATIVE_WORDS or w in _NEGATIVE_WORDS_TR)

        # Also check for positive Turkish sentences (exclamation, emoji-like patterns)
        pos_sentence_bonus = len(re.findall(r"[!]+", text)) * 0.02

        total = pos + neg
        if total == 0:
            return min(1.0, 0.5 + pos_sentence_bonus)

        ratio = pos / total
        return min(1.0, 0.4 + 0.6 * ratio + pos_sentence_bonus)

    def _coherence_check(self, text: str) -> float:
        """Check coherence for NATURA: sentence connectivity & flow (EN + TR)."""
        sentences = re.split(r"[.!?]+", text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
        if len(sentences) < 2:
            return 0.4

        score = 0.0
        lower = self._casefold_turkish(text)

        # Connective usage (EN + TR)
        words = re.findall(r"\b\w+\b", lower, re.UNICODE)
        conn_count = sum(1 for w in words if w in _CONNECTIVES or w in _CONNECTIVES_TR)
        # Also check multi-word Turkish connectives
        for conn in _CONNECTIVES_TR:
            if " " in conn and conn in lower:
                conn_count += 1
        conn_ratio = conn_count / max(len(words), 1)
        score += min(0.4, conn_ratio * 8)

        # Vocabulary overlap between adjacent sentences (topic consistency)
        overlaps = 0
        for i in range(len(sentences) - 1):
            w1 = set(re.findall(r"\b\w{3,}\b", self._casefold_turkish(sentences[i]), re.UNICODE))
            w2 = set(re.findall(r"\b\w{3,}\b", self._casefold_turkish(sentences[i + 1]), re.UNICODE))
            if w1 & w2:
                overlaps += 1
        if sentences:
            overlap_ratio = overlaps / max(len(sentences) - 1, 1)
            score += 0.4 * overlap_ratio

        # Length and sentence variety
        if len(sentences) >= 3:
            score += 0.2

        return min(1.0, score)

    def _grade(self, score: float) -> str:
        """Map score to letter grade."""
        if score >= 0.85:
            return "A"
        if score >= 0.70:
            return "B"
        if score >= 0.55:
            return "C"
        if score >= 0.40:
            return "D"
        return "F"

    def _generate_recommendations(
        self, results: dict[SpinozaPrinciple, ValidationResult]
    ) -> list[str]:
        """Suggest improvements for the weakest principles."""
        recs: list[str] = []
        sorted_results = sorted(results.items(), key=lambda x: x[1].score)

        tips: dict[SpinozaPrinciple, str] = {
            SpinozaPrinciple.CONATUS: (
                "Add growth-oriented language: develop, improve, evolve, build"
            ),
            SpinozaPrinciple.RATIO: (
                "Strengthen logical structure: use because/therefore, add lists or headers"
            ),
            SpinozaPrinciple.LAETITIA: (
                "Include positive, uplifting language: insight, clarity, discovery"
            ),
            SpinozaPrinciple.NATURA: (
                "Improve coherence and flow: use transitions, maintain topic consistency"
            ),
        }

        for principle, result in sorted_results:
            if result.score < 0.7:
                recs.append(
                    f"{principle.name} ({result.score:.2f}): {tips[principle]}"
                )

        return recs

    def _explain(
        self,
        principle: SpinozaPrinciple,
        score: float,
        found: list[str],
    ) -> str:
        """Generate a brief explanation for a principle score."""
        level = "strong" if score >= 0.7 else "moderate" if score >= 0.4 else "weak"
        kw_str = ", ".join(found[:5]) if found else "none"
        return (
            f"{principle.value.capitalize()} presence is {level} "
            f"(score {score:.2f}). Keywords: {kw_str}."
        )


# ── Standalone ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    validator = SpinozaValidator()

    sample = (
        "This analysis provides a structured approach to improving code quality "
        "through systematic refactoring. Because maintainability is essential, "
        "we develop clear patterns that evolve with the codebase.\n\n"
        "The evidence suggests that consistent formatting and coherent architecture "
        "naturally create a sustainable foundation. Therefore, we build upon "
        "balanced abstractions that integrate holistic design principles.\n\n"
        "Key improvements:\n"
        "- Cultivate readable, elegant code through disciplined practice\n"
        "- Enable discovery of better patterns via continuous learning\n"
        "- Strengthen resilience with adaptive error handling\n\n"
        "This approach brings clarity and insight to the development process, "
        "empowering teams to thrive and achieve lasting progress."
    )

    report = validator.validate(sample)
    print(validator.format_report(report))
    print()
    print(report.summary)
