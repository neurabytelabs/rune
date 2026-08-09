"""Data schemas, JSONL helpers, and judge rubric constants for the benchmark."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

DOMAINS = ("coding", "writing", "analysis", "creative", "research")
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


# ── arm specs ────────────────────────────────────────────────────────────────
#
# An arm is one side of the blind A/B. The harness does not care what produces a
# response — only that two arms answer the same prompt under the same conditions.
# That makes `wand bench` usable for anything pairwise: raw vs amplified, SOUL v1
# vs SOUL v2, policy A vs policy B, one CLI agent vs another.

ARM_KINDS = ("raw", "rune_enhance", "prefix", "command")
N_ARMS = 2

# gen_id is "prompt_id|model|arm_id" — an arm_id carrying "|" would corrupt it.
ARM_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")

ARM_COUNT_ERROR = """Exactly 2 arms are required, got {n}.

This is not an arbitrary cap. The statistics layer is pairwise by construction:
pairing.py builds one pair per (prompt_id, model), the judge protocol forces a
binary winner, and stats.py runs an exact binomial sign test over decided pairs.
Three or more arms need a different pairing scheme AND a multiple-comparison
correction, neither of which this harness implements — adding a third arm without
them inflates the false-positive rate.

To compare N arms: run N-1 separate two-arm benchmarks against a shared control
and apply the correction across runs yourself."""


class ArmSpecError(ValueError):
    """Raised when an arm definition or arm list violates the two-arm contract."""


@dataclass
class ArmSpec:
    """How one arm turns a task prompt into a response.

    kind:
        raw           send the prompt unchanged (the historical "control")
        rune_enhance  helpers.enhance_prompt first (the historical "treatment");
                      config {"rune": "<template name>"} selects a grimoire template
        prefix        config {"system": "<text or file path>"} goes in front of the
                      prompt — the SOUL / system-message / policy comparison path
        command       config {"cmd": "..."} runs an external command, stdin=prompt,
                      stdout=response; the escape hatch for anything else
    """

    arm_id: str
    kind: str
    config: Dict[str, Any] = field(default_factory=dict)


# The arms `wand bench` uses when no --arms file is given. Order is load-bearing:
# arms[0] is the baseline, arms[1] is the arm whose preference rate is the headline.
DEFAULT_ARMS: Tuple[ArmSpec, ...] = (
    ArmSpec(arm_id="control", kind="raw"),
    ArmSpec(arm_id="treatment", kind="rune_enhance"),
)

# Config keys that must be present and non-empty, per kind.
_REQUIRED_CONFIG = {"prefix": "system", "command": "cmd"}


def arm_ids(arms: Sequence[ArmSpec]) -> List[str]:
    return [a.arm_id for a in arms]


def arm_from_dict(data: Dict[str, Any]) -> ArmSpec:
    if not isinstance(data, dict):
        raise ArmSpecError(f"each arm must be an object, got {type(data).__name__}")
    unknown = set(data) - {"arm_id", "kind", "config"}
    if unknown:
        raise ArmSpecError(f"unknown arm field(s): {', '.join(sorted(unknown))}")
    for required in ("arm_id", "kind"):
        if required not in data:
            raise ArmSpecError(f"arm is missing required field '{required}'")
    config = data.get("config") or {}
    if not isinstance(config, dict):
        raise ArmSpecError(f"{data['arm_id']}: config must be an object")
    return ArmSpec(arm_id=data["arm_id"], kind=data["kind"], config=dict(config))


def validate_arms(arms: Sequence[ArmSpec]) -> None:
    """Enforce the two-arm contract and per-kind config requirements."""
    if len(arms) != N_ARMS:
        raise ArmSpecError(ARM_COUNT_ERROR.format(n=len(arms)))

    ids = arm_ids(arms)
    if len(set(ids)) != len(ids):
        raise ArmSpecError(f"arm_id values must be unique, got {ids}")

    for arm in arms:
        if not isinstance(arm.arm_id, str) or not ARM_ID_RE.match(arm.arm_id):
            raise ArmSpecError(
                f"invalid arm_id {arm.arm_id!r} — use letters, digits, '.', '_' or '-' "
                "(arm_id is embedded in gen_id as prompt_id|model|arm_id)"
            )
        if arm.kind not in ARM_KINDS:
            raise ArmSpecError(
                f"{arm.arm_id}: unknown kind {arm.kind!r} — expected one of {', '.join(ARM_KINDS)}"
            )
        key = _REQUIRED_CONFIG.get(arm.kind)
        if key and not str(arm.config.get(key, "")).strip():
            raise ArmSpecError(f"{arm.arm_id}: kind '{arm.kind}' requires config.{key}")


def load_arms(path: Path | str) -> List[ArmSpec]:
    """Read an arm file (benchmark/arms/<name>.json) into a validated arm list.

    Accepts either a bare list of arms or an object with an "arms" key (which may
    also carry "name"/"description" for humans).
    """
    path = Path(path)
    if not path.exists():
        raise ArmSpecError(f"{path}: arm file not found")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ArmSpecError(f"{path}: invalid JSON: {e}") from e

    entries = data if isinstance(data, list) else data.get("arms")
    if not isinstance(entries, list):
        raise ArmSpecError(f"{path}: expected a list of arms or an object with an 'arms' list")

    try:
        arms = [arm_from_dict(e) for e in entries]
        validate_arms(arms)
    except ArmSpecError as e:
        raise ArmSpecError(f"{path}: {e}") from e
    return arms


def arms_from_manifest(entries: Sequence[Any]) -> List[ArmSpec]:
    """Rebuild arm specs from a manifest's "arms" field.

    Pre-ArmSpec manifests stored a plain list of arm_id strings; those resolve
    against DEFAULT_ARMS so runs recorded before this feature still replay.
    """
    by_id = {a.arm_id: a for a in DEFAULT_ARMS}
    arms: List[ArmSpec] = []
    for entry in entries:
        if isinstance(entry, str):
            arms.append(by_id.get(entry) or ArmSpec(arm_id=entry, kind="raw"))
        else:
            arms.append(
                arm_from_dict({k: entry[k] for k in ("arm_id", "kind", "config") if k in entry})
            )
    return arms


def config_file(value: Any, base_dir: Path | str | None = None) -> Optional[Path]:
    """Resolve a config value to a file, or None if it is literal text.

    A `prefix` arm's "system" may be either the policy text itself or a path to it.
    A value is treated as a path only when it actually names a readable file, and
    multi-line or very long values are never probed — a SOUL.md pasted inline must
    not be stat()'d. Relative paths resolve against the current directory first,
    then base_dir (the repo root), so arm files can use repo-relative paths.
    """
    if not isinstance(value, str) or "\n" in value or len(value) > 255 or not value.strip():
        return None
    candidates = [Path(value)]
    if base_dir is not None:
        candidates.append(Path(base_dir) / value)
    for candidate in candidates:
        try:
            if candidate.is_file():
                return candidate
        except OSError:
            continue
    return None


# Values shaped like a path to a text file: no whitespace, known extension. Used only
# to tell a typo'd path apart from genuine inline text.
_PATH_SHAPED = re.compile(r"^\S+\.(md|markdown|txt|json|ya?ml|prompt)$", re.IGNORECASE)


def resolve_config_text(
    value: Any, base_dir: Path | str | None = None, what: str = "config value"
) -> str:
    """Return literal text for a config value, reading it from disk if it names a file.

    A path that does not exist is an error rather than a fallback: silently using
    "benchmark/arms/policies/soul_v2.md" as the system prompt would still produce a
    complete run and a plausible p-value, measuring nothing.
    """
    path = config_file(value, base_dir)
    if path is not None:
        return path.read_text(encoding="utf-8")
    text = str(value)
    if _PATH_SHAPED.match(text.strip()):
        raise ArmSpecError(
            f"{what}: {text!r} looks like a file path but no such file exists "
            f"(searched the current directory and {base_dir}). Fix the path, or "
            "inline the text if that string really is the intended content."
        )
    return text


def arm_to_manifest(arm: ArmSpec, base_dir: Path | str | None = None) -> Dict[str, Any]:
    """Serialize an arm for manifest.json, pinning any file-backed config.

    Config is recorded as written so the manifest stays portable, but a value that
    resolves to a file also gets that file's sha256. Without it a run referencing
    an external policy file could not be reproduced — the manifest would name a
    path whose contents may since have changed.
    """
    entry: Dict[str, Any] = {"arm_id": arm.arm_id, "kind": arm.kind, "config": dict(arm.config)}
    digests: Dict[str, Any] = {}
    for key, value in arm.config.items():
        path = config_file(value, base_dir)
        if path is not None:
            digests[key] = {
                "path": str(value),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
    if digests:
        entry["config_files"] = digests
    return entry


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
