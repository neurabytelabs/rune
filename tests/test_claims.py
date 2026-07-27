"""Guard against marketing-claim drift across distribution surfaces.

Context: the "~45% quality improvement, backed by arXiv:2512.14982" claim in README.md was
never supported by an artifact. The cited paper ("Prompt Repetition Improves Non-Reasoning
LLMs") is about a different technique — one that is not implemented in this codebase — and
reports no percentage at all. The claim reached 8 live surfaces across 3 repos by hand-copy,
because no single file owned it.

`tests/test_bench_report.py` already asserts the generated report carries no unsourced
claims. This extends the same standard to the hand-written surfaces, so the failure mode
that produced the drift — an assistant "sharpening the tagline" and inventing a number —
fails the suite instead of shipping.

Rule: the measured result lives in SKILL.md's CLAIM block and docs/BENCHMARKS.md.
Everywhere else links to it.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

# Surfaces that must not restate the claim. RUNE.md is exempt: it cites arXiv:2512.14982
# correctly, for the technique the paper actually covers, with an explicit scope note.
GUARDED_FILES = (
    "README.md",
    "SKILL.md",
    "docs/RUNE_V2_PLAN.md",
    "docs/ARCHITECTURE.md",
    "docs/QUICKSTART.md",
)

# Case-insensitive. Each entry is (pattern, why it is forbidden).
FORBIDDEN = (
    (r"arxiv", "citations belong in RUNE.md next to the technique they actually cover"),
    (r"~?\s*45\s*%", "the unbacked '45% quality improvement' number"),
    (r"dramatically better", "unquantified superiority claim"),
    (r"\b\d+(?:\.\d+)?\s*x\s+better\b", "unquantified multiplier claim"),
)

CLAIM_BLOCK = re.compile(
    r"<!--\s*CLAIM:BEGIN\s*-->.*?<!--\s*CLAIM:END\s*-->", re.DOTALL | re.IGNORECASE
)


def _text_outside_claim_block(path: Path) -> str:
    """File contents with the canonical CLAIM block removed.

    The CLAIM block is the one place the measured numbers are allowed to live, so it is
    excluded before scanning.
    """
    return CLAIM_BLOCK.sub("", path.read_text(encoding="utf-8"))


@pytest.mark.parametrize("relpath", GUARDED_FILES)
@pytest.mark.parametrize("pattern,reason", FORBIDDEN)
def test_no_unsourced_claims_on_distribution_surfaces(relpath, pattern, reason):
    path = REPO_ROOT / relpath
    if not path.exists():
        pytest.skip(f"{relpath} not present")

    body = _text_outside_claim_block(path)
    hits = [
        f"  line {i}: {line.strip()}"
        for i, line in enumerate(body.splitlines(), start=1)
        if re.search(pattern, line, re.IGNORECASE)
    ]
    assert not hits, (
        f"{relpath} restates a claim it must not own — {reason}.\n"
        + "\n".join(hits)
        + f"\n\nThe measured result lives in SKILL.md's CLAIM block and docs/BENCHMARKS.md. "
        f"Link to it instead of repeating it."
    )


def test_claim_block_exists_and_is_singular():
    """Exactly one canonical CLAIM block, and it lives in SKILL.md."""
    skill = REPO_ROOT / "SKILL.md"
    assert skill.exists(), "SKILL.md is the canonical skill definition — it must exist"

    blocks = CLAIM_BLOCK.findall(skill.read_text(encoding="utf-8"))
    assert len(blocks) == 1, f"expected exactly 1 CLAIM block in SKILL.md, found {len(blocks)}"

    block = blocks[0]
    # The claim is only useful if it carries the uncertainty with the number.
    assert "19.6" in block, "CLAIM block must state the measured preference rate"
    assert "CI" in block, (
        "CLAIM block must state the confidence interval, not just the point estimate"
    )
    assert "BENCHMARKS.md" in block, "CLAIM block must point at the full method and limitations"


def test_readme_points_at_the_benchmark():
    """The headline must send readers to the evidence rather than assert past it."""
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert "docs/BENCHMARKS.md" in readme, "README must link to the benchmark result"
