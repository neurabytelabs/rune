"""
⚖️ RUNE Evaluator — Cross-Model Testing & A/B Framework
Compare prompt performance across models and template variants.
"""

import json
import os
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import requests

from rune.core.validator import SpinozaValidator


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class LLMResponse:
    """Raw response from an LLM call."""
    content: str
    model: str
    tokens_in: int
    tokens_out: int
    time_seconds: float
    cost_estimate: float


@dataclass
class ModelResult:
    """Evaluation result for a single model."""
    model: str
    response: LLMResponse
    spinoza_score: float
    spinoza_grade: str
    rank: int


@dataclass
class CrossModelReport:
    """Comparative report across multiple models."""
    prompt: str
    enhanced_prompt: str | None
    results: list[ModelResult]
    winner: str
    timestamp: str
    summary: str


@dataclass
class DuelReport:
    """A/B test report: raw vs enhanced prompt."""
    prompt: str
    raw_result: LLMResponse
    enhanced_result: LLMResponse
    raw_spinoza: float
    enhanced_spinoza: float
    improvement_pct: float
    winner: str  # "raw" or "enhanced"
    timestamp: str


# ---------------------------------------------------------------------------
# Default models
# ---------------------------------------------------------------------------

DEFAULT_MODELS: list[str] = [
    "gemini-3-pro",
    "gemini-3-flash",
    "gpt-4o",
    "claude-sonnet-4-5",
    "claude-haiku-4",
]


# ---------------------------------------------------------------------------
# Evaluator
# ---------------------------------------------------------------------------

