# Frontend workbench modularization receipt

## Outcome and correction status

The original Step 3 extracted the media workbench and authoring autosave
without changing backend wire shapes, server-authorized mutations, URL routing
semantics, or visual design. `App.tsx` and `managed-media.tsx` are compatibility
entrypoints.

This receipt is amended because its original workspace conclusion was too
broad: moving the prior App implementation to a renamed workspace file did not
establish the required narrow owners. The correction is now accepted:
`useWorkspaceSession.ts` is the sole canonical snapshot, route ref, and route
epoch owner; typed domain hooks submit named transitions through narrow session
contracts. `WorkspaceController.tsx` is a 248-line composition/view-wiring
root, rather than a second session owner.

## Ownership tree

```text
frontend/src/
├── app/
│   ├── WorkspaceApp.tsx                    # compatibility entrypoint
│   └── workspace/
│       ├── contracts.ts                    # URL, draft, and workspace-operation facts
│       ├── useWorkspaceSession.ts          # canonical snapshot, route, and epoch
│       ├── useTextProviderProfiles.ts      # profile catalog and session-key scope
│       ├── useProjectDirectory.ts          # directory cursor/currentness
│       ├── useRunSession.ts                # poll and trace-evidence currentness
│       ├── useRunCommands.ts               # start/cancel/resume/repair/rebuild commands
│       ├── useWorkspaceProjectLoader.ts    # abortable canonical aggregate load
│       ├── useWorkspaceNavigation.ts       # URL/history and draft-gated navigation
│       ├── useProjectAuthoringPersistence.ts # canonical save/create and CAS consumption
│       ├── useAuthoringDraftRecovery.ts    # restore/discard recovery interaction
│       ├── useProjectInitialization.ts     # local blank/demo workspace starters
│       ├── useProjectLifecycle.ts           # archive/restore/duplicate/delete ownership
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
left for a later assessment has been withdrawn. `useWorkspaceProjectLoader.ts`
owns aggregate-request abortion and submits hydration/rejection; navigation
owns URL/history and draft gating; authoring owns save/CAS and conflict actions;
run and initialization hooks own their respective transitions. A caller cannot
directly set canonical snapshot fields.

## Module size checkpoint

| Module | Lines |
| --- | ---: |
| `WorkspaceController.tsx` | 248 |
| `useWorkspaceSession.ts` | 380 |
| `useProjectAuthoringPersistence.ts` | 339 |
| `useWorkspaceNavigation.ts` | 160 |
| `useWorkspaceProjectLoader.ts` | 147 |
| `useRunSession.ts` | 92 |
| `useProjectInitialization.ts` | 34 |

All replacement modules remain below the 500-line project threshold.

## Independent ownership review

One attended read-only Terra reviewer found three material trace-selection
races: an old explicit selected run remaining actionable, an implicit latest
run selection not blocking the view, and an abandoned pending selection leaving
the trace screen hydrating. Each was repaired in the session contract with a
focused regression. The final re-review accepted the candidate; a proposed
cross-project concern was traced through the replacement-loader branch and
withdrawn.

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

## Added regression coverage

- A late aggregate hydration cannot repaint a project selected after navigation.
- Old save and poll projections remain rejected after navigation.
- Explicit and implicit trace selections block commands until current hydration.
- Trace A → pending trace B → brief → implicit trace cancels the abandoned
  selection and rejects B's late response.
- Existing blank/demo initialization, draft conflict/recovery, profile-key
  scope, and hook-cleanup coverage remains in the focused suite.

## Verification

- `npm run typecheck && npm test -- --run tests/app-state.test.ts tests/m1b1-app-contract.test.ts tests/workspace-owner-contracts.test.ts`: passed, 48 tests.
- `npm test`: passed, 15 files / 139 tests.
- `npm run build` twice: passed. `src/plotloom/static/workbench.js` was
  regenerated and its SHA-256 was identical both times:
  `b101544b06b8455697e32b023b62dddb2739bd8328e8a2113d2f83978fe219d9`.
  The existing Vite large-chunk warning remains.
- `uv run pytest -q`: passed, 674 passed / 9 skipped (278 existing warnings).
  An initial run exposed an ignored top-level Playwright artifact; it was moved
  recoverably to `/tmp` before the clean-root check was rerun.
- `npm run test:e2e`: passed, including E2E TypeScript checking and 30 browser
  tests. The environment's `NO_COLOR` warning remains.
- A freshly built real FastAPI workbench was opened at 1440×900; the rendered
  three-column demo brief, editable form, canonical-stage inspector, and run
  inspector were visually checked. The retained runtime's optional
  `authoring-draft-capabilities` probe returned 404 and correctly fell back to
  session drafts; it is pre-existing and outside this frontend-only correction.
- `uv build --wheel --out-dir <isolated temporary directory>` and
  `uv run --locked python scripts/smoke_installed_wheel.py <that directory>`:
  passed for `plotloom-0.1.0-py3-none-any.whl` (SHA-256
  `9859f4ce09bd5af59c48788ce889d88426e738bebc951ad96b270039f2d13c69`).

No provider call, live credential, backend configuration change, or user data
was used.
