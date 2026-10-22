# ADR 0189: Explicit cross-shot image use and scene-continuity references

## Status

Implemented in `901e6270`, with browser-fixture correction `cf689db9`, and locally
qualified on 2026-10-17 (Toronto). See the
[verification record](../verification/2026-10-17-cross-shot-image-use.md) for the
original failed full invocation and justified downstream evidence reuse. This
does not establish hosted CI, generated-content acceptance or autopilot authority.

## Context and cause

The manual walkthrough has an approved opening frame, but two independently
generated next-shot frames move scene objects/layout. Those jobs receive the
character portrait, not the actual preceding scene frame. Model nonadherence is
observed; a particular prompting mechanism is not proven. More text-only rerolls
are not the chosen correction.

The native source resolver correctly records the shot for which an image was
generated. Keyframe selection also uses that origin-shot check as target-use
admission, so an image generated for A cannot be explicitly reviewed for B.
Image preparation has identity, same-shot refinement and aspect-adaptation
reference roles, but no independent scene-continuity role. The missing concept
is an explicit target use, not missing provenance or permission to weaken it.

## Decision

Keep immutable asset/job/candidate/delivery origin, byte hashes and strict source
resolution. Introduce two explicit manual operations in the existing workbench:

1. **Reuse unchanged pixels as another shot's initial keyframe.** Choose one
   current reviewed same-project source frame. Save independent target-shot
   visual intent and compatibility review, then select a new target binding
   against the target's current storyboard approval/presentation. The source's
   approval, visual intent and identity review never become target approval.
2. **Generate a target image with one scene-continuity frame.** Choose one
   reviewed same-project frame from a different shot. Trusted code freezes its
   exact binding, intent, origin and original bytes into the target job and
   packages it as `scene_continuity`, separate from `character_identity` and
   `parent_output`. The target shot/presentation owns action, framing, lighting
   and current object states. The reference guides visible scene appearance;
   it cannot override target facts or promise model fidelity. Output is a new,
   still-unselected target candidate.

These are manual commands, not new machine/autopilot authority. Same-shot
refinement/adaptation and default machine/geometry source checks stay strict.
References cannot silently turn into refinement parents. Neither operation
creates a new service, provider or automatic adoption flow.

### Authority and persistence

- The author chooses opaque project-owned binding IDs and authors target review
  text. Trusted code resolves source identity, snapshots, hashes and applicability.
  Client paths/hashes, generic source-reference text and asset provenance cannot
  manufacture target-use authority. The model produces candidate pixels only.
- Use a named validated target-use value in the existing immutable VisualIntent
  JSON and existing reviewed-binding FK, rather than altering the owner project's
  exact SQL layout or rewriting historical records. Scope explicit target intent
  streams by target shot so saving B's intent cannot supersede A's intent.
- One shared binding-aware use resolver validates typed reuse. Ordinary source
  resolution remains strict; consumers must not invent caller-specific bypasses.
  Target selection, same-person review, preview, video, crop, delivery and folder
  validation must agree on that use and its frozen evidence.
- At creation, require a current eligible source binding and exact retained bytes.
  Later source reselection alone does not rewrite or invalidate an independently
  reviewed target use; changed required source authority/intent/bytes or target
  approval/presentation/identity must be handled consistently. Historical evidence
  validation remains distinct from current production eligibility. Reject forged,
  cross-project, self-referential or cyclic use, and verify reference bytes at
  package publication and delivery admission.
- If identical bytes fill distinct reference roles, retain each role/path and
  each native/Exec view obligation. `referenceUse.viewedReferenceHashes` remains
  the existing unique hash list (first-occurrence order); role-specific Exec
  reference-view receipts and ImageGen arguments remain ordered and complete.
  Content hashes may repeat in those ordered receipts/arguments; attachment
  identity is its confined package path and separately ordered view call/event,
  not globally unique pixel content.
- Every reused target frame needs its own target-current same-person judgment
  before video/preview where characters are visible. A's frozen character list
  or identity review cannot exempt B from review.
- Manual whole-project handoff discloses optional typed target use on its
  displayed frame, and revalidates that exact currently eligible binding under
  the writer lease. Authored input contains no trusted use evidence. Preserve
  unchanged existing intent records; changed B author fields receive a fresh
  B-stream intent with trusted code copying the displayed frozen target use.
  If the same handoff changes required source-A intent, refuse atomically and
  require fresh source/target workbench review. Never silently rebase B's
  evidence. Ordinary frame/bundle/receipt serialization remains unchanged.
- Editing a saved target use selects its opaque current target VisualIntent ID
  and unchanged opaque source-binding choice. Trusted code revalidates/copies
  that intent's source proof and frozen target approval/storyboard/presentation
  context, including before any target binding exists. Repeated unselected
  target saves therefore preserve the exact source after source reselection.
  A changed source choice freezes fresh current source authority. Neither
  caller-authored hashes nor generic gallery retention can manufacture reuse.
  Historical ordinary intents referenced by multiple shots are not independent
  target editor streams: editing requires an explicit typed target use first.
  A different typed target intent sharing the asset does not block ordinary
  source-shot editing; ownership compares exact ordinary intent IDs, not bytes.
  Typed intent reads expose optional computed `targetUseCurrent` authoring
  eligibility. When a new target intent withdraws its former reviewed binding,
  retain the same-scope candidate while this trusted source/target proof is
  current, so the author can keep editing before selection. This is not selected
  or production eligibility. Ordinary ready-removal, replacement bindings and
  stale context still follow ADR 0103's clearing/reconciliation rules.

## Alternatives rejected

- Deleting the global origin-shot check: loses meaningful machine, refinement and
  geometry protections and conflates origin with intended use again.
- Reimporting identical generated bytes as an untyped upload: hides lineage.
- Approving a defective target frame just to unlock editing: fabricates acceptance.
- Endless independent original generation or prompt-only continuity: does not
  supply the actual scene image and has already failed the bounded walkthrough.
- A new media registry/service or historical receipt migration: unnecessary for
  the two bounded operations; existing records remain truthful and unchanged.

## Guardrails and qualification

Regress native origin checks, source/target isolation, separate intent streams,
target identity review, stale/tampered/cyclic inputs, reference-role packaging and
view attestations, both native specialist and Codex Exec consumers, previews,
video and snapshot/recovery validation. Add browser journeys for both explicit
operations and clear source-versus-target disclosure. Run focused checks first,
independent stable-candidate review, then one full local release gate. Preserve
the current manual project, all candidates and the unselected first-shot preview;
actual human listening and final creative acceptance remain separate.
