# ADR 0022: Executable correction directives and continuity ownership

## Status

Accepted.

## Context

The M1-C live preflight exposed two shared contract defects. A Story Graph
correction received several repeated join facts but no issue-selected execution
contract, while a Scene Beats correction received only
`semantic.continuity_beat_sequence_mismatch` and a broad continuity reminder.
All three attempts returned the same incompatible boundary because neither the
stable issue nor free-form validator prose identified which endpoint owned the
value or the exact field assignment. Separately, one local service advertised a
larger configured context in Plotloom while its runtime properties reported only
8192 tokens for each active slot; responses ended with `finishReason=length` at
that physical limit. These are contract and deployment-capacity mismatches, not
reasons for model-, alias-, or provider-specific behavior.

A later retained preflight exposed the same class of defect for dialogue cue
ordering. The model correctly repaired the `speakerId`/`voiceOver` XOR, but then
numbered two cues on different beats as `1, 2`. The semantic validator correctly
requires every beat's cue sequence to restart at `1`; both remaining attempts
repeated the error because `semantic.cue_order` had neither deterministic repair
facts nor a narrowed response schema. The failure therefore belonged in the
shared correction contract, not in tolerant validation or a model exception.

A subsequent retained Storyboard preflight exposed a related acceptance gap.
The deterministic timing planner produced a complete, hash-bound replacement
for shot timing, cue placement, and beat coverage. The first correction fixed
the original timing issue but changed plan-owned coverage and introduced a
duplicate link. Because timing authority was prompt-only and exact
postconditions ran only after semantic acceptance, Plotloom created a generic
coverage correction that no longer carried the original timing plan. The final
attempt then lost cue coverage. The planner and validator were correct; the
missing contract was executable enforcement at correction acceptance.

## Decision

### Corrections execute an issue-selected, versioned contract

The repository owns a static directive registry. A correction receives only
the directives selected by its revalidated stable issue codes. Known schema
issues rely on the closed response schema; known semantic families have explicit
repository text; an unknown semantic code fails closed. Validator messages and
model reasoning are never correction authority.

The prompt evidence projection is independently versioned and hashed. It may
group operationally identical join facts to reduce repetition, but preserves
their source indexes and all issue paths. The durable validation artifact keeps
the complete original facts unchanged.

Typed facts may additionally narrow a deep copy of the base response schema.
Current overlays make exact join arrays, incoming-edge key presence, proven
join values, and continuity assignments machine-readable. Every response-local
continuity target is required to remain present; exact entity-state assignments
cannot be satisfied by deleting the entity entry. The ordinary fragment and
canonical validators remain mandatory after provider output and are never
relaxed or replaced by an overlay.

Some issues are derived from fields that are themselves invalid. The immutable
validation artifact retains the complete issue list, while a versioned issue
selection contract partitions code/path pairs into executable and deferred
sets. In particular, a continuity sequence mismatch without an exact fact may
be deferred only when the same rejection contains a continuity entity/state or
finite-JSON blocker. The prompt and schema receive only executable authority;
after that repair, ordinary revalidation either clears the sequence issue or
produces its exact fact. Unsupported issues and missing facts without a named
blocker still fail closed.

Deferred issue identities and paths remain in the immutable validation
evidence. The complete deterministic selection is persisted beside the
rendered messages as audit-only prompt-artifact data, and its version and hash
bind the executable/deferred partition, reason, and blockers. None of those
deferred details are included in a model-visible message or response schema.
The model-facing projection contains only executable code/path pairs and
bindings whose indexes are local to that executable projection.

`WorkUnitPromptContract m1.13` freezes the correction policy, issue selector,
directive registry, evidence projection, and response-schema compiler versions
on the primary attempt. Each correction additionally freezes SHA-256 hashes of
the issue selection, selected directive set, evidence projection, and full
narrowed schema. Resume and correction lineage compare those immutable
snapshots and reject compiler drift. Terminal historical artifacts remain raw
evidence; their absent fields are not injected, re-saved, or re-hashed.

### Bible vocabulary and authored entity-state effects have separate owners

`stateEffects` remains the Story Graph author's arbitrary finite-JSON fact
map. It never acquires entity identity through a suffix, prose, or synonym. An
edge that changes a Story Bible character, location, or prop instead carries
an explicit `entityStateEffects` item with `entityType`, `entityId`, and
`state`. The Bible author owns the allowed vocabulary; the graph/fragment
author chooses an actual member; trusted code validates exact entity/type and
membership before graph seal or canonical save. Typed effects travel unchanged
through the graph binder and Scene Beats incident-edge context. They are not
converted from historical `stateEffects`, and arbitrary facts remain separate.

