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

`WorkUnitPromptContract m1.12p` freezes the correction policy, directive
registry, evidence projection, and response-schema compiler versions on the
primary attempt. Each correction additionally freezes SHA-256 hashes of the
selected directive set, evidence projection, and full narrowed schema. Resume
and correction lineage compare those immutable snapshots and reject compiler
drift. Terminal historical artifacts remain raw evidence; their absent fields
are not injected, re-saved, or re-hashed.

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
  grouping, deterministic overlay hashes, JSON null, and conflicting authority.
- Tests cover every continuity boundary, ordered-ID replay, foreign/non-adjacent
  rejection, source-response rebinding, exact fact/scalar assignment, and
  required entity presence.
- Retired dialogue-duration witness facts remain parseable as historical
  evidence but are outside the current executable repair-fact union.
- Pipeline tests prove current compiler versions are present on primary attempts,
  correction hashes are present only on corrections, and recovery rejects drift.
- Prompt and receipt fingerprints change with these contracts, so prior live
  qualification cannot be relabelled as evidence for this version.
- Live Alpha qualification begins only after both saved profiles pass a fresh
  probe whose effective context agrees with their declared profile capacity.

This decision refines ADR 0013, ADR 0017, and ADR 0019. It does not change the
three-attempt maximum, frozen profile, immutable attempt evidence, exact repair,
or atomic installation rules.
