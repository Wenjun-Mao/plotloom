# Frontend workbench modularization receipt

## Outcome and correction status

The original Step 3 extracted the media workbench and authoring autosave
without changing backend wire shapes, server-authorized mutations, URL routing
semantics, or visual design. `App.tsx` and `managed-media.tsx` are compatibility
entrypoints.

This receipt is amended because its original workspace conclusion was too
broad: moving the prior App implementation to a renamed workspace file did not
establish the required narrow owners. The correction introduces named profile,
directory, run-session, route-contract, inspector, and dialog boundaries, but
must receive an independent source-ownership review before it can claim full
workspace completion. The retained workbench/session composition is therefore
an explicit open correction, not a deferred Step 4 assessment.

## Ownership tree

```text
frontend/src/
├── app/
│   ├── WorkspaceApp.tsx                    # compatibility entrypoint
│   └── workspace/
│       ├── contracts.ts                    # URL, draft, and workspace-operation facts
│       ├── useTextProviderProfiles.ts      # profile catalog and session-key scope
│       ├── useProjectDirectory.ts          # directory cursor/currentness
│       ├── useRunSession.ts                # poll and trace-evidence currentness
│       └── WorkspaceViews.tsx              # inspector and dialogs
├── features/
│   ├── authoring/
│   │   └── useAuthoringDraftAutosave.ts     # durable CAS draft flight/timer ownership
│   └── media/
│       ├── ManagedMediaWorkbench.tsx        # media composition root
│       ├── assets/
│       │   ├── AssetImportPanel.tsx
│       │   ├── MediaCandidates.tsx
│       │   └── useAssetKeyframeActions.ts
│       ├── image-jobs/
│       │   ├── ImageJobPanel.tsx
│       │   └── useImageJobActions.ts
│       ├── keyframes/
│       │   ├── KeyframeAndPreviewPanel.tsx
│       │   └── useMediaSelectionContext.ts
│       └── references/
│           ├── CharacterReferencesPanel.tsx
│           ├── SamePersonReviewPanel.tsx
│           └── useCharacterReferenceActions.ts
├── App.tsx                                 # 2-line compatibility entrypoint
└── managed-media.tsx                       # 2-line compatibility entrypoint
```

The original claim that an oversized workspace composition was intentionally
left for a later assessment has been withdrawn. This receipt must not be used
as evidence that the correction is complete until the remaining project-session
owner is decomposed and independently reviewed.

## Independent ownership review

An attended read-only review confirmed that `WorkspaceOperation` and
`DurableDraftStatus` now have one declaration in `app/workspace/contracts.ts`;
autosave imports that contract and no longer needs a widened local type or a
controller cast. The review rejected completion because
`WorkspaceController.tsx` still mixes project loading, authoring-save/draft
coordination, navigation, run commands, lifecycle actions, and rendering above
the project guideline. This is an explicit rejection, not a passing review or
a reason to postpone the work to Step 4.

## Preserved behavioral contracts

- URL query state remains the route fact source; Back/Forward, selected entity,
  run identity, load epochs, and aborted/superseded response rejection remain
  in the workspace session.
- Authoring autosave retains session-first buffering, project draft CAS,
  single in-flight requests, queued newer typing, 409 conflict preservation,
  recovered-draft seeding, and cleanup of owned timers.
- Media keeps refresh sequencing and abort rejection; per-profile session-only
  keys, manual clipboard fallback, image-job delivery currentness, frozen
  identity review, selected-only keyframe behavior, and frozen-duration
  animatic playback remain unchanged.
- `api.ts` and `types.ts` deliberately remain stable shared transport/wire
  boundaries: this extraction required no endpoint or wire-shape change.

## Verification

- Baseline frontend unit suite before extraction: 132 passed.
- Correction checkpoint frontend unit suite: 135 passed, including owner
  normalization/route contracts and a late poll response rejected after
  Back/Forward changes project session.
- Correction checkpoint: `npm run typecheck`, 135 frontend unit tests, and
  `npm run build` passed; a second build left `workbench.js` byte-identical.
- Locked Python suite: 674 passed, 9 skipped. The existing FastAPI TestClient,
  SQLite/Python 3.12, and Pydantic serialization warnings remain.
- Real FastAPI browser E2E: 30 passed. The environment's `NO_COLOR` warning
  remains. A real FastAPI/Vite 1440×900 workbench inspection is retained at
  `docs/verification/supporting/frontend-workspace-correction-1440x900.png`;
  the three columns, editable brief, inspector, and frozen-profile recovery
  notice were visible with no clipping or design/test-ID change.
- A fresh isolated wheel smoke passed for
  `plotloom-0.1.0-py3-none-any.whl` (SHA-256
  `815acc7c9b09f0f22b2ef0a3907ad448ec3176c39c6824189ab45916e9486a81`).
- Post-extraction `npm run typecheck`: passed.
- Post-extraction frontend unit suite: 132 passed.
- Production frontend build: passed; regenerated
  `src/plotloom/static/workbench.js`, then a second build produced the same
  generated-static diff (freshness verified). The pre-existing Vite large-chunk
  warning remains.
- Locked Python suite: 674 passed, 9 skipped. Existing FastAPI TestClient,
  SQLAlchemy/Python-3.12, and Pydantic serializer deprecation warnings remain.
- Real FastAPI browser E2E: 30 passed, including URL back/forward, project
  lifecycle/drafts, stale response rejection, image delivery/reference
  currentness, still-preview, selected-pair playback, and project-folder
  restart paths. The environment's `NO_COLOR` warning remains.
- `uv build --wheel` and an isolated installed-wheel FastAPI route smoke:
  passed. An initial smoke assertion used an obsolete `/api/projects` path;
  inspection confirmed the packaged API's documented `/api/v2/projects` route
  and the corrected smoke passed.

A real FastAPI fixture journey captured and visually inspected the durable
1440×900 workbench screenshot at
`docs/verification/supporting/frontend-workbench-modularization-1440x900.png`.
No provider call, backend schema/configuration change, live credential, or
user data was used.
