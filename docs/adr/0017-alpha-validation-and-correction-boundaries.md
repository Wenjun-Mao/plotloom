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

Dialogue timing originally appeared to have the same boundary in a different
form. Live-model evidence later showed that asking a provider to reproduce
exact character-count arithmetic was itself the ownership error. ADR 0018
supersedes that timing mechanism: trusted code now derives cue duration and
allocates absolute scene budgets, while this ADR continues to govern how known
response failures enter bounded correction.

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

### Deterministic repair facts

Correction packets contain only the frozen response contract, immutable
topology/selector facts, the preceding final `message.content` when available,
and stable issue code/path pairs. They never use `reasoning`,
`reasoning_content`, arbitrary validator or exception messages, or secret
material.

Repair facts are narrow discriminated records, not generic validator payloads.
For example, a join whose `allowedDifferences` are not a subset of its tracked
`requiredStateKeys` receives only the join ID and exact missing keys when both
source arrays are nonblank and unique. Blank, duplicate, malformed, or
unrelated data produces no repair fact and remains fail-closed. A persisted
fact must also match the exact code and path of an issue in the same immutable
validation artifact; syntactic validity alone never grants correction
authority. Timing is now handled by ADR 0018's trusted projection; persisted
legacy timing facts remain parseable only so old evidence can be read without
broadening new authority.

The same rule applies to Storyboard entity-state repair. When an otherwise
schema-valid response selects a state outside an entity's frozen Story Bible
vocabulary, trusted code may emit only the exact issue path, entity type and
ID, and the nonempty `allowedStates` list from that frozen dependency. The
invalid model value and validator prose are not repair authority. A malformed
path, missing entity, wrong type, empty vocabulary, or schema-invalid response
produces no fact. The correction must preserve the entity identity and choose
one allowed value byte-for-byte.

Cross-field wire rules that are already part of the response model must also
be explicit in both primary and correction prompts. In particular every
dialogue cue writes both `speakerId` and `voiceOver`, with exactly one non-null.
This avoids a bounded correction losing a schema invariant merely because its
stable issue packet intentionally omits free-form Pydantic messages.

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
- **Send arbitrary issue payloads to correction.** Rejected because a path and
  code do not establish which values are safe for a model to change.
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
- Tests must prove typed repair facts reject unknown discriminators, duplicate
  keys, blank values, and malformed source data, and that neither reasoning,
  free-form errors, nor secrets enter a correction packet or secret-free
  receipt.
- Tests must prove an invalid Storyboard entity state receives only the exact
  frozen whitelist and succeeds through normal bounded correction, while
  malformed or unbound state evidence remains fail-closed.
- Tests must prove a persisted rejected response cannot be corrected after its
  base or correction-template contract changes across a restart/deployment.
- Alpha receipts must distinguish stable rejected-response issue codes from
  application-owned failure codes while retaining their strict public field
  set. Complete acceptance evidence is confined to the runner's disposable
  temporary database and artifact directory, which are deleted after the run;
  only the whitelisted receipt and blinded review samples may be promoted.

This decision refines ADR 0013's bounded correction contract. ADR 0018 now owns
the dialogue and scene timing boundary without changing the secret, snapshot,
or atomic installation rules defined here.
