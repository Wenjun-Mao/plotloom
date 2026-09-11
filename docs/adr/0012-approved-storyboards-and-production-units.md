# ADR 0012: Approved storyboards and derived production units

## Context

Plotloom correctly separates story nodes, dramatic scenes, beats, shots, and
media tasks, but the current production boundary is incomplete. A Shot carries
free-form `dialogue` and `audio` strings; Dramatic Scene order and timeline
semantics are implicit; storyboard validation does not yet prove adjacent-state
continuity, dialogue fit, or asset-state consistency; and a media task can be
created directly from a storyboard revision without a recorded human approval.

Narrative Forge demonstrates the value of a short loop from a selected shot to
reference media, generation, and preview, but its mutable scene-shaped records
are not an acceptable canonical model. shuohao-skills demonstrates useful
segment/cut/frame, timing, dialogue, sound, reference, and export disciplines,
but its positional identities, linear-episode assumptions, and provider-specific
prompt packages must not become Plotloom's interactive story model.

The root problem belongs between canonical authoring and provider execution. If
the browser or each media adapter independently invents this layer, production
semantics will drift and later providers will force migrations of authored story
data.

## Decision

### Canonical authoring semantics

Plotloom will extend, rather than replace, its four canonical stages:

- Dramatic scenes have stable order within their story node and an authored or
  derived duration budget.
- Dialogue is represented by stable `DialogueCue` records owned by a beat. A cue
  identifies its beat, ordered position, `speakerId` or explicit voice-over,
  text, language, and performance delivery. Shots schedule or reference cue IDs;
  they do not duplicate the authoritative line as an unrelated string.
- Shot sound uses a structured `AudioPlan` that distinguishes ambience, sound
  effects, diegetic sound or music, and non-diegetic score.
- Character, location, and prop specifications can declare visual/voice anchors,
  permitted lighting or object states, scale, and continuity rules. Shots name
  the required entity states; they do not name provider reference-image slots.
- Ordered shot durations deterministically derive scene, node, and selected-path
  timecodes. Dialogue-fit validation uses a versioned language/delivery timing
  profile rather than one hard-coded characters-per-second constant.

Storyboard gates validate contiguous order, exactly one primary beat owner with
optional supporting coverage, adjacent entry/exit state compatibility, dialogue
ownership and fit, asset-state availability, and deterministic timing. Each
result is a structured `GateResult` with stable ID, severity, status
(`pass`, `fail`, `skipped`, or `not_applicable`), entity path, evidence, and
reason. A skipped required gate never counts as passing.

### Approval

An `Approval` is an immutable decision over an exact subject revision and
content hash. It records project, subject type and ID, decision, reviewer,
timestamp, optional note, and the gate-set version considered. Saving or
successfully generating content does not approve it.

Historical approvals remain auditable. An approval is active only while the
subject revision, its canonical input revisions, and required gate results still
match. Editing an upstream stage or the approved storyboard makes the approval
stale; it never transfers to the new head. Revocation is a new decision, not
deletion of history.

The one-click text pipeline from ADR 0004 remains allowed: it may atomically
install all four valid stages as reviewable drafts. Approval is mandatory when
crossing from authored storyboard into production or media. A project policy may
add intermediate review stops, but Plotloom does not globally require approval
between every text stage.

### Derived production units

**2026-09-11 amendment — non-generative P0:**
[ADR 0026](0026-story-to-playable-product-direction.md) permits controlled
import/exploration without storyboard Approval and separately permits reviewed
still-preview bindings/projections before provider production is implemented.
The latter requires exact active Approval, reviewed selections, immutable asset
hashes and coherent revision-frozen inputs. It is not a MediaTask or a complete
ProductionSnapshot. This narrowly qualifies the blanket media boundary above;
all provider production requirements below remain unchanged. P0 does not
authorize exploratory provider generation or raw-Shot submission.

A `ProductionUnit` is a versioned, content-addressed projection of one approved
storyboard snapshot. It is not a fifth canonical story stage and is never edited
to change narrative truth. A unit contains:

- approval ID and exact storyboard/entity revision references;
- one or more ordered shots from one continuous production context;
- authored and delivery duration, cut boundaries, and derived frame plan;
- scheduled Dialogue Cue and Audio Plan references;
- a provider-neutral `ShotReferencePlan` resolved from required character,
  location, prop, and style asset roles; and
