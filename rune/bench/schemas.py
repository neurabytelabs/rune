"""Data schemas, JSONL helpers, and judge rubric constants for the benchmark."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

DOMAINS = ("coding", "writing", "analysis", "creative", "research")
ARMS = ("control", "treatment")
LENGTH_CLASSES = ("short", "medium")
LANGS = ("en", "tr")
RUBRIC_CRITERIA = ("task_fulfillment", "accuracy", "depth", "clarity", "actionability")
WINNERS = ("A", "B", "tie")


@dataclass
class PromptRecord:
    prompt_id: str
    domain: str
    lang: str
    source: str
    length_class: str
    prompt: str


@dataclass
class GenerationRecord:
    gen_id: str
    prompt_id: str
    model: str
    arm: str
    enhanced_prompt: Optional[str]
    output: Optional[str]
    started_at: str
    duration_s: float
    chars_out: int
    error: Optional[str] = None


JUDGE_PROMPT = """You are a blind evaluation judge. Two AI responses (A and B) answer the same \
task prompt. You do NOT know how either response was produced — judge only what is written.

TASK PROMPT:
{task_prompt}

RESPONSE A:
{response_a}

RESPONSE B:
{response_b}

Evaluate in the language of the task prompt. Score each criterion 1-5 for both responses:
- task_fulfillment: does it do exactly what the prompt asked, including hard constraints \
(length, language, format)?
- accuracy: factual and technical correctness, sound reasoning.
- depth: substance and insight relative to what the task warrants — longer is NOT better.
- clarity: organization and readability in service of the task — do not reward structure \
or formatting for its own sake.
- actionability: can the requester act on it directly?

Then pick an overall winner: "A", "B", or "tie". Use "tie" ONLY if the responses are \
genuinely indistinguishable in quality.

Return ONLY valid JSON, no markdown fences:
{{"winner": "A|B|tie",
  "scores": {{"task_fulfillment": {{"a": 1, "b": 1}}, "accuracy": {{"a": 1, "b": 1}},
             "depth": {{"a": 1, "b": 1}}, "clarity": {{"a": 1, "b": 1}},
             "actionability": {{"a": 1, "b": 1}}}},
  "rationale": "one line", "flags": []}}"""


# ── JSONL helpers ────────────────────────────────────────────────────────────


def read_jsonl(path: Path | str) -> List[Dict[str, Any]]:
    """Read a JSONL file. Missing file → []. A corrupt FINAL line is dropped
    (interrupted append); corruption anywhere else raises ValueError."""
    path = Path(path)
    if not path.exists():
        return []
    lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    records: List[Dict[str, Any]] = []
    for i, line in enumerate(lines):
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as e:
            if i == len(lines) - 1:
                break  # tolerate a trailing partial line from an interrupted write
            raise ValueError(f"{path}: corrupt JSONL at line {i + 1}: {e}") from e
    return records


def write_jsonl(path: Path | str, records: Iterable[Dict[str, Any]]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def append_jsonl(path: Path | str, record: Dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
