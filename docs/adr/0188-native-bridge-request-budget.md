# ADR 0188: Complete native bridge request budget

Status: Accepted, 2026-10-17

## Problem and evidence

A real 7-scene, 35-cut, 42-target walkthrough was refused before Bridge Intent
enqueue. Its complete native source/target evidence measured 74,043 canonical
UTF-8 bytes against a 60,000-byte ceiling inherited from API intent inference.
The narrower API projection measured 61,149 bytes. The next native Presentation
source/context already measured 250,535 bytes against 180,000, before adding
intent suggestions. These are complete admitted source facts and trusted bindings,
not an oversized model response. Removing repeated story nodes or empty prior
wording cannot bring the native evidence below those ceilings.

## Decision

Native Bridge Intent and Presentation share a **1 MiB (1,048,576-byte) complete
serialized creative-request budget**. Measure canonical UTF-8 JSON of every
`CreativeHandoffRequest` field, including source, input artifacts/schema, identity
and creative brief, before execution-pin reservation, enqueue or package writes.
The bound does not count additional generated package metadata or pinned code/skill
resources; it is not a total filesystem-package size or token count. Bridge
package JSON readers have a separate 2,000,000-byte per-file bound, allowing the
complete request plus generated execution metadata. Publication checks that bound
before writing any package. Other creative stages retain their 1,000,000-byte
JSON readers. Both native executor backends must round-trip a request exactly at
the 1 MiB admission boundary.

Keep every source fact, excerpt, coordinate, hash, prior intent, runtime choice
and frozen evidence unchanged. Keep the existing 128 intent-target and 256
presentation-source limits, strict complete response binders, Unicode span
coverage, provenance, freshness and human/machine review separation. API intent
keeps its independent 60,000-byte prompt-evidence bound: its projection and
provider request contract are not the native file-delivery contract.

This is a finite native admission/storage bound, not a guarantee that every
admitted request fits a model context, will finish on time, or is semantically
faithful. Actual execution and creative review remain separate. Oversized native
requests must still refuse before any new job or dispatch; do not truncate them.

## Rejected alternatives and guardrails

Do not drop complete source evidence, weaken binding, invent a generic reference
codec, remove byte bounds, or force the thin API budget onto full native files.
Regress both stages above their former ceilings, exact UTF-8 boundary acceptance,
all request fields contributing to size, pre-enqueue refusal and unchanged API
limits. Preserve historical failures and frozen execution identities. This budget
change does not authorize rebasing an already-frozen autopilot policy.
