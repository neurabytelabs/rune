"""Render the per-run report.md and the repo-level docs/BENCHMARKS.md."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from rune.bench.schemas import RUBRIC_CRITERIA

DEFAULT_ARM_NAMES = ("control", "treatment")


def _pct(x: float | None) -> str:
    return "n/a" if x is None else f"{x * 100:.1f}%"


def _arms(analysis: Dict[str, Any]) -> tuple[str, str]:
    """(baseline, variant) arm ids. Analyses written before arm specs omit the field."""
    arms = analysis.get("arms") or {}
    return (
        arms.get("baseline", DEFAULT_ARM_NAMES[0]),
        arms.get("variant", DEFAULT_ARM_NAMES[1]),
    )


def _headline_sentence(analysis: Dict[str, Any]) -> str:
    h = analysis["headline"]
    if h["preference_rate"] is None:
        return (
            "No decided pairs — every pair was judged a tie; no preference claim can be made (n/a)."
        )
    baseline, variant = _arms(analysis)
    # The default pair keeps its published wording so the RUNE result reads the same
    # as it always has; any other arm pair is described by its arm ids.
    if (baseline, variant) == DEFAULT_ARM_NAMES:
        subject = "RUNE-amplified prompts were preferred"
    else:
        subject = f"`{variant}` was preferred over `{baseline}`"
    lo, hi = h["ci95"]
    decided = h["wins"] + h["losses"]
    tie_share = h["ties"] / h["n_pairs"] if h["n_pairs"] else 0
    return (
        f"In blind pairwise comparison, {subject} in "
        f"**{_pct(h['preference_rate'])}** of decided pairs "
        f"(95% CI [{_pct(lo)}, {_pct(hi)}]; {decided} decided of {h['n_pairs']} pairs; "
        f"ties: {_pct(tie_share)}; exact binomial sign test p = {h['p_value']:.4g})."
    )


def _breakdown_table(title: str, rows: Dict[str, Dict[str, int]], arms: tuple[str, str]) -> str:
    baseline, variant = arms
    lines = [
        f"### {title}",
        "",
        f"| | {variant} wins | {baseline} wins | ties |",
        "|---|---|---|---|",
    ]
    for name in sorted(rows):
        r = rows[name]
        lines.append(
            f"| {name} | {r.get(f'{variant}_win', 0)} | {r.get(f'{baseline}_win', 0)} "
            f"| {r['tie']} |"
        )
    return "\n".join(lines)


def _deltas_table(deltas: Dict[str, float], arms: tuple[str, str]) -> str:
    baseline, variant = arms
    lines = [
        f"### Per-criterion score delta ({variant} − {baseline}, 1–5 scale)",
        "",
        "| criterion | mean delta |",
        "|---|---|",
    ]
    for crit in RUBRIC_CRITERIA:
        lines.append(f"| {crit} | {deltas.get(crit, 0.0):+.2f} |")
    return "\n".join(lines)


_LIMITATIONS_TMPL = """## Limitations

- **The protocol is label-blind, not style-blind.** {self_reveal} may self-reveal through
  structural artifacts. Judges are instructed not to reward structure per se; judge
  agreement and tie rates above are the honesty diagnostics.
- **Single sample per cell** at the configured temperature — the benchmark measures the
  output distribution users actually get, not a best-of-N.
- **Generation model family is Gemini only**; judging is cross-family but single-family
  (see JUDGE_PROTOCOL.md for the judge configuration of this run).
