"""
⚔️ SWARM Tournament — Spinoza-based Agent Ranking

Scores each agent's output and selects the top K for synthesis.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AgentResult:
    """Result from a single agent's execution."""
    agent_type: str
    agent_name: str
    agent_emoji: str
    system_prompt: str
    response: str
    model: str
    spinoza_scores: dict = field(default_factory=dict)
    overall_score: float = 0.0
    rank: int = 0
    time_seconds: float = 0.0
    tokens_in: int = 0
    tokens_out: int = 0


@dataclass
class TournamentResult:
    """Result of the full tournament."""
    prompt: str
    results: list[AgentResult]
    winner: AgentResult
    top_k: list[AgentResult]
    fused_output: Optional[str] = None
    fused_score: float = 0.0


class SpinozaTournament:
    """Score and rank agent outputs using Spinoza's 4 pillars."""

    # Keyword-based heuristic scoring (no LLM needed)
    # Each pillar scores 0-25, total 0-100

    def score(self, text: str) -> dict:
        """Score text on 4 Spinoza pillars. Returns dict with scores + overall."""
        conatus = self._score_conatus(text)
        ratio = self._score_ratio(text)
        laetitia = self._score_laetitia(text)
        natura = self._score_natura(text)

        overall = conatus + ratio + laetitia + natura

        return {
            "conatus": round(conatus, 1),
            "ratio": round(ratio, 1),
            "laetitia": round(laetitia, 1),
            "natura": round(natura, 1),
            "overall": round(overall, 1),
        }

    def rank(self, results: list[AgentResult], top_k: int = 2) -> TournamentResult:
        """Score all results, rank them, return tournament outcome."""
        for r in results:
            scores = self.score(r.response)
            r.spinoza_scores = scores
            r.overall_score = scores["overall"]

        # Sort by overall score descending
        results.sort(key=lambda r: -r.overall_score)
        for i, r in enumerate(results, 1):
            r.rank = i

        winner = results[0]
        top = results[:top_k]

        return TournamentResult(
            prompt="",  # Will be set by orchestrator
            results=results,
            winner=winner,
            top_k=top,
        )

    # ── Scoring Heuristics ──────────────────────────────────────────

    def _score_conatus(self, text: str) -> float:
        """Agency & actionability (0-25)."""
        score = 10.0  # Base

        # Action indicators
        action_words = ["implement", "create", "build", "use", "apply", "run",
                       "execute", "start", "deploy", "configure", "install",
                       "write", "design", "yap", "oluştur", "kur", "çalıştır"]
        hits = sum(1 for w in action_words if w.lower() in text.lower())
        score += min(hits * 1.5, 8)

        # Numbered steps or lists
        steps = len(re.findall(r'^\s*\d+[\.\)]\s', text, re.MULTILINE))
        score += min(steps * 0.8, 5)

        # Code blocks (highly actionable)
        code_blocks = len(re.findall(r'```', text))
        score += min(code_blocks * 1.0, 4)

        return min(score, 25)

    def _score_ratio(self, text: str) -> float:
        """Logic & consistency (0-25)."""
        score = 12.0  # Base

        # Structure indicators (headers, sections)
        headers = len(re.findall(r'^#+\s', text, re.MULTILINE))
        score += min(headers * 1.2, 5)

        # Logical connectors
        connectors = ["because", "therefore", "however", "although", "since",
                      "çünkü", "dolayısıyla", "ancak", "bu nedenle", "consequently"]
        hits = sum(1 for c in connectors if c.lower() in text.lower())
        score += min(hits * 1.0, 4)

        # Length penalty (too short = incomplete reasoning)
        words = len(text.split())
        if words < 50:
            score -= 5
        elif words > 100:
            score += 2
        if words > 500:
            score += 2

        return min(max(score, 0), 25)

    def _score_laetitia(self, text: str) -> float:
        """Tone & constructiveness (0-25)."""
        score = 15.0  # Base (assume constructive)

        # Positive indicators
        positive = ["excellent", "powerful", "effective", "recommend", "best",
                    "mükemmel", "güçlü", "etkili", "öneriyorum", "harika"]
        hits = sum(1 for p in positive if p.lower() in text.lower())
        score += min(hits * 0.8, 4)

        # Negative markers (hedging, apologizing)
        hedges = ["i'm sorry", "i cannot", "as an ai", "i don't have",
                  "unfortunately", "maalesef", "yapamam"]
        hits = sum(1 for h in hedges if h.lower() in text.lower())
        score -= hits * 2

        # Emoji/formatting care
        if any(c in text for c in "🎯💡🔥✅⚡🚀"):
            score += 1.5

        return min(max(score, 0), 25)

    def _score_natura(self, text: str) -> float:
        """Naturalness & flow (0-25)."""
        score = 14.0  # Base

        # Sentence variety (std dev of sentence lengths)
        sentences = re.split(r'[.!?]\s+', text)
        if len(sentences) > 2:
            lengths = [len(s.split()) for s in sentences if s.strip()]
            if lengths:
                avg = sum(lengths) / len(lengths)
                variance = sum((l - avg) ** 2 for l in lengths) / len(lengths)
                # Some variety is good
                if 5 < variance < 200:
                    score += 4
                elif variance >= 200:
                    score += 2

        # Anti-robot patterns
        robot_phrases = ["as an ai language model", "i'd be happy to",
                        "certainly!", "absolutely!", "great question"]
        hits = sum(1 for r in robot_phrases if r.lower() in text.lower())
        score -= hits * 3

        # Paragraph structure
        paragraphs = text.count('\n\n')
        if 2 <= paragraphs <= 10:
            score += 3

        return min(max(score, 0), 25)
