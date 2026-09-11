# P0 creator-workflow review

## Scope and result

Baseline: clean `9339ee6`, branch `codex/p0-imported-still-preview`.
Outcome: review the actual creator path before asking the user to trial it;
fix routine friction without starting P1 or changing production authority.
This source-only follow-up does not close or modify the historically blocked
Codex Flow run. No provider calls, merge, push, or user-project changes.

The director exercised a real FastAPI/file-SQLite browser at 1440×900 with
isolated data. Importing four existing development-session ImageGen PNGs,
comparing candidates, recording intent, explicitly reviewing three contiguous
keyframes, creating/playing/seeking a still preview, and reopening it worked.
The temporary review Approval was explicitly a Codex workflow-test judgment,
not human acceptance or production-quality certification.

## Findings and resolution

| Finding / root cause | Resolution and regression evidence |
|---|---|
| Saving the teaching sample's Brief silently discarded its displayed stages: generic Brief-first creation omitted the initial prefix. | Explicit local teaching-sample provenance sends all four stages when saving its Brief; blank creation stays Brief-only. Canonical hydration clears provenance. App tests and the real first-save journey pass. ADR 0009 records the boundary. |
| Visual-intent edits disappeared on shot changes: a form-reset effect replaced unsaved local state. Selection could freeze old saved text while different text was displayed. | Session-only drafts keyed by project/shot/candidate retain their saved intent ID. Changed bases are not silently rebased; save/discard is required before reviewed selection. Five focused hook tests cover isolation, remount, stale base, discard, unload, and corrupt storage. ADR 0027 records the contract. |
| Shot selection required leaving the media controls; review controls were buried below extensive detail (the sample exposed 407 passing gates). | Media-local shot selector and review shortcut; passing coverage/gate details collapsed below the review controls. Failed required gates still block Approval and are expanded. Long reviewer labels wrap. |

The first screenshot review showed coverage detail still displaced the review
form, so a final layout correction moved that detail below the controls. This
was a concrete continuation of the same navigation finding, not another audit.

Browser checks after the fixes confirmed:

- The unsaved style marker survived shot switching and refresh; refresh raised
  the unload warning. With a compatibility note present, reviewed selection
  stayed disabled until explicit draft discard, then became enabled.
- The review shortcut exposed the reviewer field and action buttons without
  traversing the passing gate list; detailed results remained available.
- No browser console errors were observed in the final session.

Retained visual evidence:

- [Media navigation](supporting/p0-creator-media-navigation.png)
- [Restored draft and blocked selection](supporting/p0-creator-draft-restored.png)
- [Review controls and collapsed passing details](supporting/p0-creator-review-shortcut.png)

## Verification and boundaries

- Focused frontend checks: **44 passed**.
- Full frontend unit suite: **120 passed**; TypeScript check passed.
- Full existing browser suite: **24 passed**.
- After the final coverage-layout/CSS adjustment: typecheck and the six affected
  first-save, canonical-authoring/Approval, and imported-still browser journeys
  passed. The imported-still journey includes the existing backend-restart proof.
- Final frontend build passed; generated JS/CSS included with the source.
  Vite's existing large-chunk warning remains; it is not a runtime failure.
- No backend, migration, packaging or provider contract changed; the full Python
  and wheel gates were not repeated for this frontend-only follow-up. Their
  prior results remain in the original P0 receipt, not fresh evidence here.

One Terra delegate owned sample-save changes; the director owned media drafts,
navigation and real-browser review. The delegate also reviewed only the
director-owned changes once stable. See the commit closeout for disposition.
That bounded independent pass returned no actionable findings; the director
separately reviewed the sample-save diff and its tests before integration.
Task usage/cost deltas are unavailable; no new metering was built.

Private review data and raw captures remain at
`/Users/wjmao/.codex/plotloom-p0-ux-review.P3XZdd`; the review browser and owned
server were stopped. The previously accepted restart pilot was not modified.
This review used canonical fixtures to isolate media UX from model availability;
it is not fresh story-to-image generation evidence.

## Next bounded outcome

P0 can proceed to product integration planning without a routine user-testing
gate. P1 should retain the same explicit candidate/intent/selection boundaries
when introducing proposals and production inputs. Larger side-by-side image
comparison and terminology cleanup are nonblocking polish, not evidence that
generation or audiovisual continuity has been qualified. No critical product
trade-off was uncovered that requires the user's decision in this review.