- The prompt set was partly authored by RUNE's developer; prompt IDs, sources, and the
  full set are committed for scrutiny."""


def _limitations(arms: tuple[str, str]) -> str:
    baseline, variant = arms
    self_reveal = (
        "RUNE-amplified responses"
        if (baseline, variant) == DEFAULT_ARM_NAMES
        else f"`{variant}` responses"
    )
    return _LIMITATIONS_TMPL.format(self_reveal=self_reveal)


def render_report(manifest: Dict[str, Any], analysis: Dict[str, Any]) -> str:
    h = analysis["headline"]
    agreement = analysis["judge_agreement"]
    arms = _arms(analysis)
    baseline, variant = arms
    parts = [
        f"# RUNE Benchmark Report — `{manifest['run_id']}`",
        "",
        f"- Created: {manifest['created_at']}  ",
        f"- Git SHA: `{manifest['git_sha']}`  ",
        f"- Harness: rune-wand {manifest['harness_version']}  ",
        f"- Prompt set: `{manifest['promptset']['path']}` "
        f"(n={manifest['promptset']['n']}, sha256 `{manifest['promptset']['sha256'][:12]}…`)  ",
        f"- Models: {', '.join(manifest['models'])}  ",
        f"- Seed: {manifest['seed']}",
        "",
        "## Headline",
        "",
        _headline_sentence(analysis),
        "",
        f"Raw counts: **{h['wins']} {variant} wins / {h['losses']} {baseline} wins / "
        f"{h['ties']} ties** over {h['n_pairs']} pairs.",
        "",
        f"Judge agreement: {agreement['unanimous']} unanimous, {agreement['split']} split.",
        "",
        _deltas_table(analysis["criterion_deltas"], arms),
        "",
        _breakdown_table("By domain", analysis["breakdowns"]["by_domain"], arms),
        "",
        _breakdown_table("By model", analysis["breakdowns"]["by_model"], arms),
        "",
        _limitations(arms),
        "",
        "## Reproduce",
        "",
        "```bash",
        f"wand bench generate --promptset {manifest['promptset']['path']} "
        f"--models {','.join(manifest['models'])} --seed {manifest['seed']}"
        + (f" --arms {manifest['arms_file']}" if manifest.get("arms_file") else ""),
        "wand bench export",
        "wand bench judge --api-url <openai-compat-endpoint> --model <judge-model>",
        "wand bench ingest",
        "wand bench report",
        "```",
    ]
    return "\n".join(parts)


def render_benchmarks_md(manifest: Dict[str, Any], analysis: Dict[str, Any]) -> str:
    """Regenerate docs/BENCHMARKS.md wholesale from real run data."""
    arms = _arms(analysis)
    baseline, variant = arms
    if (baseline, variant) == DEFAULT_ARM_NAMES:
        arms_sentence = [
            "through two arms — **control** (the raw prompt) and **treatment** (the prompt",
            "amplified by RUNE's 8-layer enhancement) — on the same model with identical",
        ]
    else:
        arms_sentence = [
            f"through two arms — **{baseline}** and **{variant}**, as defined in the run",
            "manifest — on the same model with identical",
        ]
    parts = [
        "# RUNE Benchmarks",
        "",
        "> Generated by `wand bench report --publish` from committed run artifacts in",
        f"> `benchmark/results/{manifest['run_id']}/`. Every number below is",
        "> reproducible from those artifacts — no hand-authored results.",
        "",
        "## Methodology",
        "",
        "Blind pairwise A/B: each prompt in the committed, versioned prompt set runs",
        *arms_sentence,
        "parameters. Responses are anonymized (per-judge randomized A/B order) and",
        "scored by independent judges on a 5-criterion rubric with a forced winner.",
        "Majority vote decides each pair; split decisions get an adversarial verifier.",
        "See `benchmark/JUDGE_PROTOCOL.md` for the full contract.",
        "",
        "## Result",
        "",
        _headline_sentence(analysis),
        "",
        _deltas_table(analysis["criterion_deltas"], arms),
        "",
        _breakdown_table("By domain", analysis["breakdowns"]["by_domain"], arms),
        "",
        _breakdown_table("By model", analysis["breakdowns"]["by_model"], arms),
        "",
        _limitations(arms),
        "",
        "## Run it yourself",
        "",
        "```bash",
        "export RUNE_API_KEY=<your key>",
        f"wand bench generate --promptset {manifest['promptset']['path']}"
        + (f" --arms {manifest['arms_file']}" if manifest.get("arms_file") else ""),
        "wand bench export",
        "wand bench judge --api-url <any-openai-compat-endpoint> --model <judge-model>",
        "wand bench ingest && wand bench report",
        "```",
        "",
        "The judge is pluggable: any judging system that honors",
        "`benchmark/JUDGE_PROTOCOL.md` (an LLM endpoint, a multi-agent workflow, or a",
        "human panel) produces verdicts this harness can analyze.",
    ]
    return "\n".join(parts)


def write_report(run_dir: Path | str, publish_to: Path | str | None = None) -> str:
    """Read manifest.json + analysis.json from run_dir, write report.md.

    If publish_to is given, also regenerate that file (docs/BENCHMARKS.md).
    """
    run_dir = Path(run_dir)
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    analysis = json.loads((run_dir / "analysis.json").read_text(encoding="utf-8"))
    report = render_report(manifest, analysis)
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    if publish_to is not None:
        Path(publish_to).write_text(render_benchmarks_md(manifest, analysis), encoding="utf-8")
    return report
