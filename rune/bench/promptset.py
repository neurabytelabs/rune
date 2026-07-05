"""Load and validate the versioned benchmark prompt set."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import List

from rune.bench.schemas import DOMAINS, LANGS, LENGTH_CLASSES, PromptRecord, read_jsonl

REQUIRED_FIELDS = ("prompt_id", "domain", "lang", "source", "length_class", "prompt")


class PromptSetError(ValueError):
    """Raised when the prompt set file fails validation."""


def load_promptset(path: Path | str) -> List[PromptRecord]:
    records = read_jsonl(path)
    if not records:
        raise PromptSetError(f"{path}: empty or missing prompt set")

    prompts: List[PromptRecord] = []
    seen: set[str] = set()
    for i, rec in enumerate(records, 1):
        missing = [f for f in REQUIRED_FIELDS if f not in rec]
        if missing:
            raise PromptSetError(f"{path}: line {i}: missing field(s) {', '.join(missing)}")
        pid = rec["prompt_id"]
        if pid in seen:
            raise PromptSetError(f"{path}: line {i}: duplicate prompt_id {pid}")
        seen.add(pid)
        if rec["domain"] not in DOMAINS:
            raise PromptSetError(f"{path}: line {i}: invalid domain '{rec['domain']}'")
        if rec["lang"] not in LANGS:
            raise PromptSetError(f"{path}: line {i}: invalid lang '{rec['lang']}'")
        if rec["length_class"] not in LENGTH_CLASSES:
            raise PromptSetError(f"{path}: line {i}: invalid length_class '{rec['length_class']}'")
        if not rec["prompt"].strip():
            raise PromptSetError(f"{path}: line {i}: empty prompt ({pid})")
        prompts.append(PromptRecord(**{f: rec[f] for f in REQUIRED_FIELDS}))
    return prompts


def promptset_sha256(path: Path | str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
