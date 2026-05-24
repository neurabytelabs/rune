# RUNE × Agent Mesh Cronjob Lineage Demo

This is a staged, zero-install decision demo for RUNE Visible Lineage.

It models how Mustafa's Hermes agent mesh can evolve from a vague recurring prompt into a safer recurring operating loop:

1. generic "check agents and cronjobs" prompt
2. role-specialized RICK / SUMMER / MORTY prompts
3. unified daily Agent Mesh brief
4. escalation-safe recurring cron loop with guardrails and reply codes

## Run locally

```bash
open demo/agent-cron-lineage/index.html
```

## GEPA-viz data

`run.json` is GEPA-viz-compatible. If a GEPA-viz app is running separately, load this file as the run data.

## What this demo is testing

The question is not "can RUNE draw a graph?" The real question is:

> Does visible lineage help us design, compare, and govern recurring autonomous prompts?

For the Hermes mesh, the answer is likely yes when used narrowly:

- daily/weekly cron briefs
- agent-role prompt design
- escalation rules
- noisy alert reduction
- decision reports with P#/S# reply codes

It should **not** become a mandatory runtime dependency for RUNE or Hermes.

## Recommendation

Ship visible lineage as a **small export + demo feature**, not as a heavyweight UI integration.

Good default scope:

- `wand lineage --export-gepa run.json`
- zero-install HTML demos for decision/pitch surfaces
- optional GEPA-viz inspection when useful

Avoid for now:

- mandatory GEPA-viz install
- automatic cronjob rewrites
- graphing every prompt by default
- replacing human approval for protected agent/service domains