- planner/compiler version, inputs, warnings, and content hash.

For a single-shot provider, one unit may contain one shot. A multi-shot video
adapter may consume a bounded sequence and derive segment/cut/frame requests.
One unit never crosses a dramatic-scene boundary; its shot membership is ordered,
contiguous, non-empty, and non-overlapping with other units in the same projection.
Provider duration, frame-count, vocabulary, or reference-slot restrictions are
adapter capabilities applied while compiling the production unit. They do not
mutate canonical Shot data. Provider-specific prompts and request payloads are
versioned artifacts derived by a deterministic compiler, not fields written back
into the storyboard.

Changing a canonical input makes later units and tasks stale but preserves their
history and artifacts. Rebuilding creates new units. A media task may reference
only an active approval, an exact production-unit revision, and validated local
reference artifacts. Missing required references block that media submission but
do not invalidate the text storyboard itself.

At media enqueue, Plotloom resolves the unit, canonical revisions, approvals,
Dialogue Cues, Audio Plan, reference requirements, and selected artifact hashes
into an immutable `ProductionSnapshot`. That snapshot—not `shotId`, the current
storyboard head, or a remote URL—is the authoritative task input. Shot and
storyboard identifiers may remain denormalized read fields for navigation.
Clients cannot supply `sourceUri`, `imageUrl`, reference-image URLs, or other
arbitrary media inputs through public provider settings. An adapter may upload a
validated local artifact and derive a short-lived provider URL only after the
snapshot is frozen.

Asset roles include, at minimum, character master/reference, location and
lighting state, prop and prop state, style reference, shot keyframe, generated
video, and explicitly imported user media. Every bound artifact records hash,
MIME, observed dimensions or duration where relevant, origin, license/provenance
metadata, and the revision that selected it. Arbitrary server paths and temporary
remote URLs are not durable asset identities.

A generated image or video is a candidate artifact. It does not automatically
become the newest approved keyframe or a later video's reference. Selecting it
creates a revisioned reference decision and requires the applicable approval;
history is preserved when another candidate is selected later.

The media workflow supports progressive approval: generate a small reference or
first production unit, review and lock the style/reference decision, then permit
larger batches. Batch generation and final editing remain later capabilities;
this decision defines their prerequisite boundary.

## Rejected alternatives

- Treating Save, valid model output, or media submission as human approval.
- Requiring approval between every text stage and thereby breaking the one-click
  draft pipeline.
- Copying dialogue into Beat, Shot, provider prompt, and dubbing sheets as four
  independent authorities.
- Making linear segment numbers, cut ranges, or frame positions stable domain IDs.
- Storing a provider's long-form prompt or reference-slot layout as canonical
  Storyboard data.
- Creating new media tasks directly from a raw Shot or client-supplied source URL
  without an approved Production Snapshot and locally verified references.
- Allowing invalid or unapproved boards to produce a package merely marked with
  missing assets.
- Replacing Plotloom's stable many-to-many `ShotBeatLink` model with positional
  beat ranges or exact-once coverage for every supporting link.

## Consequences and guardrails

Implementing this decision requires domain and persistence migrations, prompt
schema revisions, validators, approval APIs/UI, production planners, and media
task changes. Old storyboard revisions remain readable through explicit schema
version handling; migrations must not invent speakers, approvals, or asset states
from ambiguous free-form text.

ADR 0004 remains authoritative for canonical revisions and stage staleness, and
ADR 0006 remains authoritative for task lifecycle, adapters, secrets, and restart
reconciliation. After this contract is implemented, ADR 0006's production input
is narrowed from a raw frozen Shot to an approved `ProductionSnapshot`. Existing
legacy media tasks remain historical and receive no fabricated approval.

Tests must cover approval creation, revocation, and staleness; one-click draft
generation without intermediate approval; structured dialogue ownership and
timing; audio categories; scene/path timecode derivation; primary/supporting
coverage; continuity and asset-state failures; deterministic production-unit and
provider-compiler hashes; adapter capability refusal without canonical mutation;
reference-artifact lineage; and rejection of media work from unapproved, stale,
invalid, or incomplete inputs. Subjective quality remains a versioned human
review rubric tied to the same snapshot, not a unit-test assertion or model
self-score.