Graph entity-state effect violations deliberately fail closed at graph seal.
`semantic.invalid_entity_state_effect` and
`semantic.unknown_entity_state_effect_entity` do not enter the bounded
correction directive registry: a correction has neither authority to choose a
Bible state nor to replace an authored entity identity. The correction planner
raises a named, stable fail-closed error that requires a new Story Graph
generation, rather than accepting an arbitrary replacement or falling through
as an unclassified runtime exception. This is intentionally narrower than the
Scene Beats continuity repair fact, whose rejected response already identifies
the entity and whose frozen Bible supplies only an allowed literal vocabulary.
The durable correction attempt records
`contract.graph_entity_state_effect_correction_forbidden` rather than flattening
this disposition into a generic source-change failure.

For `semantic.invalid_continuity_entity_state`, current correction contracts
emit a source-rebound `ContinuityEntityStateRepairFact`: the exact response
path, response-local boundary identity, entity type/ID, array index, and the
ordered allowed-state vocabulary from the frozen Bible. Its schema overlay and
application postcondition require that same entry and identity to remain and
allow only the listed literals. The directive may rely only on that fact, not
on an absent schema enum or validator prose. Unknown entities, wrong types,
and malformed or stale facts receive no vocabulary authority and fail closed.

This changes current generation semantics, so planning, work-unit, directive,
and response-schema versions advance together. Nonterminal plans under the
prior planning version fail recovery rather than resuming with a different
contract. Retained raw prompts, responses, seals, and hashes remain untouched.

### Join corrections retain only source-proven valid sibling assignments

A retained Story Graph preflight showed that an issue-selected correction could
repair one required join key while deleting a different required key that was
already valid. The original fact/schema/postcondition contract named only the
failed key, so the validator correctly rejected the deletion but the next
correction had no executable authority to retain the sibling assignment.

`JoinStateEffectRepairFact` now carries `preservedStateEffects` only for other
required keys whose complete values already satisfy the rejected response's
frozen join contract: every exact incoming edge is present, every value is
finite canonical JSON (including an explicit JSON null), and a non-variant key
has one canonical value across its incoming edges. Each preserved key binds the
exact ordered incoming-edge membership and the exact per-edge value. The
response-schema overlay and provider-independent postcondition require those
assignments to remain unchanged while the issue-selected key is repaired.

This is preservation authority, not branch-value selection. Any key with a
missing, conflicting, non-finite, or allowed-difference-promotion issue in the
same rejected response is excluded from preservation, so simultaneous repairs
remain free to repair invalid fields and cannot receive contradictory frozen
constraints. Immediately before compiling a correction, Plotloom re-extracts
the rejected final and deterministically re-derives the whole join fact against
the frozen topology and validation issues; a fabricated edge ID, changed value,
or fact rebound to another source is rejected. The current policy/compiler
identities are `bounded_correction.v23`, `correction_directives.v5`,
`correction_evidence_projection.v3`, and `correction_response_schema.v5`.
Older artifacts retain their original JSON, hashes, and seals; they are neither
rewritten nor relabelled as evidence for this contract.

### Continuity repairs have one deterministic boundary owner

`ContinuitySequenceRepairFact` carries the ordered response-local item IDs and
only the incompatible adjacent boundaries. Its assignments contain complete
finite JSON fact values, valid Story Bible entity states, or declared visual and
sound scalars. Notes and one-sided declarations are outside its authority.

For Scene Beats, ownership flows left to right:

- scene entry owns the first beat entry;
- each beat exit owns the next beat entry; and
- the last beat exit owns the scene exit.

For Storyboard, the enclosing canonical scene owns both outer boundaries:

- canonical scene entry owns the first shot entry;
- each shot exit owns the next shot entry; and
- canonical scene exit owns the last shot exit.

Persisted facts are accepted only when every endpoint is one of these exact
adjacent pairs in the frozen ordered sequence. Immediately before a correction
is compiled, Plotloom re-extracts the rejected final content and deterministically
recomputes each continuity fact against the frozen Story Bible and scoped scene
context; the persisted fact must match exactly. A foreign, renamed, reordered,
or non-adjacent target cannot authorize an overlay merely by being internally
self-consistent.

### Cue ordering uses complete, source-bound assignments

`CueOrderRepairFact` carries the complete response-local cue membership as
`localCueId`, `beatLocalId`, and exact `expectedOrder` assignments. Plotloom
preserves the model's relative intent by sorting cues within each beat by the
declared order and original array position, then renumbers each beat from `1`.
The correction schema fixes collection cardinality using the same basic array
keywords already present in primary schemas. A provider-independent application
postcondition then requires exactly one matching item for every assignment. The
contract cannot be satisfied by deleting, renaming, duplicating, or moving a cue
to another beat even when native JSON Schema is unavailable or ignored.

