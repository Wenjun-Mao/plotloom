# Live-action art contract — implementation and delivery receipt

Authority: ADR 0094 and the creator-approved correction in the playable-MVP
roadmap. Implementation revision: `6632c2f` on main.

## Executed verification

- Stable committed revision: 819 backend tests passed. The earlier development
  run overlapped adapter edits and an uncommitted specialist skill; its failures
  are not the final gate. The clean rerun passed the Git-provenance test too.
- 257 frontend unit tests, application/E2E typechecks, deterministic static
  build, API F401 lint and specialist-skill validation passed.
- Nine art browser journeys passed, covering replacement, acceptance/edit,
  restart, stale references, cancellation and held cross-project responses.
- Independent Terra review found two issues: only live-action had full prompt
  checks, and stale prepared tasks still offered dispatch. Both were corrected
  in the shared contract/state owners and rechecked with 15 focused style tests.
- Live Chromium walkthrough verified required style selection, disabled
  preparation before selection, explicit 真人写实 preparation, one-click send,
  automatic delivery admission, and readable live-action report. Safari was
  not automated. Local screenshots: `output/playwright/art-style-required.png`,
  `art-style-live-action-sent.png`, `art-style-live-action-ready.png`.

## Live result, not creative acceptance

Project `ee271b49-f384-414c-9711-452ee6333b84` (雨停以后):

- Old task `ch_d219890a21bd49399c29928602dd873a` was cancelled, not erased.
  Before/after hashes of its frozen request, art, report and manifest matched.
  Original art SHA-256:
  `99dc0ab513d39b1b803c044e4ba1c12f47005e42eb89ca8711ac55494e26bfba`.
- New task `ch_a26084b5f8cd4128a4e57265e95bd44d` was prepared through the UI
  with `live-action` and the actual Brief direction, then sent once to the
  existing **Complete Plotloom character cast** assistant. No new thread.
- Delivered two scenes (S01, S02) and one phone prop (P01). Every subject's
  prompt and sheet uses the live-action render direction; painterly terms
  occur only in negative prompts. Source additions remain disclosed as
  proposed anchors. The shared adapter validated the actual delivered file.
- New art SHA-256:
  `6e6509c87308c218e84c3657949ebc2a00a157995eb9cc5ba03bb545e73e52f2`.
  Backend state: `candidate_ready`, no stale reasons, no accepted art.
  Specialist dispatch state: completed. Accepted cast remains r2.

No images/videos were generated, no creative acceptance occurred, and no
identity/reference selection was changed. Creator review is the next action.

## Retained follow-ups

- Before other-style image trials, replace the hardcoded cinematic-realism
  starting text in ArtReferenceGallery with an explicitly style-aware direction.
  It is compatible with this live-action trial but not a general style default.
- The sandboxed read-only upstream art report displays copy/export controls
  whose scripts are intentionally blocked. Present these affordances truthfully
  in a separately scoped report-UX change; do not weaken the sandbox.
- Earlier Safari disclosure-text selection, red pending treatment and technical
  wording findings remain open. This receipt does not claim those fixes.
