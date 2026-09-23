# ADR 0079: F5 production canonical bridge

Status: Accepted for scoped implementation, 2026-09-22. Product and creative
acceptance remain separate.

## Context

F5A persists an accepted, source-bound upstream storyboard as review evidence.
Current image, video, and playback owners consume the separate canonical V2
Bible, graph, SceneBeatPlan, and Storyboard. U4 proves coherent F1–F5 reading,
not a production projection. In the retained pilot, one F4 scene occurrence
has nine F5 cuts while the current editable Brief planning policy permits two
to four shots per canonical scene.

## Decision

Add a dedicated F5 production-bridge proposal/acceptance owner. It deterministically
freezes accepted F1–F5 plus the project brief, builds a reviewable V2 canonical
proposal with source provenance, and installs it only after an explicit
revision/hash-protected acceptance. A separate, optional bridge-intent job may
infer provisional semantic wording from that frozen evidence; it never installs
anything. F5 remains raw review evidence; the bridge does not create an
upstream-style shot store, select references, approve a storyboard, or submit
media.

The proposal maps each F5 cut to one canonical shot, not to one H3 job or one
source segment, and maps each F4 scene occurrence to exactly one canonical
dramatic scene. It preserves source-cut coordinates and exact milliseconds,
treats F5 H3 text as review evidence rather than a provider prompt, and
refuses an unsupported exact source duration at video preparation without
conversion. A count outside the frozen Brief's editable shot-range policy is a
visible blocking proposal conflict, not authorization to invent dramatic
segmentation or silently alter the Brief.

ADR 0080 supersedes only the *strictness* of that conflict: legacy Briefs
remain strict, while an explicitly advisory Brief presents the exceedance as
nonblocking review evidence. Source mapping and explicit acceptance are
unchanged.

F2 consumer mappings provide canonical character IDs only after V2 ID
validation; F3 is evidence and explicit entity mapping, never image selection.
The first install targets empty Bible/SceneBeatPlan/Storyboard heads only.

Canonical invalidation must follow recorded input revisions and upstream
readiness rather than stage order alone. This keeps a source-map graph that has
no Bible input current across the bridge Bible install, while normally authored
or transitively dependent stages continue to stale. The bridge records the
retained graph revision/hash with its three installed canonical revisions.

### Reviewed dramatic-intent supplement

F1--F5 do not own the semantic `DramaticScene.objective` or `Beat.purpose`
fields required by V2. The production proposal contains one distinct,
reviewable dramatic-intent supplement, never represented as a frozen F1--F5
fact. Each entry records its exact accepted source coordinates and raw-content
hash, the frozen F1--F5/Brief input binding, the suggestion method, source
excerpt, and author-reviewable text.

The canonical Scene Beats work-unit path cannot own bridge suggestions: its
binder installs a canonical stage. The generic text profile, prompt renderer,
adapter, and response-extraction boundaries *can* transport a bridge-specific
inference without a new provider or credential system. The bridge owns a
separate, durable one-attempt job and review admission; it must retain
request-not-sent versus outcome-unknown dispatch states, never blindly retry
an ambiguous provider call, and cannot install canonical data from a worker.

The deterministic F1/F4 excerpts remain source evidence, not completed
semantic `objective`/`purpose` values. An initially prepared proposal is not
installable until the whole package has either model-inferred suggestions or
explicit author wording. A versioned bridge prompt may ask only for semantic
`suggestedText` keyed by a trusted exact target-ID set. The model cannot create
IDs, coordinates, content hashes, canonical payloads, source bindings, or
acceptance. Trusted code freezes F1--F5/Brief, proposal revision/hash, public
profile, prompt/schema and response provenance; validates exactly one nonblank
suggestion per target; binds the package; and creates only a new reviewable
proposal revision if all frozen inputs and the head are still current. Late
results after edits, cancellation, restart uncertainty, or source changes are
not admitted. The author may edit all entries as one proposal package, then
explicitly accept its exact saved revision and hash. A
later package edit, or a change to any frozen upstream/Brief input, creates a
new non-accepted binding and prevents installation under the prior review.
The client must treat an edited package as dirty: it preserves that draft across
same-proposal refreshes and disables acceptance until the server acknowledges a
new proposal revision/hash for the displayed text.

