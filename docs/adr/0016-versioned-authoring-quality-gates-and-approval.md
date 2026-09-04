# ADR 0016: Versioned authoring, quality gates, and approval

## Status

Accepted.

## Context

ADR 0012 established the production-authoring direction, but its semantics
were not yet executable at the canonical revision boundary. In particular,
free-text dialogue/audio, floating durations, and unversioned historical stage
JSON cannot prove a reproducible production-quality decision. Treating old
payloads as current and filling new fields from defaults would fabricate
speakers, anchors, entity states, timing, and approval evidence.

The missing contract sits between authored canonical data and M2 production
execution: authoring must have an explicit schema and deterministic quality
receipt before a human can approve its exact revision.

## Decision

### Schema and historical evidence

Canonical stage payloads carry a schema version. Schema 1 remains an explicit
read model for historical revisions, snapshots, plans, and seals. Migration
adds only the version scalar (`1`) to legacy rows; it does not parse, rewrite,
rehash, or materialize V2 defaults into historical JSON.

Schema 2 is the only current authoring-write model. New project bootstrap,
manual stage writes, generated aggregates, and current runtime inputs parse
through `stage_payload_model(stage, schema_version=2)`. An active V1 head is
not a partially upgradeable V2 document: a current read, write, planning,
approval, or production operation that needs it fails closed with
`schema_reset_required`. Historical evidence remains inspectable through its
explicit V1 read path.

### V2 authoring time and sound

All authored V2 timing is an integer `durationUnit` measured in milliseconds.
`DramaticScene` has a stable node-local order and a duration budget; ordered
shots derive scene, node, and explicitly selected-path timecodes without
float-rounding. A budget is an upper bound, not a requirement to pad a scene.

`DialogueCue` is the sole dialogue authority. It is owned by one beat, has a
stable local order, and names exactly one character speaker or explicit
voice-over. Its bounded delivery pace selects a rule from a versioned timing
profile; free-form performance notes do not select timing. `AudioPlan` records
timed ambience, sound effects, diegetic sound/music, and score. Bible entities
declare anchors, allowed states, and continuity rules; shots state the entity
states they require rather than provider reference slots.

### Server-authoritative quality receipts

The server evaluates a fixed, versioned storyboard gate set from the exact V2
storyboard revision and frozen canonical inputs. It persists immutable,
revision-scoped `GateResult` records with a deterministic input hash, gate-set
version, concrete gate identity, path, evidence, severity, status, and reason.
The server—not a browser, provider, or arbitrary repository caller—constructs
and records an approval-eligible receipt. Approval accepts only the canonical
gate-set version and a receipt recomputed for the exact current revision.

Required gates include scene/shot order, budgets, cue ownership/order/reference
and fit, audio timing, entity-state availability, exactly one PRIMARY coverage
with optional SUPPORTING coverage, and adjacent continuity. Required `skipped`
and `not_applicable` outcomes are not passing outcomes. A gate receipt is part
of the same transaction that installs a successful storyboard revision.

### Approval and M2 production boundary

An approval is append-only and binds the canonical storyboard subject, exact
entity revision, content hash, canonical input revisions, and considered
gate-set version. It is active only while that exact READY head and all frozen
upstream revisions and required gates remain current. A revoke is a new ledger
decision; edits make prior approvals stale rather than transferring them.

M1's local workbench has no authentication authority. Its `reviewer` field is
therefore an operator-supplied audit label, not a verified identity or an
authorization claim. A networked or multi-user deployment must bind approval
reviewer identity and permission to a server-authenticated principal before
using the ledger as an access-control record.

Until M2 implements `ProductionSnapshot` and `ProductionUnit`, media work is a
hard stop at this boundary. No media task, provider request, reference binding,
or source URI may be derived directly from a Shot or merely valid storyboard.
M2 must require an active exact approval and freeze the approval, canonical
revisions, gate receipt, dialogue/audio schedule, reference artifacts, and
compiler inputs into an immutable ProductionSnapshot.

## Rejected alternatives

- Silently upgrading V1 JSON with V2 defaults or free-text inference.
- Letting browser code, a model response, or an adapter submit a gate receipt.
- Treating a skipped required gate as pass, or accepting an arbitrary gate-set
  version for approval.
- Using seconds/floats or provider frame positions as canonical timing IDs.
- Copying dialogue into beat, shot, prompt, and dubbing structures.
- Allowing valid-but-unapproved storyboards to enqueue media before M2's exact
  ProductionSnapshot boundary exists.

## Consequences and guardrails

- V1 active projects require an explicit reset/re-authoring flow; they are not
  rewritten in place.
- Every new V2 storyboard installation must atomically persist its canonical
  receipt, and Approval must prove the receipt came from server evaluation.
- Gate identities must remain stable, revision-scoped in persistence, and safe
  for authored identifier lengths; new gate-set behavior requires a version.
- Timeline derivation must reject invalid scene/shot order and invalid selected
  graph paths rather than deriving a plausible sequence from malformed data.
- Tests must cover historical-byte preservation and active V1 reset refusal;
  deterministic receipt identity and forged-receipt rejection; approval,
  revoke, stale upstream/head behavior; required skipped failure; timing and
  path determinism; and M2 media hard-stop behavior.

This ADR implements and narrows the executable M1 portion of ADR 0012. ADR
0012 remains authoritative for the later ProductionUnit and ProductionSnapshot
design.
