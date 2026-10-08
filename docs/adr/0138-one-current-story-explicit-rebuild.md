# ADR 0138: One current story with explicit production rebuild

Status: owner-approved contract, 2026-10-08; implementation and native revision
acceptance pending. Supersedes only the first-install-only restrictions in ADRs
0079, 0118 and 0121. Their source ownership, exact review and dispatch safeguards
continue to apply.

## Problem and decision

The current graph editor can recover drafts but deliberately refuses confirming
or applying structural changes after production installation. Bridge preparation
also refuses a second installation. The Revise round therefore cannot complete
by removing a button lock or using a cloned project. The owner selected one current
story and explicit rebuild, rather than a separate next-version workflow.

- Keep one current source-bound graph and one current canonical production in the
  same project. Saving a recoverable draft is not content admission. Confirmed
  source changes make dependent production outdated; applying the exact graph
  draft updates the sole current graph through existing source/CAS admission.
- Rebuild through the existing bridge preparation, whole-package dramatic-intent
  and presentation review, and explicit acceptance journey. Require current
  accepted source reviews. Preparation produces fresh pending reviews, not an
  automatically accepted copy of earlier intent or presentation decisions.
- Acceptance atomically appends canonical Bible, SceneBeats and Storyboard
  revisions plus an immutable bridge admission. Preserve project identity,
  authoring history, original receipts and managed media. No reset, clone, second
  version manager, historical-request replay or compatibility adapter is added.
- Freeze the exact replacement target: proposal-head CAS, installed admission
  identity and current canonical replacement revisions/hashes. Bind that target
  into the proposal hash; acceptance rechecks it under the write transaction.
  Concurrent edits cannot be overwritten by an older rebuild.
- Read latest proposal state separately from installed-production authority.
  Installed identity/currentness comes from the latest immutable admission, its
  own frozen source inputs and exact canonical heads. Preparing another proposal
  cannot make old production current, erase its identity or borrow its runtime
  choices for the new proposal.
- Revalidate a Bible-dependent source graph against a proposed replacement Bible
  within the same bundle transaction. Record fresh source-owned admission when
  rebinding is required; never edit old provenance or merely update a head's input
  revisions. Incompatible entity effects fail without partial installation.
- Separate the authored graph identity from its canonical Bible-dependency binding.
  Today F2–F5 bind the canonical graph revision; a dependency-only graph revision
  during rebuild would immediately stale those accepted inputs. Normal explicit
  graph application establishes both identities. A trusted source-owned Bible-only
  rebind preserves the authored revision/hash, appends fresh canonical dependency
  provenance and records the exact new canonical identity. Source reviews bind
  the authored identity and still require a READY canonical head matching that
  admission and payload hash. Arbitrary same-hash canonical writes cannot satisfy
  it. Any current-data schema cutover initializes authored identity from its exact
  source-owned admission; no runtime old/new reader or rewritten historic receipts.
- Current media source timing uses the latest installed admission only. A removed
  or reused shot ID cannot recover authority from a historical admission. Retained
  evidence preview remains a separately verified read, not production admission.
- Rebuilding requires fresh Storyboard approval and current explicit presentation,
  reference/keyframe and video decisions where their existing bindings changed.
  Claim stage-level rebuild, not selective frozen-video reuse. Preserved assets
  may be considered through existing explicit review/selection contracts; stable
  IDs alone are not proof of unchanged meaning or valid media.
- Withdraw story playback while affected production is outdated or its current
  read is unknown/failed. Resume only after explicit rebuild, fresh review and
  current selected clips cover the complete route. Old bytes remain previewable
  where the immutable-evidence contract permits them.
- Preserve busy/quiescence refusal and unresolved queued, dispatched or
  outcome-unknown jobs. Never clear reservations or resend uncertain requests to
  enable replacement.

## Alternatives and guardrails

### Typed entry-state projection and persistence identity

The rebuild implementation probe found that bridge projection emitted empty
SceneState values even when the exact admitted graph assigned typed direct-edge
entity states. Canonical coverage correctly refused the first target scene.
Trusted projection now uses the existing `edge_entity_entry_states.v1` compiler:
only unanimously assigned direct-edge states become target scene/beat/shot
entry and unchanged exit facts. It invents no authored state changes, path
variants or inferred semantic intent. Partial or conflicting converging inputs
refuse at graph/entry-contract validation; proposed Bible incompatibility still
fails before any bundle revision is committed.

An append-only `v2_source_graph_identities` table binds each source-owned canonical
entity revision to its authored revision/hash and exact source/outline/map
admission. Explicit graph Apply writes a new authored identity; trusted dependency
rebind appends a canonical identity with the original authored identity. Arbitrary
same-hash canonical writes have no identity and cannot authorize F2–F5. This is a
breaking current-schema requirement. Exact schema classification rejects prior
folders before ordinary open; there is no reader fallback or automatic backfill.
Any disposable cutover is a separate exact operation, not implemented here.

The bridge response has required `installation` and `preparation` fields;
installation includes its own frozen inputs, cuts, scenes and runtime choices.
Duplicated flat installation/currentness fields retire. Proposal preparation
requires the server-proved typed body, including proposal CAS, source-input hash
and the exact canonical replacement target. Intent/presentation revisions retain
that target unchanged in their proposal hash.

Rejected: retaining an independently playable old story while editing a second
version; deleting/resetting production to get through empty-head guards; changing
frozen jobs to match new content; weakening graph effects or copying approvals.
Use current contracts and explicit development cutovers, not old/new adapters.

Regression coverage must prove same-project current → outdated → reviewed rebuild
→ fresh approval → all revised routes playable; independent proposal/installation
reads; stale target/CAS rejection; late inference containment; busy refusal;
rollback after a late bundle failure; compatible/incompatible Bible effects;
dependency-only rebinding retaining current F2–F5 source authorization while an
explicit authored graph change invalidates it; removed/reused shot identity;
retained assets and restart. Unit and software gates
do not establish this native journey. The existing Create → Revise → Recover
playbook and dated run ledger own executed acceptance and remaining gaps.
