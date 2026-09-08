# M1-C usable storyboard canary

Status: **Approved**  
Approved: 2026-09-08  
Source baseline: `29a4998fcf3143579c4b04aea1fa90b692178684` on `codex/m1b-alpha`

## Outcome

Produce one retained, real-model `default`-profile Plotloom project from the
existing fixed Chinese Alpha story. The normal four-stage pipeline must install
one complete canonical result, the storyboard must survive browser refresh, and
one ordinary storyboard edit must survive save and reopen. Review the generated
storyboard as creative material, not only as valid JSON.

## Scope and non-goals

Use the existing application, provider profile, secret-loading path, workbench,
and fixed story. Run against the configured llama server in a new isolated data
directory and retain the result for inspection. Record only secret-free evidence.

Do not contact or qualify the deferred vLLM backend. Do not implement adapter
registry/V3 snapshots, runtime-diagnostic infrastructure, formal nine-run Alpha
qualification, media production, deployment changes, or model-specific behavior.
Do not alter the retained failed canary.

## Decisions

- This is one product canary, not formal backend qualification or product
  Approval.
- Start from the exact source baseline above and use `default`; do not relabel or
  repair the older failed run after its generation contract changed.
- Preserve raw local evidence, but report only hashes, IDs, status, issue codes,
  attempts, timing, token counts, and content-review observations.
- Never print, persist, or report an API key. HTTP over the user's Tailscale LAN
  is an accepted deployment shape.
- Do not replay an `outcome_unknown` request. Do not increase correction limits,
  weaken validators, invent creative values in trusted code, or add provider or
  model exceptions.
- This bounded sequential journey has no independent child lane worth the added
  coordination cost. The coordinator executes it directly.

## Checkpoints

1. **Preflight:** verify clean source identity, the `default` profile's public
   effective configuration and configured llama service readiness without
   revealing secrets. Create a fresh retained data/artifact directory.
2. **Generate:** submit the unchanged first fixed Chinese Alpha story through
   the normal application and follow the run to a terminal state without busy
   polling.
3. **Inspect:** if successful, verify four sealed stages, atomic installation,
   bounded attempt lineage, refresh persistence, and the visible storyboard.
   Review narrative clarity, branch causality, continuity, performance
   readability, shot language/pacing, and likely editing effort.
4. **Edit:** make one normal storyboard edit, save it through the product, reopen
   or refresh, and verify the same edit persists.
5. **Close:** preserve the retained project and secret-free evidence, run only
   checks directly affected by any documentation/evidence change, and report the
   exact result. Do not merge or push.

## Acceptance evidence

The completion report identifies the source commit, public profile/config hash,
project and run IDs, terminal stage/seal state, per-unit attempt counts, stable
issues, absence of `outcome_unknown` and partial canonical installation, refresh
and edit-persistence evidence, provider-reported timing/token counts when
available, and a concise content review. A browser screenshot should be retained
when the workbench result is visible. Run a secret scan over any tracked or
shared evidence.

## Execution authority

The coordinator may create its isolated Plotloom data directory, start and stop
only the Plotloom/browser processes it creates, use the existing configured
secret path for the `default` profile, operate the normal API/workbench, and add
concise secret-free evidence or roadmap updates. It may commit those bounded
repository changes locally.

This assignment does not authorize a new product-contract fix. If generation
fails, preserve the evidence and return the exact responsible layer and smallest
useful next experiment for director review.

## Escalation and stop conditions

Stop safely and report instead of expanding scope when any of these occurs:

- the corrected join-preservation failure recurs;
- a request has unknown submission outcome;
- a secret may have entered evidence, logs, artifacts, or source control;
- the configured llama service is unavailable or reports a materially different
  deployment identity/capacity;
- success would require a prompt, schema, binder, validator, persistence, or
  provider-adapter change;
- the exact baseline cannot be reproduced without rewriting repository history.

