# ADR 0107: Reviewed shot production presentation amendments

Status: accepted for the 2026-10-03 E2E-first continuation.

## Problem

Accepted source requires phone-screen text and typing completion. The author now
permits a complete unsent popped-out draft preview and a separate send shot.
English H3 translation and asset VisualIntent cannot amend physical authority;
changing the global storyboard would invalidate six unrelated selected clips.

## Decision

Keep accepted canonical and bridge evidence unchanged. Append a source-bound,
author-reviewed production presentation decision per shot, with revision CAS and
an exact source hash. The author may amend physical presentation fields and must
explain the change. Exact message text is selected by trusted source pointer from
the current shot or its immediately preceding shot in the same scene; the API
does not accept invented literal text. Original text provenance is copied intact.

One shared projection supplies effective shot fields and beat visible events to
both image and H3 preparation. The complete unsent draft is present at frame zero;
draft review does not imply typing completion or sending. A send presentation
requires a deliberate send action and intelligible sent state. It is an authored
generated-media treatment, not a runtime compositor. Physical rendering and
actual media still require creator review; validators do not certify semantics.

For amended requests, image instructions exclude runtime branching-choice UI,
not the explicitly reviewed message preview or nonverbal interface cues. Exact
words still come only from frozen visibleTexts; no new replies or status words
are authorized implicitly. Retained unamended packages keep their original
instruction bytes so immutable delivery evidence remains recheckable.

Requests freeze the exact presentation decision. A later decision invalidates
only that shot's requests and bindings. Binding selection confirms the current
presentation revision; earlier bindings require explicit review again. Unchanged
shots and their frozen requests remain current. Presentation decisions do not
modify timing, identity, dialogue, canonical approval or playback selection rows.
Because selected visible literals are nonspoken, review refuses a literal that
also occurs in a canonical dialogue cue for the shot. The author must resolve
that canonical conflict first; the presentation layer never drops or silences
a cue. Unrelated dialogue remains unchanged. This refusal applies before an
amendment is stored and again during its source-currentness validation.

## Alternatives and consequences

Whole-storyboard rewriting unnecessarily invalidates unrelated media. Freeform
translation overrides hide a conflicting source contract. Asset-scoped intent
revisions can affect multiple shots sharing an image. A temporal typing engine
or compositor is not needed for the approved complete-first-frame treatment.

The additive table follows exact predecessor schema admission. Guardrails cover
source/CAS refusal, literal provenance, shared image/H3 projection, affected-shot
currentness and retention of unrelated selected clips. Old evidence is never
relabelled as satisfying the amended presentation.

Creator edits retain a narrow session buffer and block project Close while
unreviewed. Recovered buffers cannot borrow a newer source hash or decision
revision. Saving is explicit; Close never silently approves an amendment.

An unbound image is not necessarily historical: delivered job currentness owns
that distinction. Current unbound candidates await keyframe review; genuinely
stale delivered candidates retain the existing historical warning and refusal.