Trusted code owns coordinate resolution, immutable provenance, proposal
hashing/currentness, exact-output validation, canonical validation, and atomic
empty-head/CAS installation. The model owns only provisional semantic
suggestions. The author owns final objective/purpose wording and explicit
package acceptance, including when accepting an unchanged suggestion. No
provider response or source excerpt becomes an accepted dramatic intent merely
by existing. Reusing the canonical Scene Beats work-unit binder remains
unsupported.

The persisted supplement keeps three distinct texts: immutable accepted-source
`sourceExcerpt` (bound to `sourceCoordinates` and `sourceContentHash`), optional
model `suggestedText`, and reviewable/final `text`. Package `suggestionOrigin`
identifies whether a model supplied a suggestion; `reviewState` independently
records pending, model-suggested, or author-saved wording. Saving an author edit
must not change model origin, its original suggestion, or its provenance. A new
inference must use `sourceExcerpt`, never a previous `suggestedText`, as source
evidence. The one retained pre-correction accepted local fixture is projected
read-only from its original proposal revision and model job provenance; its
historical rows and accepted binding are not rewritten to claim the new shape.
Development-only fake previews carry a server-owned simulation notice in the
bridge response. The UI must not infer that notice from a removable URL flag,
and normal project responses carry no such notice.

### Canonical shot handoff and preparation visibility

An accepted bridge may link each installed proposal cut to its exact canonical
Storyboard shot through the existing shot route. The link is available only
while the bridge and installed Storyboard revision are current. An unknown or
no-longer-owned shot ID must fail visibly rather than fall back to another
shot; unsaved source work must retain the existing navigation guard.
The bridge's accepted-source status does not become stale merely because a
downstream Storyboard was edited. Its read-only `installedStoryboardCurrent`
projection compares the installed revision with the current ready Storyboard
head; both the link and the shot summary fail closed on a mismatch.

The shot workbench may display a read-only preparation summary from the
existing bridge, Storyboard approval, visual-workbench decisions, and video
backend owners. It creates no new approval, selection, job, or readiness
verdict. A media-owner read is current only after all its owners succeed for
the same project and approval context; loading or failure suspends media
mutations, exported-job polling, and durable media-draft writers while
retaining session drafts for retry. The disabled video-backend response still
exposes the qualified request-duration catalog so the UI can distinguish an
unconfigured backend from an exact source duration outside that catalog.
Catalog compatibility is not physical output-duration equality. The deployed
gateway's frame-grid function computes 124, 158, and 192 requested frames at
24 fps for nominal 5, 6, and 8 seconds respectively. Retained real 5/8-second
canaries confirm those actual outputs, but no 6-second clip has been generated
or measured.
Therefore adding a nominal 6-second request to the catalog alone cannot
prove satisfaction of the exact 6-second F5 source contract. Duration
reconciliation needs a separate policy and physical evidence before media
preparation changes.

## Consequences

The implementation needs a versioned bridge prompt and strict whole-package
binder, durable source-bound job/attempt lifecycle, typed proposal/admission
persistence, a single Chinese dramatic-intent editor/review (not a per-field
wizard), deterministic source-preserving projection tests, input-provenance
invalidation tests, explicit acceptance controls, atomic installation, and a
narrow bridge-aware duration guard at video preparation.
It does not migrate existing canonical projects, replay or rewrite F4/F5
history, add a compatibility layer, or change provider capabilities. Existing
canonical review, reference, keyframe, media, and playback owners remain the
next explicit workflow steps.

The detailed mapping, acceptance sequence, exclusions, and test scope are in
[the bridge design](../verification/2026-09-22-f5-to-production-canonical-bridge-design.md).
