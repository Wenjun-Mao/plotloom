# ADR 0137: Retained video evidence and production admission

Status: Accepted for the demonstrated E21/E22 repair, 2026-10-08.

## Problem

The native media archive walkthrough retained all original and derivative bytes,
but `current=false` was interpreted as stale inputs and inadequate footage.
Derivative preview also required production currentness. Lifecycle permission,
frozen-input applicability and immutable evidence integrity are different owners.
Simply removing the preview currentness check would lose its frozen-hash guards.

## Decision

- Video projections name `lifecycleStatus` (active/archived) and `inputStatus`
  (current/stale/invalid). Immutable frozen-request integrity precedes applicability;
  archive alone does not invalidate input bindings. Existing operational `current`
  and selection/dispatch/playback gates continue to require active/current inputs.
- Segment projections name `previewEligible`: retained evidence can be read when
  its exact project/job ownership, frozen request/source timing, original identity,
  proposal hash, window and derivative metadata are intact. This pure integrity
  check does not consult current approvals, references, catalogs or lifecycle.
  Streaming still verifies derivative bytes, including Range requests.
- Currentness uses the same frozen integrity owner before session-owned current
  bindings. Malformed shapes, booleans masquerading as integers, inconsistent
  source shot IDs and window bounds fail closed, not with incidental exceptions.
  Supported adapter identity selects its explicit frozen schema; unknown identity
  cannot skip H3 validation. Parse that schema with the adapter-owned production
  contract, not the current catalog. Preserve invalid raw snapshots for diagnostics
  and guard their display reads rather than replacing evidence.
- Archive permits retained preview only. Preparation, review, reopening, selection
  and story playback keep their existing lifecycle/currentness refusal boundaries.
  UI guidance distinguishes archive, stale inputs, invalid evidence, rejection and
  actual timing failures; local preview choice is not an authoring operation.
  The storyboard page admits read-only media navigation/preview while its owning
  structural/review fieldset and individual media write actions stay disabled.
  Workspace loading/failure still locks the entire host. Other pages retain their
  existing host lock until they have an equivalent read/write-control contract.
- Current Wan preparation records its explicit cost policy. Remove the historical
  missing-policy accounting inference; no compatibility adapter or data migration.
- Mounted visual/video readers include the authoritative project lifecycle revision
  in their read identity. Archive/restore withdraws old projections immediately and
  rereads without remounting the editor or resetting local H3 settings. Held responses
  cannot publish across lifecycle revisions. Permission/loading flags are not read
  identity; they must not create refresh loops. Retire tests requiring execution of
  obsolete request shapes; incomplete current contracts fail closed.
- A ready archived media read does not admit durable visual-intent/image-direction
  writers. Preserve their local buffers, suspend autosave and quiescence persistence,
  and resume only after restore plus a ready current read. Disabling form controls
  alone is insufficient because autosave is a separate writer.
  The shared project draft coordinator holds canonical lifecycle write admission;
  retained media/review writers consult it at flush/discard and after awaiting an
  older write. Failed deletion can release suspension but cannot grant archived
  writers permission to resume persistence. Archive/restore ACKs update admission
  even for a directory target no longer visible in the current editor.

## Alternatives and guardrails

Reject changing currentness to admit archive, hiding retained proposals, treating
rejection as a timing error, or granting preview eligibility from a metadata-only
copy without its frozen job hashes. ADR 0082's retained-comparison rule and explicit
production admission remain separate. Test active/archive/restore, stale/rejected
retained reads, malformed/rehashed inputs, cross-project ownership and corrupt
derivative bytes. Native archive/restore pixels and unchanged bytes are a separate
acceptance gate, not implied by unit tests. Creative/media quality is excluded.
