# ADR 0017: Alpha validation and correction boundaries

## Status

Accepted.

## Context

The first continuous-creation Alpha matrix exposed a contract gap rather than
a provider-specific capability problem. A model-facing Story Graph content fill
can express values accepted by an intermediate compatibility model but rejected
by the V2 canonical projection. One observed example is an empty string for a
continuation edge's `choiceText`: it is neither the canonical `null` value nor
a valid choice label.

When an expected output-validation exception crosses the generic worker
boundary, the durable record becomes `validation.internal_error` with no
structured issue and no correction eligibility. This safely prevents an
unknown program failure from being retried, but it also makes a known,
model-correctable contract violation look like a local implementation fault.
The secret-free Alpha receipt can then report only the coarse failure code.

Dialogue timing has the same boundary in a different form. A model may supply
an estimated duration below the versioned language/delivery minimum. That is a
deterministic semantic rejection, not free-form reviewer advice, and must be
repairable without exposing hidden reasoning, arbitrary exception prose, or
credentials.

## Decision

### One topology contract from schema through canonical projection

Topology-owned facts constrain every representation of Story Graph content.
The model-facing schema, the deterministic binder, and the V2 projection must
agree on edge kind and its legal content:

- a choice edge requires non-blank `choiceText`;
- a continuation edge requires `choiceText: null`; and
- topology-owned IDs, endpoints, kinds, and join membership remain outside
  model authority.

The schema may use topology-bound constraints to prevent avoidable invalid
output, but the binder remains the final authority. The binder explicitly
checks model-controlled edge and join invariants, then performs a complete V2
projection before returning a canonical value. No compatibility model may
silently broaden what the canonical projection accepts.

### Expected model validation is a rejected response

Expected parsing, schema, binding, and semantic validation failures must be
normalized into stable `ValidationIssue` values with data paths. They persist
the response and validation artifact, finish the attempt as a known rejected
response, and enter the frozen primary-plus-at-most-two correction lineage.
The correction source is the immediately preceding failed attempt and retains
the existing response-persisted, non-unknown, immutable-evidence requirements.
Before rendering a correction, its persisted base contract must exactly match
the current executable base contract. A later correction must also retain the
same correction-template identity and policy. A deployment that changes either
contract fails closed with `contract.correction_source_changed`; it never
silently reinterprets or replays an older rejection.

This does not turn every exception into a retry. Programming faults, repository
failures, corrupted frozen contracts, artifact persistence failures, provider
preflight failures, cancellation, and outcome-unknown delivery states remain
fail-closed. They receive a stable application-owned outcome code and cannot
authorize a correction. Internal evidence may retain a safe error type for
diagnosis; secret-free receipts must not include exception messages, prompts,
raw responses, endpoints, model names, IP addresses, or credentials.

### Deterministic repair facts, including dialogue timing

Correction packets contain only the frozen response contract, immutable
topology/selector facts, the preceding final `message.content` when available,
and stable issue code/path pairs. They never use `reasoning`,
`reasoning_content`, arbitrary validator or exception messages, or secret
material.

Dialogue duration repair uses the versioned deterministic timing policy as a
contract fact. The primary Scene Beats prompt receives the complete manifest
serialized from that policy as a named prompt variable; it does not repeat
units-per-character constants in YAML. A correction receives only trusted,
per-cue quantities derived from the same policy, plus nullable scene-budget
facts when local IDs and ownership are unambiguous. It never asks the model to
infer a pace from prose. Changing the timing policy requires a new version and
a corresponding prompt/validator contract update.

## Rejected alternatives

- **Retry every `validation.internal_error`.** Rejected because a code defect,
  corrupted artifact, or uncertain provider result is not trustworthy model
  feedback and must not cause a blind replay.
- **Relax the V2 projection to preserve compatibility-model values.** Rejected
  because canonical data would become ambiguous and the schema, binder, and
  editor would diverge.
- **Put free-form error text or model reasoning into corrections.** Rejected
  because it is unstable, can leak private/provider data, and turns diagnostics
  into unversioned generation authority.
- **Teach timing only in a correction prompt.** Rejected because first-pass
  output must be governed by the same deterministic timing rule as repairs.
- **Add aliases or model-vendor exceptions.** Rejected because Alpha failures
  are repaired at the shared contract boundary, not by model-specific paths.

## Consequences and guardrails

- Tests must prove that a continuation `choiceText` empty string or other
  V2-projection-only invalid value produces a stable issue and bounded
  correction lineage, never `validation.internal_error`.
- Tests must prove that binder/schema constraints reject topology changes and
  that schema, binder, and V2 projection agree for every edge kind and join
  invariant.
- Tests must prove a deliberately injected programming exception remains a
  one-attempt fail-closed failure and cannot become correction-eligible.
- Tests must prove `semantic.cue_duration_underestimated` carries a stable
  path, that the primary contract receives the full versioned policy while the
  correction receives only safe policy-derived quantities, and that neither
  reasoning, free-form errors, nor secrets enter a correction packet or
  secret-free receipt.
- Tests must prove a persisted rejected response cannot be corrected after its
  base or correction-template contract changes across a restart/deployment.
- Alpha receipts must distinguish stable rejected-response issue codes from
  application-owned failure codes while retaining their strict public field
  set. Complete acceptance evidence is confined to the runner's disposable
  temporary database and artifact directory, which are deleted after the run;
  only the whitelisted receipt and blinded review samples may be promoted.

This decision refines ADR 0013's bounded correction contract and ADR 0016's
versioned dialogue timing without changing their secret, snapshot, or atomic
installation boundaries.
