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
revision/hash-protected acceptance. F5 remains raw review evidence; the bridge
does not run a model, create an upstream-style shot store, select references,
approve a storyboard, or submit media.

The proposal maps each F5 cut to one canonical shot, not to one H3 job or one
source segment, and maps each F4 scene occurrence to exactly one canonical
dramatic scene. It preserves source-cut coordinates and exact milliseconds,
treats F5 H3 text as review evidence rather than a provider prompt, and
refuses an unsupported exact source duration at video preparation without
conversion. A count outside the frozen Brief's editable shot-range policy is a
visible blocking proposal conflict, not authorization to invent dramatic
segmentation or silently alter the Brief.

F2 consumer mappings provide canonical character IDs only after V2 ID
validation; F3 is evidence and explicit entity mapping, never image selection.
The first install targets empty Bible/SceneBeatPlan/Storyboard heads only.

Canonical invalidation must follow recorded input revisions and upstream
readiness rather than stage order alone. This keeps a source-map graph that has
no Bible input current across the bridge Bible install, while normally authored
or transitively dependent stages continue to stale. The bridge records the
retained graph revision/hash with its three installed canonical revisions.

### Reviewed source-excerpt supplement

F1--F5 do not own the semantic `DramaticScene.objective` or `Beat.purpose`
fields required by V2. This slice therefore exposes one distinct, reviewable
source-excerpt supplement within the production proposal. It is not a semantic
suggestion or inference and is never represented as a frozen F1--F5 fact. Each
entry records its exact accepted source coordinates and raw-content hash, the
frozen F1--F5/Brief input binding, its seed method, the source text, and the
author-edited text.

The only existing model transport is the versioned Scene Beats work-unit path
(`generation/work_units.py` → `scene_beats.fragment.v13` → aggregate canonical
`SceneBeatPlanV2`). Its input/output schema and binder install a canonical
stage; they have no response shape, provenance binding, or persistence target
for a source-bound bridge supplement. This slice consequently uses only
deterministic `source_excerpt_seed.v1` text from the relevant F1 summary or F4
flow entry. It makes no model call. The author may edit all entries as one
proposal package, then explicitly accept its exact saved revision and hash. A
later package edit, or a change to any frozen upstream/Brief input, creates a
new non-accepted binding and prevents installation under the prior review.
The client must treat an edited package as dirty: it preserves that draft across
same-proposal refreshes and disables acceptance until the server acknowledges a
new proposal revision/hash for the displayed text.

Trusted code owns coordinate resolution, immutable provenance, proposal
hashing/currentness, canonical validation, and atomic empty-head/CAS
installation. The author owns the final objective/purpose wording and the
explicit package acceptance. The model owns nothing in this slice. A semantic,
model-backed suggestion needs separately authorized work: a bridge-specific
prompt and response schema, immutable input/output provenance, an admission
owner that creates only a bridge revision, and review semantics. Reusing the
canonical Scene Beats transport is explicitly unsupported.

## Consequences

The implementation needs typed proposal/admission persistence, a single
Chinese source-excerpt package editor/review (not a per-field wizard),
deterministic source-preserving projection tests, input-provenance invalidation
tests, a usable Chinese proposal review with explicit acceptance controls,
atomic installation, and a narrow bridge-aware duration guard at video
preparation.
It does not migrate existing canonical projects, replay or rewrite F4/F5
history, add a compatibility layer, or change provider capabilities. Existing
canonical review, reference, keyframe, media, and playback owners remain the
next explicit workflow steps.

The detailed mapping, acceptance sequence, exclusions, and test scope are in
[the bridge design](../verification/2026-09-22-f5-to-production-canonical-bridge-design.md).
