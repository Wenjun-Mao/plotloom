# ADR 0218: Working input autosave and optional Freeze

Status: accepted for implementation, 2026-10-24. Implements the owner-approved
[retained plan](../roadmap/2026-10-24-autosave-and-project-freeze.md).

## Problem and evidence

Project creation requires `ProjectBrief`; draft validation also invokes that
canonical model. Review buffers persist locally but their update method does not
schedule a server write. Navigation flushes only its active legacy scope. Folder
Close denies reads and writes. Thus hiding Close loses durability, while calling
canonical Save from autosave would adopt content and invalidate production.

## Decision

Use the existing `v2_authoring_drafts` CAS authority, scoped by project, editor,
entity and canonical/source basis. Bounded author-input models allow incomplete
text and raw numeric strings; canonical models remain strict at explicit Apply /
Confirm. Keep the single shared graph owner and exact draft-consumption checks.
The browser journal uses persistent local storage, with independent client-owned
entries and verified writes; session identity is not project authorization.
Receipts never erase newer input. A lost receipt is reconciled only against the
exact expected revision and payload; competing content remains a conflict.

A newly reserved project has `brief = null` until explicit Brief Apply. The JSON
column already represents JSON null: no SQL layout or existing-row migration is
needed. No invented synopsis or canonical defaults are installed. The API exposes
the working display title separately. Generation/canonical operations require a
confirmed Brief. New uses existing creation reservations with a stable intent key;
teaching preview has no persistent identity and editable-copy is explicit.

Persisted operational `closed` maps to product Frozen. Keep this private enum and
exclusive/quiescent transition: a vocabulary-only storage migration is needless.
Frozen reads use genuine query-only admission, with no reconciliation or resume;
write/dispatch admission remains refused. Unfreeze restores admission only.
Archive, snapshots, deletion and UNKNOWN ownership retain their separate guards.

This supersedes Close/save-close/force-exit semantics in ADRs 0043 and 0113,
save-before-leave parts of 0087/0115 and manual matching restoration in 0113/0116.
ADR 0129’s read-only versus save-progress distinction remains in force.
Navigation preserves working input without adopting it. Apply/Confirm and
production consumption remain deliberate semantic decisions.

## Preservation and rollback boundary

Existing rows and SQL schema are unchanged merely by installing this code. After
a draft-only project or extended working payload is written, an older binary is
not qualified as a workflow-compatible rollback. The fixture proves that the old
reader refuses a null-Brief home. It can open/read the extended raw draft, but its
old canonical draft validator refuses that payload; read-open refusal is not
claimed for this second case. Preserve the qualified source/static package as the readable fallback
and use forward repair; never delete new drafts or rewrite canonical history to
make an old binary start. Fixture proof must cover prior-reader refusal, current
reader recovery and unchanged pre-existing rows before activation. No automatic
backup, general legacy reader or reset is introduced.

## Alternatives and consequences

Rejected: generic browser dumps, canonical schema relaxation, automatic Save,
last-write-wins, secret Unfreeze on GET, and a second graph autosaver. These lose
domain ownership, approvals or preservation guarantees. Local journaling is
bounded working-input recovery, not offline generation or cross-device sync.
Consent, explicit acknowledgements, restored reviewer/operator attribution and pending File authorization are excluded;
unsaved File selections require a departure guard. Tests must exercise creation,
incomplete input, exact receipts, conflicts, restart, scoped erasure, truthful
status, frozen read/write separation and unchanged production/provider counts.

## Exact recovery and independent scratch input

Journal ownership uses both a session lineage and a per-document token, so cloned
session IDs cannot overwrite one another. Every foreign/legacy namespace retains
its exact entity key and serialized revision for inspect/copy/scoped discard.
Current entries never hide other namespaces. Exact durable payload/basis/receipt
matches retire redundant journals and auto-resume; disagreement never rebases.
Reconnect retains admitted writers after their editor unmounts. Status and unload
protection follow the current project and actual journal readback, including a
first quota failure. Known stale editors are disabled; a raced rejected update
retains its exact visible text for copy and blocks departure, rather than claiming
that an old journal preserves the new input.

`brief_custom` alone is dependency-free scratch text: fixed `brief-custom:v1`
basis, one known direction-group target, 120-character limit and base revision 0.
Enter/+ explicitly adds a selected direction. An unrelated Brief Apply cannot
erase this text or turn it into a selection. Other review buffers retain their
ordinary canonical revision plus proposal/section/candidate/source basis.

