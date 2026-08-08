# Redactions

Applied 2026-08-08 to run `bench-20260704-2316-c29090a`.

One prompt in the committed prompt set, `p003`, was written against the author's
own infrastructure. It named a **private** repository and enumerated the host
hardware of three machines. Publishing the run artifacts verbatim would have
disclosed that; the prompt was redacted instead of removed, because `p003` is
load-bearing evidence — it is one of the five coding pairs hand-read to rule out
a harness bug as the explanation for the headline result (see `docs/BENCHMARKS.md`,
"Is this a harness artifact?").

## What was replaced

| Original | Replacement |
|---|---|
| `github.com/<private-org>/<private-repo>` | `github.com/<org>/<repo>` |
| `M3 MacBook` / `M4 Mac Mini` / `M1 Mac Mini` | `machine A` / `machine B` / `machine C` |
| bare `M3` / `M4` / `M1` in the same context | `machine A` / `machine B` / `machine C` |
| `Mac mini`, `MacBook` (any case) | `machine` |
| model-invented hostnames `rick-macbook`, `morty-m4`, `summer-m1` | `agent-a-host`, `agent-b-host`, `agent-c-host` |

252 substitutions across 7 files: `promptset_v1.jsonl`,
`results/bench-20260704-2316-c29090a/generations.jsonl`, and
`results/bench-20260704-2316-c29090a/judge_inbox/pairs_j1..j5.jsonl`.

## What was deliberately **not** redacted

- **Agent names `RICK`, `MORTY`, `SUMMER`.** Already public — the author has
  published a post describing this three-agent setup by name.
- **"All agents have SSH access to each other and GitHub."** This is a design
  premise of the question, not a disclosure: no hosts, users, keys or ports.
  Removing it would change what was asked.
- **Model-invented paths and branch names** (`tasks/pending/morty-login.md`,
  `task/morty/login-api`, `ssh morty@<morty-ip>`). Illustrative output, not real
  infrastructure; the IP was already a placeholder in the generated text.
- **Everything in the other 24 prompts.** A scan of all 25 prompts and all 100
  generations for credentials, tokens, IP addresses, hostnames, local filesystem
  paths and email addresses returned nothing. 18 of 25 prompts matched no pattern
  at all. Where a pattern did match, it was already present in the prompt — the
  models introduced no new identifying detail.

## What this does and does not affect

**No number changed.** No arm was re-generated and no pair was re-judged. The
substitutions are semantically neutral: `p003` still asks for a multi-agent Git
collaboration architecture across three machines, which is what the judges
compared.

**The judges scored the pre-redaction text.** A replication that runs the
redacted prompt set will not reproduce these artifacts byte for byte, and may
differ marginally in generated output. The result in `docs/BENCHMARKS.md` stands
as the record of the original run.

**`manifest.json` records both hashes.** `promptset.sha256` now matches the
redacted file; the pre-redaction hash is preserved under `redaction.
promptset_sha256_before_redaction` (`a45bd0f3…`).

**`generations.jsonl` `chars_out` is unchanged** and reflects pre-redaction
output length. It is a record of what the model produced, not of what this file
now contains.

## Prior exposure

The unredacted artifacts were pushed to public branches
(`feat/bench-arm-specs`, `fix/align-claims-with-benchmark`) on 2026-07-27 and
were reachable until this redaction. This redaction is forward-looking hygiene —
it keeps the disclosed detail off `main` and out of what readers and indexers
see — not containment of an exposure that already occurred. Nothing disclosed was
a credential.
