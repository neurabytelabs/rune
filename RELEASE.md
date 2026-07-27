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

3. **Sync any locally installed copies.** These are runtime caches, not sources:
   ```bash
   cp SKILL.md ~/.claude/skills/rune-prompt-amplification/SKILL.md
   # ...and any other runtime you have installed it into
   ```

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
