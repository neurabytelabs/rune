# RUNE × GEPA Local Lineage Demo

This folder is a zero-install local demo for the RUNE v2.1 visible-lineage release.

## Files

- `run.json` — GEPA-viz-compatible candidate tree exported from the RUNE lineage shape.
- `index.html` — self-contained local viewer for the same data; no server or package install required.

## Run locally

```bash
open demo/gepa-lineage/index.html
```

Optional GEPA-viz path, if an upstream GEPA-viz app is running separately:

```bash
# Load demo/gepa-lineage/run.json into the GEPA-viz app.
```

## What to look for

The demo shows one rough prompt evolving through two refinements:

1. broad founder-agent prompt, score `0.58`
2. structured launch brief prompt, score `0.76`
3. observable RUNE release prompt, score `0.88`

The point is not the sample copy. The point is that RUNE can now make prompt evolution visible: parent links, score movement, strategy, model metadata, and feedback are all inspectable.

Keep GEPA-viz optional. RUNE should export clean data; viewers can remain outside the runtime dependency chain.
