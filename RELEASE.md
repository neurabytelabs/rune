# Release checklist — distribution surfaces

`SKILL.md` in this repo is canonical. Every other surface is derived from it. There is no
generator script: with two derived fields, a checklist is cheaper than a build step. If a
third distribution target ever needs real templating, write the script then — not before.

## The one rule

**The measured result lives in exactly two places:** the `<!-- CLAIM:BEGIN -->` block in
`SKILL.md`, and `docs/BENCHMARKS.md`. Every other surface links to them. Never restate a
percentage, a confidence interval, or a research citation anywhere else.

`tests/test_claims.py` enforces this on the canonical surfaces. It cannot see registry
metadata (clawhub descriptions are stored server-side, not in this repo) — that is what this
checklist covers.

## When `SKILL.md` changes

1. **Run the guard.**
   ```bash
   python3 -m pytest tests/test_claims.py -q
   ```

2. **Mirror to `neurabytelabs/rune-skill`.** Copy verbatim; never edit the mirror in place.
   ```bash
   cp SKILL.md ~/Documents/GitHub/rune-skill/SKILL.md
   ```
   Then sync `package.json` → `description` from the canonical frontmatter `description`.

3. **Sync locally installed copies — but diff first.** Most are runtime caches. At least one
   is not, and copying over it destroys work:
   ```bash
   for f in ~/.claude/skills/rune-prompt-amplification/SKILL.md \
            ~/.hermes/skills/prompt-engineering/rune-prompt-amplification/SKILL.md; do
     [ -f "$f" ] && { diff -q SKILL.md "$f" >/dev/null && echo "cache  → safe to cp: $f" \
                                                       || echo "DIVERGED → inspect:    $f"; }
   done
   ```
   Copy only over the ones reported as `cache`. Anything `DIVERGED` is a fork with its own
   frontmatter or body and needs a deliberate merge — never a blind `cp`.

   Known as of 2026-07-27: the Claude Code copy is byte-identical (safe). The Hermes copy is
   a **fork** — version 2.0.0, a Hermes-targeted `description`, `homepage` pointing at the
   mirror, an extra `metadata.hermes` block, and a different body (348 diff lines). It has
   never been synced from canonical and must not be overwritten without a decision.

   `tests/test_claims.py` cannot see these files — they live outside the repo. This diff step
   is the only thing standing between the checklist and data loss.

4. **Publish to clawhub** (or any registry). Two fields are hand-copied because registries
   store description text server-side and do not render links:
   - skill `description` ← canonical frontmatter `description`
   - `package.json` `description` ← same, adjusted for length if the registry caps it

   Bump the version. Verify the published description contains **no** percentage, no
   research citation, and no unquantified superiority claim ("dramatically better", "Nx
   better").

5. **Check `mustafasarac-core`.** The repo table and the
   `agents/skills/prompt-engineering/rune-framework/references/` copy must point at the
   canonical file rather than restate it.

## Before running `wand bench report`

**`docs/BENCHMARKS.md` and each run's `report.md` are generated-plus-manual, not generated.**
Both commands regenerate their target wholesale, with no warning and no diff prompt, and the
renderer cannot reproduce the hand-authored sections that were committed on top:

- `docs/BENCHMARKS.md` — the "Is this a harness artifact?" section and the two-judge-panel
  limitation bullet (16 lines as of 2026-07-27)
- `benchmark/results/bench-20260704-2316-c29090a/report.md` — the "Judge panel note" with its
  per-panel breakdown, and the "Qualitative root-cause spot-check"

This is pre-existing behaviour, not something the arm-spec refactor introduced. It matters
because the qualitative spot-check is what rules out "harness bug" as the explanation for the
19.6% result — analysis that cannot be regenerated from artifacts.

So, every time:

```bash
cp docs/BENCHMARKS.md /tmp/BENCHMARKS.before.md
wand bench report --publish
diff /tmp/BENCHMARKS.before.md docs/BENCHMARKS.md   # re-apply anything the renderer dropped
```

If this trips anyone twice, the real fix is sentinel markers the renderer preserves — the
same pattern as the `CLAIM` block in `SKILL.md`.

## Why this exists

The "~45% quality improvement, backed by arXiv:2512.14982" claim reached 8 live surfaces
across 3 repos and 1 registry by hand-copy. It was never supported by an artifact, and the
cited paper covers a different technique — prompt repetition — that is not implemented in
this codebase. When the blind A/B benchmark finally measured the actual intervention, the
amplified prompts lost.

Nothing about that failure was malicious; it was structural. No file owned the claim, so
every surface owned a slightly different version of it, and none of them could be corrected
in one place. The canonical file plus this checklist is the smallest structure that makes
that impossible to repeat.
