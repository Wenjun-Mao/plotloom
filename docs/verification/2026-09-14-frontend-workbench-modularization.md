# Frontend workbench modularization receipt

## Outcome

Step 3 separates the former frontend workbench entrypoints by product
responsibility without changing backend wire shapes, server-authorized
mutations, URL routing semantics, or visual design. `App.tsx` and
`managed-media.tsx` are now compatibility composition entrypoints.

## Ownership tree

```text
frontend/src/
├── app/
│   └── WorkspaceApp.tsx                    # workspace route/session composition
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

The composition root is 479 lines. Each media capability module is below 500
lines; the largest is the cohesive keyframe/intent/preview panel (474 lines).
`WorkspaceApp.tsx` remains the explicit workspace session composition root
while route identity, request epochs, abort ownership, project loading,
pipeline polling, and page contracts are still coupled. It is intentionally
not further mechanically split in this Step 3 scope; later assessment remains
separate under the roadmap's Step 4 boundary.

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