Explicit Brief adoption validates the exact selected working receipt, converts
raw numeric strings and supplies the documented optional-title fallback only at
Apply. No confirmed Brief exists before that action. Cleanup compares exact
payload/base/receipt/local lineage, because local counters can restart after an
acknowledgement; a delayed A receipt cannot retire B's reused counter.

## Restored authority-read admission

Portable payloads exclude operational lock debris. Restore now initializes and
syncs the ordinary operation lock before publishing a home. Authority reads
require that real shared OS lease; a missing lock is refused without read-time
repair. Passive inspection remains noncreating. This amends the historical
restored-CLOSED omission behavior while preserving existing lock interoperability,
query-only reads and exclusive deletion/Unfreeze exclusion across processes.

## Owner decisions and regression map

The owner explicitly approved implementation through RelayDirect and answered all
five choices in the [retained plan](../roadmap/2026-10-24-autosave-and-project-freeze.md#outcome-and-owner-decisions): matching edits resume automatically; New persists an unnamed draft before a valid Brief; the built-in teaching preview is read-only with explicit editable-copy; frozen projects browse/play read-only; autosave preserves working input while confirmed production updates require explicit Apply/Confirm. New is an explicit creation intent, so it accepts unused drafts to preserve input before validation. Preview alone is not creation intent, so teaching does not clutter the catalog. Read-only Frozen browsing supports review without edit admission. Matching auto-resume avoids routine Restore prompts. Explicit Apply keeps typing from invalidating production. These choices supersede the earlier vocabulary-only Close rename. This record preserves the decision and its reasons rather than reproducing the chat.

Idle never automatically freezes a project. Ordinary departure preserves input
and already-admitted background work continues under its existing authority.
Freeze checks busy/UNKNOWN ownership authoritatively and refuses when unsafe; it
does not cancel work, clear uncertainty or queue a later freeze. No approval,
reviewer attribution, explicit consent, credential or paid-operation authority is
restored from a working journal.

| Decision / rejected alternative | Durable boundary and regression |
| --- | --- |
| Automatic preservation / explicit Apply; no Save-on-leave or Close workflow | [Incomplete A/B fresh-browser journey](../../frontend/e2e/working-project-autosave.spec.ts), [Home and background ownership](../../frontend/e2e/project-save-force-close.spec.ts), [exact raw adoption](../../tests/test_working_project_autosave.py) |
| Immediate identity / no fake canonical Brief; read-only teaching / explicit copy | [Creation/idempotency tests](../../frontend/tests/app-state-save.test.ts), [lost New reply and teaching-copy journey](../../frontend/e2e/first-save.spec.ts) |
| Matching auto-resume / no blind restoration or last-write-wins | [Addressable namespaces, cloned clients, exact receipts and frozen refusal](../../frontend/tests/working-input-journal.test.ts), [real competing-journal copy/discard](../../frontend/e2e/draft-recovery-presentation.spec.ts) |
| Optional Freeze / no idle freeze, hidden Unfreeze, resume or dispatch on read | [Freeze/preview browser proof](../../frontend/e2e/project-folder-close.spec.ts), [real frozen ready playback](../../frontend/e2e/video-batch.spec.ts), [native pure query](../../tests/test_native_bridge_intent.py), [batch query/write refusal](../../tests/test_video_batch_review.py), [reason-specific guidance](../../frontend/tests/recommended-workflow.test.ts), [teaching/Frozen/archive UI guidance without writes](../../frontend/e2e/project-folder-close.spec.ts) |
| Entity/source ownership and newer-input protection / no generic project dump | [Candidate A/B and current-project unload](../../frontend/tests/review-delta-contracts.test.ts), [delayed Apply A/new B lineage](../../frontend/tests/app-state-navigation.test.ts), [per-section/CAS/reconnect](../../frontend/tests/working-input-journal.test.ts) |
| Failed preservation remains visible / no stale success or automatic conflict rebase | [First quota failure for both media owners](../../frontend/tests/visual-intent-drafts.test.ts), [stale H3 edit/race/departure guard](../../frontend/tests/h3-directions-review.test.ts) |
| Notes resume, authority stays fresh / no restored review judgment, attribution or File upload | [Material text projection](../../frontend/tests/bulk-material-review.test.ts), [fresh reviewer](../../frontend/tests/media-workbench-failed-refresh.test.ts), [pending-File subject departure](../../frontend/tests/character-reference-gallery.test.ts) |
| Narrow dependency-free scratch / no general review rebase | [`brief_custom` bounds and survival through Brief Apply](../../tests/test_working_project_autosave.py) |
| Pure read plus real exclusion / no lock creation or lease-free authority during GET | [Frozen snapshot/direct-folder restore and cross-process shared read](../../tests/test_project_storage_recovery.py) |
| Honest compatibility boundary / no erasing new drafts for old code | [Prior-reader/validator refusal and exact current recovery](../../tests/test_working_project_rollback.py) |

Qualification receipts distinguish focused evidence, the final unfiltered local
gate, installed runtime activation and owner creative acceptance. Historical ADRs
and receipts remain unchanged records of their original behavior.

Branch state and draft projection use read leases throughout their basis lookups. Creation owns head initialization; querying never repairs a missing source or section-map head. A missing required basis is refused without changing rows, while a new project with no candidate may project its planned topology without inventing accepted content.

Ordinary preservation is separate from exclusive drainage. The branch-operation owner may declare its already-owned sent request preserved for departure because it owns no editable buffer; navigation does not cancel or replay it. Freeze, snapshot and deletion still join that exact request and refuse uncertain completion. Other writers retain their journal/flush obligations. The held-flight regression in [branch-operation-owner.test.ts](../../frontend/tests/branch-operation-owner.test.ts) and [branch-mutation-remount.spec.ts](../../frontend/e2e/branch-mutation-remount.spec.ts) binds this exception. Ordinary departure proves both captured and currently registered owners: an exact flush receipt or current durable/local preservation can tolerate harmless hydration/registration churn. A successful old receipt cannot cover newer unpreserved input, and an unknown late owner, rejected input or pending File still refuses departure. Registration revision equality remains an exclusive drain/commit requirement. Busy work with no File is operation authority rather than unsaved author input, so it does not claim input loss or leave a ghost input guard after unmount; authoritative Freeze still refuses the admitted operation. An actual File remains held by its exact project/cast-session owner until import or explicit discard, and old callbacks cannot alter a newer session. [Ordinary proof and late-owner tests](../../frontend/tests/project-draft-quiescence.test.ts), [File guard lifetime](../../frontend/tests/explicit-review-close-guard.test.ts), and [held preparation/native import browser journeys](../../frontend/e2e/cast-reference-studies.spec.ts) protect these distinctions.

Project-management display and deletion consent use the autosaved working title plus the exact deletion scope, independently of production Brief Apply. Forcing canonical Apply to make deletion consent agree would accept creative content as a side effect of project management. The current raw abandonment reader shares the pure title projection in its existing query snapshot and binds it in its current preview digest; the one supported prior-layout digest remains unchanged. [Deletion preparation](../../tests/test_project_deletion_preparation.py) verifies stale title and changed-away/back scope refusal without row/file changes, ledger acknowledgement or host revocation, followed by fresh scoped consent matching the visible working title.

Read validation depth and operational admission are separate obligations. Explicit media/project metadata inspection retains ADR 0192's requested-byte/hash/schema contract instead of validating unrelated authority domains; both it and default strict authority reads require an initialized shared OS lease before database opening and reject acknowledged deletion quarantine. [Inspection admission](../../tests/test_project_inspection_admission.py) binds damaged unrelated authority, open/Frozen byte reads, strict authority refusal, pre-open missing-lock refusal, exclusive exclusion and exact query purity; [deletion quarantine](../../tests/test_project_deletion_quarantine.py) checks both modes.

The current raw abandonment reader validates only the existing title field shapes before projection: whole Brief JSON null is allowed, otherwise canonical title is a string of1..200 characters; a present working row requires a string of0..200. Nonstring/empty canonical fields do not become an unnamed project through falsey fallback. Whitespace string display rules remain unchanged. This does not newly validate unrelated Brief fields or alter the prior-layout reader; the raw refusal matrix in deletion preparation checks both boundaries before host calls.


Recovery availability belongs to the current loaded input owner. A retained-only
warning is not authority to recover an entry that has not hydrated. Explicit
image-direction context recovery requires the exact current entry, a ready
conflict-free server receipt and current editing/write admission; captured
callbacks cannot recover after busy/read-only, target or lifecycle changes.
Foreign namespaces keep their separate inspect/copy/discard and exact matching
resume contract. This prevents an enabled recovery action from silently doing
nothing and prevents restoration from becoming an editing bypass. The
[held real draft-read journey](../../frontend/e2e/image-jobs.spec.ts) and
[recovery/captured-callback guards](../../frontend/tests/visual-intent-drafts.test.ts)
map this boundary to executable regressions.