class Evaluator:
    """Cross-model evaluation and A/B testing engine.

    Uses the Antigravity proxy (OpenAI-compatible) to call various LLMs
    and :class:`SpinozaValidator` to score responses.

    Args:
        api_url: Base URL for the Antigravity proxy (e.g. ``http://127.0.0.1:8045``).
        api_key: API key for the proxy.
    """

    def __init__(self, api_url: str, api_key: str):
        self.api_url: str = api_url.rstrip("/")
        self.api_key: str = api_key
        self._validator = SpinozaValidator()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def cross_model_test(
        self,
        prompt: str,
        models: list[str] | None = None,
        enhanced: bool = True,
    ) -> CrossModelReport:
        """Run *prompt* across multiple models and compare results.

        Args:
            prompt: The user prompt to evaluate.
            models: List of model identifiers. Defaults to :data:`DEFAULT_MODELS`.
            enhanced: If ``True``, also store the enhanced version of the prompt.

        Returns:
            A :class:`CrossModelReport` with ranked results.
        """
        models = models or DEFAULT_MODELS
        timestamp = datetime.now(timezone.utc).isoformat()

        model_results: list[ModelResult] = []

        for model in models:
            try:
                resp = self._call_llm(prompt, model)
            except Exception as exc:  # noqa: BLE001
                resp = LLMResponse(
                    content=f"[ERROR] {exc}",
                    model=model,
                    tokens_in=0,
                    tokens_out=0,
                    time_seconds=0.0,
                    cost_estimate=0.0,
                )

            validation = self._validator.validate(resp.content)
            score = validation.get("score", 0.0)
            grade = validation.get("grade", "F")

            model_results.append(ModelResult(
                model=model,
                response=resp,
                spinoza_score=score,
                spinoza_grade=grade,
                rank=0,
            ))

        # Rank by Spinoza score descending, break ties by speed
        model_results.sort(
            key=lambda r: (-r.spinoza_score, r.response.time_seconds),
        )
        for i, mr in enumerate(model_results, 1):
            mr.rank = i

        winner = model_results[0].model if model_results else "none"

        summary_lines = [f"Winner: {winner}"]
        for mr in model_results:
            summary_lines.append(
                f"  #{mr.rank} {mr.model}: Spinoza {mr.spinoza_score:.2f} "
                f"({mr.spinoza_grade}) in {mr.response.time_seconds:.1f}s"
            )

        return CrossModelReport(
            prompt=prompt,
            enhanced_prompt=prompt if enhanced else None,
            results=model_results,
            winner=winner,
            timestamp=timestamp,
            summary="\n".join(summary_lines),
        )

    def duel(self, prompt: str, model: str = "gemini-3-pro") -> DuelReport:
        """A/B test a raw prompt against its enhanced version on the same model.

        Args:
            prompt: The original (raw) prompt.
            model: Model to use for both runs.

        Returns:
            A :class:`DuelReport` comparing raw and enhanced outcomes.
        """
        timestamp = datetime.now(timezone.utc).isoformat()

        # --- Round A: raw prompt ---
        raw_resp = self._call_llm(prompt, model)
        raw_val = self._validator.validate(raw_resp.content)
        raw_score: float = raw_val.get("score", 0.0)

        # --- Round B: enhanced prompt ---
        enhanced_prompt = self._enhance_prompt(prompt)
        enh_resp = self._call_llm(enhanced_prompt, model)
        enh_val = self._validator.validate(enh_resp.content)
        enh_score: float = enh_val.get("score", 0.0)

        # --- Compare ---
        if raw_score > 0:
            improvement = ((enh_score - raw_score) / raw_score) * 100
        else:
            improvement = 100.0 if enh_score > 0 else 0.0

        winner = "enhanced" if enh_score >= raw_score else "raw"

        return DuelReport(
            prompt=prompt,
            raw_result=raw_resp,
            enhanced_result=enh_resp,
            raw_spinoza=raw_score,
            enhanced_spinoza=enh_score,
            improvement_pct=round(improvement, 2),
            winner=winner,
            timestamp=timestamp,
        )

    # ------------------------------------------------------------------
    # Formatting
    # ------------------------------------------------------------------

    def format_cross_model(self, report: CrossModelReport) -> str:
        """Format a cross-model report for terminal display.

        Args:
            report: The report to format.

        Returns:
            Human-readable table string.
        """
        header = (
            f"⚖️  Cross-Model Report  ({report.timestamp})\n"
            f"Prompt: {report.prompt[:80]}{'…' if len(report.prompt) > 80 else ''}\n"
            f"{'─' * 78}\n"
            f"{'#':<3} {'Model':<22} {'Time':>6} {'Tok In':>7} {'Tok Out':>8} "
            f"{'Spinoza':>8} {'Grade':>6}\n"
            f"{'─' * 78}"
        )

        rows: list[str] = []
        for mr in report.results:
            marker = " 🏆" if mr.model == report.winner else ""
            rows.append(
                f"{mr.rank:<3} {mr.model:<22} "
                f"{mr.response.time_seconds:>5.1f}s "
                f"{mr.response.tokens_in:>7} "
                f"{mr.response.tokens_out:>8} "
                f"{mr.spinoza_score:>8.2f} "
                f"{mr.spinoza_grade:>6}{marker}"
            )

        footer = f"{'─' * 78}\n🏆 Winner: {report.winner}\n{report.summary}"
        return "\n".join([header, *rows, footer])

    def format_duel(self, report: DuelReport) -> str:
        """Format a duel report for terminal display.

        Args:
            report: The duel report to format.

        Returns:
            Human-readable comparison string.
        """
        raw = report.raw_result
        enh = report.enhanced_result
        lines = [
            f"⚔️  Duel Report  ({report.timestamp})",
            f"Prompt: {report.prompt[:80]}{'…' if len(report.prompt) > 80 else ''}",
            f"{'─' * 60}",
            f"{'':>20} {'RAW':>18} {'ENHANCED':>18}",
            f"{'─' * 60}",
            f"{'Time':>20} {raw.time_seconds:>17.1f}s {enh.time_seconds:>17.1f}s",
            f"{'Tokens In':>20} {raw.tokens_in:>18} {enh.tokens_in:>18}",
            f"{'Tokens Out':>20} {raw.tokens_out:>18} {enh.tokens_out:>18}",
            f"{'Spinoza Score':>20} {report.raw_spinoza:>18.2f} {report.enhanced_spinoza:>18.2f}",
            f"{'─' * 60}",
            f"Improvement: {report.improvement_pct:+.1f}%",
            f"🏆 Winner: {report.winner.upper()}",
        ]
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save_report(self, report: CrossModelReport | DuelReport, output_dir: str = "outputs") -> str:
        """Save a report as JSON and Markdown.

        Creates a date-stamped subfolder inside *output_dir*.

        Args:
            report: Report to persist.
            output_dir: Root output directory.

        Returns:
            Path to the created directory.
        """
        date_str = datetime.now().strftime("%Y-%m-%d")
        ts = datetime.now().strftime("%H%M%S")
        kind = "cross" if isinstance(report, CrossModelReport) else "duel"
        folder = Path(output_dir) / date_str
        folder.mkdir(parents=True, exist_ok=True)

        base = f"{kind}_{ts}"

        # JSON
        json_path = folder / f"{base}.json"
        json_path.write_text(
            json.dumps(self._report_to_dict(report), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        # Markdown
        md_path = folder / f"{base}.md"
        if isinstance(report, CrossModelReport):
            md_content = self.format_cross_model(report)
        else:
            md_content = self.format_duel(report)
        md_path.write_text(md_content, encoding="utf-8")

        return str(folder)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _call_llm(self, prompt: str, model: str, system: str | None = None) -> LLMResponse:
        """Call an LLM via the Antigravity OpenAI-compatible proxy.

        Args:
            prompt: User message.
            model: Model identifier.
            system: Optional system message.

        Returns:
            An :class:`LLMResponse` with timing and usage info.

        Raises:
            requests.HTTPError: On non-2xx responses.
        """
        messages: list[dict] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model,
            "messages": messages,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        start = time.monotonic()
        resp = requests.post(
            f"{self.api_url}/v1/chat/completions",
            json=payload,
            headers=headers,
            timeout=120,
        )
        elapsed = time.monotonic() - start
        resp.raise_for_status()

        data = resp.json()
        choice = data["choices"][0]
        usage = data.get("usage", {})

        tokens_in = usage.get("prompt_tokens", 0)
        tokens_out = usage.get("completion_tokens", 0)

        # Rough cost estimate (USD) — placeholder rates
        cost = tokens_in * 0.000003 + tokens_out * 0.000015

        return LLMResponse(
            content=choice["message"]["content"],
            model=model,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            time_seconds=round(elapsed, 2),
            cost_estimate=round(cost, 6),
        )

    def _enhance_prompt(self, prompt: str) -> str:
        """Create an enhanced version of a prompt for duel testing.

        Wraps the raw prompt with structured instructions to improve
        response quality.

        Args:
            prompt: Original raw prompt.

        Returns:
            Enhanced prompt string.
        """
        return (
            "You are an expert assistant. Answer the following question with:\n"
            "1. Clear structure and headings\n"
            "2. Concrete examples where helpful\n"
            "3. Accurate, well-reasoned content\n"
            "4. A brief summary at the end\n\n"
            f"Question: {prompt}"
        )

    @staticmethod
    def _report_to_dict(report: CrossModelReport | DuelReport) -> dict:
        """Convert a report dataclass tree to a JSON-serializable dict."""

        def _convert(obj):
            if hasattr(obj, "__dataclass_fields__"):
                return {k: _convert(v) for k, v in asdict(obj).items()}
            if isinstance(obj, list):
                return [_convert(item) for item in obj]
            return obj

        return _convert(report)
