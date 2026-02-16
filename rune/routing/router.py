"""
🔀 RUNE Router — Intelligent Multi-Model Routing
Routes prompts to the optimal LLM based on task classification.

Supports four routing strategies:
  • optimal  — best quality model for the task
  • fast     — lowest latency
  • cheap    — lowest cost
  • specific — user-chosen model
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# Task taxonomy
# ---------------------------------------------------------------------------

class TaskType(Enum):
    """Canonical task categories recognised by the router."""

    CODE_GENERATION = "code_generation"
    CODE_REVIEW = "code_review"
    DEBUGGING = "debugging"
    CREATIVE_WRITING = "creative_writing"
    ANALYSIS = "analysis"
    DOCUMENTATION = "documentation"
    CONVERSATION = "conversation"
    MATH_LOGIC = "math_logic"
    TRANSLATION = "translation"
    GENERAL = "general"


# ---------------------------------------------------------------------------
# Model registry
# ---------------------------------------------------------------------------

@dataclass
class ModelInfo:
    """Metadata for a single LLM endpoint."""

    id: str
    name: str
    provider: str                       # gemini, claude, gpt, ollama
    strengths: list[TaskType]
    cost_per_1k_input: float            # USD per 1 000 input tokens
    cost_per_1k_output: float           # USD per 1 000 output tokens
    max_tokens: int
    speed: str                          # fast, medium, slow

    def __str__(self) -> str:
        return f"{self.name} ({self.provider})"


MODEL_REGISTRY: list[ModelInfo] = [
    ModelInfo(
        id="claude-opus-4",
        name="Claude Opus 4",
        provider="claude",
        strengths=[TaskType.CODE_GENERATION, TaskType.CODE_REVIEW, TaskType.ANALYSIS,
                   TaskType.DEBUGGING, TaskType.DOCUMENTATION],
        cost_per_1k_input=0.015,
        cost_per_1k_output=0.075,
        max_tokens=200_000,
        speed="medium",
    ),
    ModelInfo(
        id="claude-sonnet-4",
        name="Claude Sonnet 4",
        provider="claude",
        strengths=[TaskType.CODE_GENERATION, TaskType.CODE_REVIEW, TaskType.DEBUGGING,
                   TaskType.CONVERSATION, TaskType.DOCUMENTATION],
        cost_per_1k_input=0.003,
        cost_per_1k_output=0.015,
        max_tokens=200_000,
        speed="fast",
    ),
    ModelInfo(
        id="gpt-4o",
        name="GPT-4o",
        provider="gpt",
        strengths=[TaskType.CONVERSATION, TaskType.ANALYSIS, TaskType.CREATIVE_WRITING,
                   TaskType.CODE_GENERATION],
        cost_per_1k_input=0.005,
        cost_per_1k_output=0.015,
        max_tokens=128_000,
        speed="fast",
    ),
    ModelInfo(
        id="gpt-o3",
        name="GPT o3",
        provider="gpt",
        strengths=[TaskType.MATH_LOGIC, TaskType.CODE_GENERATION, TaskType.ANALYSIS,
                   TaskType.DEBUGGING],
        cost_per_1k_input=0.010,
        cost_per_1k_output=0.040,
        max_tokens=200_000,
        speed="slow",
    ),
    ModelInfo(
        id="gemini-2.5-pro",
        name="Gemini 2.5 Pro",
        provider="gemini",
        strengths=[TaskType.CODE_GENERATION, TaskType.ANALYSIS, TaskType.MATH_LOGIC,
                   TaskType.DOCUMENTATION],
        cost_per_1k_input=0.00125,
        cost_per_1k_output=0.01,
        max_tokens=1_000_000,
        speed="medium",
    ),
    ModelInfo(
        id="gemini-2.5-flash",
        name="Gemini 2.5 Flash",
        provider="gemini",
        strengths=[TaskType.CONVERSATION, TaskType.TRANSLATION, TaskType.GENERAL,
                   TaskType.DOCUMENTATION],
        cost_per_1k_input=0.00015,
        cost_per_1k_output=0.0006,
        max_tokens=1_000_000,
        speed="fast",
    ),
    ModelInfo(
        id="gemini-2.0-flash",
        name="Gemini 2.0 Flash",
        provider="gemini",
        strengths=[TaskType.CONVERSATION, TaskType.GENERAL, TaskType.TRANSLATION],
        cost_per_1k_input=0.0001,
        cost_per_1k_output=0.0004,
        max_tokens=1_000_000,
        speed="fast",
    ),
    ModelInfo(
        id="grok-4-1-fast-reasoning",
        name="Grok 4.1 Fast Reasoning",
        provider="xai",
        strengths=[TaskType.ANALYSIS, TaskType.MATH_LOGIC, TaskType.CODE_GENERATION,
                   TaskType.DEBUGGING, TaskType.CREATIVE_WRITING],
        cost_per_1k_input=0.0002,
        cost_per_1k_output=0.0005,
        max_tokens=2_000_000,
        speed="fast",
    ),
    ModelInfo(
        id="grok-4-fast",
        name="Grok 4 Fast",
        provider="xai",
        strengths=[TaskType.CONVERSATION, TaskType.ANALYSIS, TaskType.GENERAL,
                   TaskType.CREATIVE_WRITING],
        cost_per_1k_input=0.0002,
        cost_per_1k_output=0.0005,
        max_tokens=2_000_000,
        speed="fast",
    ),
    ModelInfo(
        id="grok-code-fast-1",
        name="Grok Code Fast",
        provider="xai",
        strengths=[TaskType.CODE_GENERATION, TaskType.CODE_REVIEW, TaskType.DEBUGGING],
        cost_per_1k_input=0.0002,
        cost_per_1k_output=0.0015,
        max_tokens=256_000,
        speed="fast",
    ),
    ModelInfo(
        id="deepseek-r1",
        name="DeepSeek R1",
        provider="ollama",
        strengths=[TaskType.MATH_LOGIC, TaskType.CODE_GENERATION, TaskType.DEBUGGING,
                   TaskType.ANALYSIS],
        cost_per_1k_input=0.00055,
        cost_per_1k_output=0.0022,
        max_tokens=128_000,
        speed="medium",
    ),
    ModelInfo(
        id="llama-3.3-70b",
        name="Llama 3.3 70B",
        provider="ollama",
        strengths=[TaskType.CONVERSATION, TaskType.GENERAL, TaskType.CREATIVE_WRITING,
                   TaskType.TRANSLATION],
        cost_per_1k_input=0.0,
        cost_per_1k_output=0.0,
        max_tokens=128_000,
        speed="medium",
    ),
    ModelInfo(
        id="claude-haiku-3.5",
        name="Claude Haiku 3.5",
        provider="claude",
        strengths=[TaskType.CONVERSATION, TaskType.GENERAL, TaskType.TRANSLATION,
                   TaskType.DOCUMENTATION],
        cost_per_1k_input=0.0008,
        cost_per_1k_output=0.004,
        max_tokens=200_000,
        speed="fast",
    ),
]

_REGISTRY_BY_ID: dict[str, ModelInfo] = {m.id: m for m in MODEL_REGISTRY}


# ---------------------------------------------------------------------------
# Keyword patterns for classification
# ---------------------------------------------------------------------------

_TASK_PATTERNS: dict[TaskType, list[str]] = {
    TaskType.CODE_GENERATION: [
        r"\b(write|create|build|implement|generate|code)\b.*\b(function|class|api|app|script|module|program)\b",
        r"\b(python|javascript|typescript|rust|go|java|c\+\+|html|css|sql)\b",
        r"\bdef\b|\bclass\b|\bimport\b|\bfrom\b",
    ],
    TaskType.CODE_REVIEW: [
        r"\b(review|critique|check|audit)\b.*\b(code|implementation|pr|pull request)\b",
        r"\bcode\s*review\b",
    ],
    TaskType.DEBUGGING: [
        r"\b(debug|fix|error|bug|issue|traceback|exception|crash|broken|not working)\b",
        r"\bstack\s*trace\b",
    ],
    TaskType.CREATIVE_WRITING: [
        r"\b(write|create|compose)\b.*\b(story|poem|essay|blog|article|novel|song|script)\b",
        r"\b(creative|fiction|narrative|poetic)\b",
    ],
    TaskType.ANALYSIS: [
        r"\b(analy[sz]e|evaluate|compare|assess|examine|investigate|research)\b",
        r"\b(pros?\s*(and|&)\s*cons?|trade-?offs?|benchmark)\b",
    ],
    TaskType.DOCUMENTATION: [
        r"\b(document|readme|docstring|jsdoc|explain\s+this)\b",
        r"\bwrite\b.*\b(docs?|documentation|guide|tutorial)\b",
    ],
    TaskType.MATH_LOGIC: [
        r"\b(math|calcul|equation|proof|theorem|algorithm|probability|statistic)\b",
        r"\b(solve|compute|derive|integral|matrix|linear algebra)\b",
        r"[∑∫∏√πΔ]",
    ],
    TaskType.TRANSLATION: [
        r"\b(translat|çevir|übersetze|tradui)\b",
        r"\b(from\s+\w+\s+to\s+\w+)\b.*\b(language|english|turkish|german|french|spanish)\b",
    ],
    TaskType.CONVERSATION: [
        r"\b(chat|talk|tell me|hey|hi|hello|what do you think)\b",
        r"\b(opinion|advice|recommend|suggest)\b",
    ],
}


# ---------------------------------------------------------------------------
# Task classifier
# ---------------------------------------------------------------------------

class TaskClassifier:
    """Classify prompts into ``TaskType`` via regex-based keyword analysis.

    Uses a scoring system: each matching pattern adds a point.  The task type
    with the highest score wins.  Falls back to ``GENERAL`` when no pattern
    matches.
    """

    def __init__(self) -> None:
        self._last_scores: dict[TaskType, int] = {}
        self._last_winner: TaskType = TaskType.GENERAL

    def classify(self, prompt: str) -> TaskType:
        """Classify *prompt* into a ``TaskType``.

        Args:
            prompt: Raw user prompt text.

        Returns:
            The best-matching ``TaskType``.
        """
        lower = prompt.lower()
        scores: dict[TaskType, int] = {t: 0 for t in TaskType}

        for task_type, patterns in _TASK_PATTERNS.items():
            for pat in patterns:
                if re.search(pat, lower):
                    scores[task_type] += 1

        self._last_scores = scores
        best = max(scores, key=scores.get)  # type: ignore[arg-type]
        self._last_winner = best if scores[best] > 0 else TaskType.GENERAL
        return self._last_winner

    def confidence(self) -> float:
        """Return confidence of the last classification (0.0–1.0).

        Confidence is the ratio of the winning score to the total score sum,
        or 0.0 if nothing matched.
        """
        total = sum(self._last_scores.values())
        if total == 0:
            return 0.0
        return self._last_scores.get(self._last_winner, 0) / total


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

_SPEED_RANK = {"fast": 1, "medium": 2, "slow": 3}


class Router:
    """Intelligent multi-model routing engine.

    Strategies:
        - **optimal** — highest quality model whose strengths match the task.
        - **fast** — lowest latency among matching models.
        - **cheap** — lowest cost among matching models.
        - **specific** — user chooses a model id via *model_id* parameter.

    Usage::

        router = Router()
        model = router.route("Write a Python function to parse JSON")
        print(model)  # -> Claude Opus 4 (claude)
    """

    def __init__(self, strategy: str = "optimal",
                 registry: Optional[list[ModelInfo]] = None) -> None:
        self.strategy = strategy
        self.registry = registry or MODEL_REGISTRY
        self._classifier = TaskClassifier()

    def route(self, prompt: str, strategy: Optional[str] = None,
              model_id: Optional[str] = None) -> ModelInfo:
        """Select the best model for *prompt*.

        Args:
            prompt: Raw user prompt.
            strategy: Override the default strategy for this call.
            model_id: If strategy is ``"specific"``, the model id to use.

        Returns:
            A ``ModelInfo`` for the selected model.

        Raises:
            ValueError: If *model_id* is not found in the registry.
        """
        strat = strategy or self.strategy

        if strat == "specific":
            if model_id and model_id in _REGISTRY_BY_ID:
                return _REGISTRY_BY_ID[model_id]
            raise ValueError(f"Unknown model_id: {model_id}")

        task = self._classifier.classify(prompt)
        candidates = [m for m in self.registry if task in m.strengths]
        if not candidates:
            candidates = list(self.registry)

        if strat == "fast":
            candidates.sort(key=lambda m: _SPEED_RANK.get(m.speed, 99))
        elif strat == "cheap":
            candidates.sort(key=lambda m: m.cost_per_1k_input + m.cost_per_1k_output)
        else:  # optimal — prefer slower/pricier models (assumed higher quality)
            candidates.sort(
                key=lambda m: (-m.cost_per_1k_output, _SPEED_RANK.get(m.speed, 99))
            )

        return candidates[0]

    def get_alternatives(self, prompt: str, n: int = 3) -> list[tuple[ModelInfo, str]]:
        """Return top *n* alternative models with a short rationale.

        Args:
            prompt: Raw user prompt.
            n: Number of alternatives to return.

        Returns:
            List of ``(ModelInfo, reason_string)`` tuples.
        """
        task = self._classifier.classify(prompt)
        conf = self._classifier.confidence()

        scored: list[tuple[ModelInfo, float]] = []
        for m in self.registry:
            score = 0.0
            if task in m.strengths:
                score += 10.0
            score -= m.cost_per_1k_input * 100  # slight cost penalty
            score -= _SPEED_RANK.get(m.speed, 3)
            scored.append((m, score))

        scored.sort(key=lambda x: -x[1])

        results: list[tuple[ModelInfo, str]] = []
        for model, score in scored[:n]:
            match = "✓ strength match" if task in model.strengths else "general-purpose"
            reason = (f"{match} for {task.value} | "
                      f"speed={model.speed} | "
                      f"cost=${model.cost_per_1k_input:.4f}/1k in")
            results.append((model, reason))

        return results

    def estimate_cost(self, prompt: str, model: ModelInfo) -> float:
        """Estimate the cost (USD) of processing *prompt* with *model*.

        Assumes output ≈ 2× input tokens for generation tasks.

        Args:
            prompt: Raw user prompt.
            model: The target model.

        Returns:
            Estimated cost in USD.
        """
        input_tokens = len(prompt) / 4  # rough char-to-token ratio
        output_tokens = input_tokens * 2  # heuristic
        cost = ((input_tokens / 1000) * model.cost_per_1k_input +
                (output_tokens / 1000) * model.cost_per_1k_output)
        return round(cost, 6)


# ---------------------------------------------------------------------------
# Quick CLI test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    router = Router()
    classifier = TaskClassifier()

    prompts = [
        "Write a Python function to parse nested JSON",
        "Debug this traceback: KeyError on line 42",
        "Write a short poem about autumn rain",
        "Analyse the trade-offs between REST and GraphQL",
        "Translate this paragraph from English to Turkish",
        "What is the integral of x²·sin(x)?",
        "Hey, how are you today?",
    ]

    for p in prompts:
        task = classifier.classify(p)
        conf = classifier.confidence()
        model = router.route(p)
        cost = router.estimate_cost(p, model)
        print(f"[{task.value:<20}] conf={conf:.0%}  → {model.name:<22} "
              f"${cost:.6f}  | {p[:50]}")