Immediately before compilation, Plotloom re-extracts the rejected final content
and independently re-derives the fact. A persisted fact whose identities,
membership, beat ownership, or order differ from that source is rejected. When
the same rejection includes an issue that can change beat or cue membership,
cue-order repair is deferred as audit-only authority until structural repair and
ordinary revalidation produce a stable collection. There is no server-side
renumbering and the semantic validator remains unchanged.

Native response schemas are an advisory constrained-decoding aid, not the trust
boundary for exact repair authority. Plotloom does not add `oneOf` or
`contains` solely to express the cue contract under the undifferentiated
`jsonSchema` capability: OpenAI-compatible servers support different schema
subsets. The ordinary local model/semantic validator enforces the voice-source
XOR, while the application postcondition enforces exact repair facts. A future
provider-schema dialect contract may safely opt into richer lowering without
changing canonical acceptance.

### Storyboard timing plans are executable before semantic retry branching

`StoryboardTimingRepairPlanFact` owns an exact replacement for target shot
identity, order, duration, ordered cue IDs, PRIMARY coverage, and SUPPORTING
coverage. Plotloom checks those fields against the decoded correction before it
branches on ordinary semantic acceptance. A mismatch is terminal
`contract.correction_output_constraint_mismatch`; it cannot create a descendant
generic correction that silently drops the timing plan. A plan-following
response still passes through the complete Storyboard validator, which may
authorize a later correction for an unrelated issue.

The response-schema compiler projects the same target cardinality, allowed shot
IDs, per-shot values, and exact coverage collections as a decoding aid. It does
not use richer collection-membership keywords to claim target presence or
uniqueness under the generic provider capability; the application postcondition
remains the trust boundary. Source-relative `removeAudioEventIndexes` cannot be
proven from a replacement response alone, so remaining audio legality stays
owned by the ordinary Storyboard validator rather than an inferred deletion.
No response is patched server-side and no provider or model receives a special
case.

Immediately before correction compilation, Plotloom extracts the rejected final
content and deterministically rebuilds the timing plan from that value and the
frozen guidance. The persisted fact must equal the rebuilt plan in full. A
self-consistent, re-hashed substitute plan for the same scene is therefore not
trusted merely because it carries the expected guidance hash.

### Declared provider context must match effective per-request capacity

The saved profile's `textContextWindowTokens` is a trusted execution claim, not
a request to make an upstream server larger. Operators must verify the effective
per-request or per-slot context exposed by that server. When a runtime divides a
total context pool across parallel slots, the configured total must be large
enough that each Plotloom request receives at least the profile value. A mismatch
is corrected in the service or profile configuration and then re-probed; Plotloom
does not add a model-name exception, lower a validator, or reinterpret truncated
output as valid JSON.

## Rejected alternatives

- **Repeat all semantic instructions on every correction.** Rejected because it
  enlarges prompts and silently authorizes unrelated edits.
- **Copy free-form validator messages into prompts.** Rejected because prose is
  unstable diagnostic evidence, not a versioned execution contract.
- **Choose a join branch value in trusted code.** Rejected because no branch is
  authoritative unless surviving peers prove one exact convergent value.
- **Patch a rejected response server-side.** Rejected because corrections must
  remain visible model attempts followed by the same validators.
- **Special-case either local model.** Rejected because the observed defects are
  shared schema, continuity, and runtime-capacity contracts.

## Consequences and guardrails

- Tests cover directive selection, unknown-code rejection, lossless join-fact
  grouping, deterministic issue-selection and overlay hashes, deferred derived
  continuity issues, JSON null, and conflicting authority. Join preservation
  tests cover source rebinding, frozen membership, per-edge variant values,
  JSON null, and simultaneous repairable keys remaining unfrozen.
- Tests cover every continuity boundary, ordered-ID replay, foreign/non-adjacent
  rejection, source-response rebinding, exact fact/scalar assignment, and
  required entity presence.
- Tests cover beat-local cue renumbering, complete membership postconditions, source
  rebinding, structural deferral, provider-independent postconditions, and
  rejection of conflicting authority.
- Tests cover Storyboard timing-plan shot and coverage exactness, advisory
  schema projection, pre-semantic postcondition precedence, terminal mismatch,
  and the absence of a hidden descendant retry after plan violation.
- Retired dialogue-duration witness facts remain parseable as historical
  evidence but are outside the current executable repair-fact union.
- Pipeline tests prove current compiler versions are present on primary attempts,
  correction hashes and inspectable audit selections are present only on
  corrections, and recovery rejects drift.
- Prompt and receipt fingerprints change with these contracts, so prior live
  qualification cannot be relabelled as evidence for this version.
- Live Alpha qualification begins only after both saved profiles pass a fresh
  probe whose effective context agrees with their declared profile capacity.

This decision refines ADR 0013, ADR 0017, and ADR 0019. It does not change the
three-attempt maximum, frozen profile, immutable attempt evidence, exact repair,
or atomic installation rules.
