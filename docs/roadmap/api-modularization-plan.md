# API modularization proposal

**Status:** director-approved and implemented as a behavior-preserving API
modularization checkpoint. The project-folder storage destination is already
decided by the approved storage plan; only its production cutover timing
remains deferred.

## Checkpoint

- **Baseline:** clean `4789d0d9fbe8cbf1837a746554eb7bd780a83973`.
- **Outcome:** a source-backed, behavior-preserving extraction plan for
  `src/plotloom/api.py` (3,018 lines), plus follow-up inventory.
- **Owned scope:** this document only.  No runtime, frontend, test,
  configuration, provider, retained-data, or generated-static work occurred.
- **Acceptance evidence for this proposal:** the factory, route registrations,
  public callers, runtime composition, and focused characterization tests were
  inspected; local links and the final diff are checked below.
- **Stopping condition:** director review decides the first code slice.  A code
  refactor needs a separate source assignment.

The current repository standard is an aim of roughly 400 lines where practical;
more than 500 lines is a strong signal to split responsibilities before adding
more code.  It is not a line-count-only mandate.

## What grew, and why

`api.py` grew by adding feature slices chronologically to two closure-heavy
FastAPI factories.  The normal `create_app` factory owns repository and runtime
composition, provider-profile admission/readiness, errors, lifecycle and
generation routes, video, managed media, image jobs, and the static mount.  The
same file also retains `create_project_folder_authoring_app`, a deliberately
limited direct-storage composition added for the storage checkpoint.

This is a cohesion problem, not merely a size problem:

| Current area | Source range | Captured authority/dependencies | Cohesive concern |
| --- | ---: | --- | --- |
| Wire DTOs and small serializers | 123–668 | Pydantic/domain models | API request/response shape and public-field validation |
| Normal factory and text-backend admission | 669–1025 | repository, defaults, key availability, resolver, secret source, scheduler | trusted profile selection, ephemeral readiness, credential lease and frozen snapshot admission |
| Normal error translation | 1026–1207 | domain, persistence, media, and request-validation errors | stable HTTP status/code/detail translation |
| Project lifecycle and video | 1208–1387 | repository, video service, artifact store | project state and explicit video-pilot operations |
| Managed media and image jobs | 1388–1886 | repository, artifacts, exchange, H3 catalog | immutable asset/preview evidence and manual image-package lifecycle |
| Stages, approvals, runs, legacy media and profile settings | 1887–2322 | repository, scheduler, text-backend admission | canonical updates/review; generation lifecycle; profile management |
| Project-folder factory | 2323–3018 | `ProjectFolderStorage`, opened project handle, project artifacts/exchange | storage-only authoring and still/image workbench proof |

The normal and project-folder routes look similar in places, but they do not
currently have interchangeable contracts.  The project-folder factory opens a
manifest-selected handle for every request, uses confined per-project artifacts
and exchange roots, supports durable authoring/media draft CAS, and intentionally
does *not* expose normal runtime lifecycle, profiles, provider admission,
archive/restore, video, or a browser-selectable storage mode.  Its active-only
listing also deliberately defers cursor/archive behavior.  Sharing those routes
today would either erase these distinctions or introduce a generic storage
adapter that hides them.

## Public behavior to hold fixed

The first extraction is behavior-preserving.  It must retain:

- Public imports: `plotloom.create_app`, `plotloom.api.create_app`, and
  `plotloom.api.create_project_folder_authoring_app`; the normal factory's
  complete keyword-only signature and its defaults stay unchanged.
- Every existing `/api/v2` method, path, operation response model, JSON alias,
  nullable/default field, status code, deprecation marker, error code/detail
  shape, and header contract.  This includes `Idempotency-Key`, the
  `X-Plotloom-Draft-Consumed-Revision` receipt, byte-range video responses,
  and the deprecated run-repair route.
- The normal factory's `app.state` values, injected lifespan, completion
  observer, and `/v2` static mount.  `build_runtime_app` remains the only
  production composition caller and continues to own worker close/recovery.
- Secret isolation: browser session keys and short-lived leases never enter
  persisted profiles, snapshots beyond existing public fields, readiness
  observations, errors, traces, or logs.  Readiness remains process-lifetime,
  revision-bound evidence, not qualification or durable state.
- Trusted adapter and H3-catalog checks; active/disabled profile semantics;
  frozen run profile/version/adapter attribution; scheduler submission/resume/
  cancellation behavior; repository transaction, lifecycle, idempotency, and
  storage semantics.
- Project-folder-only draft consumption and atomic canonical-save behavior,
  handle close discipline, confinement, and direct-storage error mapping.

There is no evidence that either factory is obsolete.  The only source-backed
removal candidate is the duplicated *placement* of wire models, serializers,
and error mapping in the monolith after equivalent extracted modules are in use;
no route, factory, storage mode, legacy repair endpoint, or static mount is
approved for deletion.

## Proposed module boundaries

Keep `src/plotloom/api.py` as the small compatibility façade (target: 120–220
lines): re-export the two factories and construct the normal application.  Do
not create an `api/` package alongside `api.py`, and do not use a generic
``Dependencies`` bag.  The factory should pass explicit dependencies to each
cohesive registrar.

| Proposed module | Target size | Owns | Directional dependencies |
| --- | ---: | --- | --- |
| `api_models.py` | 350–480 | request DTOs, small response wrappers, approval view serializers, scheduler/secret protocols | domain, provider-profile, video/image contracts; no router or persistence implementation |
| `api_errors.py` | 220–320 | normal runtime exception-to-HTTP registration and canonical schema response | exceptions, validation, managed-media/image errors; no route registrar |
| `api_text_backends.py` | 400–480 | the focused text-backend admission/readiness service and profile/settings routes | repository, registry, secret/resolver protocols, models; no generation router import |
| `api_projects.py` | 260–340 | normal project lifecycle, cursor codec, stage/runs/media listings | repository and project DTOs |
| `api_generation.py` | 330–430 | canonical stage/review routes, run creation/rebuild/resume/cancel/repair, legacy unavailable media-task route | repository, text-backend admission service, scheduler, models |
| `api_video.py` | 220–300 | budget/backend/job/review/media-range routes | repository, explicit `VideoJobService`, artifact store |
| `api_managed_media.py` | 360–460 | imports, asset serving, visual intent, reviewed keyframe/crop, previews and workbench applicability | repository, artifact store, limits, H3 lookup, models |
| `api_image_jobs.py` | 380–480 | character-reference and image-job package export/refresh/cancel flows | repository, exchange, artifact store, image contracts |
| `project_folder_authoring_api.py` | 240–340 | storage-factory setup, scoped errors, handle lifetime, project/stage/draft/review routes | `ProjectFolderStorage`, API models/serializers; no normal factory import |
| `project_folder_media.py` | 280–380 | direct-storage managed assets, visual intent, reviewed keyframes, previews/workbench | opened project handle and its confined artifacts |
| `project_folder_image_jobs.py` | 300–420 | direct-storage character-reference and image-job package lifecycle | opened project handle and its run-local exchange |

The estimates include nearby helpers and imports, not speculative abstraction
layers.  A router registrar may receive an `APIRouter` or an app plus the exact
dependencies it needs.  `TextBackendAdmission` is justified as a focused
service because it alone owns profile snapshot creation, readiness observation,
trusted adapter validation, and request-scoped credential admission.  Media
and project-folder modules should receive named repository/artifact/exchange or
opened-handle arguments; they must not gain a reusable untyped service locator.

```
api.py (compatibility façade / normal factory)
  ├── api_models.py                 <- domain + API contract modules
  ├── api_errors.py                 <- exceptions + validation
  ├── api_text_backends.py          <- repository, adapters, secret source
  ├── api_projects.py ──────────────┐
  ├── api_generation.py ────────────┼── repository / explicit scheduler
  ├── api_video.py ─────────────────┤
  ├── api_managed_media.py ─────────┤── explicit artifact/exchange services
  └── api_image_jobs.py ────────────┘

create_project_folder_authoring_app (separate compatibility factory)
  ├── project_folder_authoring_api.py
  ├── project_folder_media.py
  └── project_folder_image_jobs.py
       └── ProjectFolderStorage -> per-request opened project handle
```

The lower branch may reuse wire DTOs and approval serializers, but must not
reuse normal route implementations or normal application state.  In particular,
it may not claim that the normal `SQLiteRepository` is a project-folder
repository, nor expose project-folder behavior through the production runtime.

## Extraction sequence

1. **Freeze the observable contract.** Extend only characterization coverage
   where the present tests lack a precise assertion: route/OpenAPI inventory,
   factory signature/state/static mount, error mapping, headers, scheduler
   calls, profile readiness/secret non-retention, and project-folder draft-CAS
   and confinement behavior.  Retain the existing full route inventory in
   `tests/backend_core/test_api.py`; retain OpenAPI/TypeScript checks in
   `tests/backend_core/test_frontend_contract.py`.
2. **Extract contracts and normal error registration without changing route
   behavior.** Leave compatibility re-exports in `api.py`; check import cycles
   before moving a route family.
3. **Extract normal route families one cohesive family at a time:** projects;
   text-backend admission plus profiles; generation/review; video; managed
   media; image jobs.  Each registrar gets explicit inputs, then the factory is
   reduced.  Do not combine this with persistence or frontend restructuring.
4. **Extract the project-folder factory independently.** First its factory,
   errors, handle and canonical/draft routes; then its media and image routes.
   Compare it to normal behavior only at named shared wire contracts.  Do not
   deduplicate similar code until a contract says the dependencies and
   lifecycle are actually equivalent.
5. **Stabilize, then consider only evidence-backed sharing.** A shared pure
   serializer or DTO is acceptable.  A shared router, storage adapter, broad
   media helper, or changed route is a separate design decision and, if it
   changes public/runtime behavior, requires a concise ADR before code.

This order removes the normal factory's mixed responsibilities early while
keeping its entrypoint and runtime semantics stable.  It postpones the highest
risk false abstraction: merging the two storage compositions merely because
their URLs overlap.

## Characterization and verification plan

No checks were run for this documentation-only audit.  A code assignment should
run focused checks after the relevant extraction and expand only when its stable
candidate changes:

- `tests/backend_core/test_api.py`, `test_project_lifecycle.py`,
  `test_storyboard_review.py`, `test_pipeline.py`, and
  `test_exact_work_unit_repair_integration.py` for normal projects/runs;
  `test_m15_profile_repository.py` for profiles/admission.
- `test_managed_still_media.py`, `test_image_jobs.py`, and
  `test_p2_video_jobs.py` for explicit artifact, exchange, and range behavior.
- `tests/test_project_storage.py` and
  `tests/test_project_storage_image_workflow.py` for the separate project-folder
  composition, CAS receipts, restart/isolation, and confined package paths.
- `tests/backend_core/test_frontend_contract.py` plus configuration/runtime
  boundary tests for OpenAPI/TypeScript fields, static mounting, lifecycle, and
  secret non-exposure.  Browser tests must cover the existing normal workbench
  path and the direct-storage evidence path only where it is already exercised.

On the stable integrated candidate, follow the repository gate: focused Python
checks first, then `uv run pytest -q`, frontend test/typecheck/build/e2e,
`uv build --wheel`, the established installed-wheel smoke, and verify that a
subsequent frontend build leaves `src/plotloom/static/` clean.  Extraction alone
does not change frontend assets; if the frontend changes, regenerated assets
remain required.  Check `git diff --check`, imports, and route/OpenAPI snapshots
at every slice.  Preserve failures as evidence; do not paper over an import
cycle or behavior difference with forwarding modules.

## Other oversized first-party modules

This is an inventory, not authorization for parallel rewrites.  Priority uses
both size and mixed responsibility; a large but coherent contract module is not
automatically next.

| Priority | Module(s), current lines | Observed responsibility | Follow-up boundary to assess separately |
| --- | --- | --- | --- |
| 1 | `src/plotloom/persistence.py` — 10,120 | SQLAlchemy rows, repository lifecycle, project/stage/run/media/profile/approval persistence | repository capability slices and model mapping; never mix with this API extraction |
| 2 | `src/plotloom/generation/work_units.py` — 4,772 | work-unit schema, facts, prompts/contracts and repair inputs | contract families by stage/repair authority; require ADR ownership review first |
| 3 | `frontend/src/managed-media.tsx` — 2,209; `frontend/src/App.tsx` — 1,633 | media workbench and application composition | route/page/state seams; coordinate static rebuild and browser evidence separately |
| 4 | `src/plotloom/work_unit_pipeline.py` — 1,719 | durable work-unit execution and correction path | lifecycle vs correction orchestration, after generation contracts are frozen |
| 5 | `src/plotloom/domain.py` — 1,550; `validation.py` — 1,484 | canonical types and cross-stage validation | domain families and validator ownership; high public-contract risk, not a mechanical split |
| 6 | `src/plotloom/alpha_acceptance.py` — 1,351; `generation/story_graph_topology.py` — 1,110; `generation/planning.py` — 1,063 | acceptance evidence; topology; planning | assess cohesion per domain before splitting |
| 7 | `frontend/src/pages/SceneBeatsPage.tsx` — 1,276; `frontend/src/types.ts` — 1,099; `frontend/src/pages/StoryBiblePage.tsx` — 1,032 | page UI and public client contract | page-local components and type families, preserving generated asset discipline |
| 8 | `project_storage.py` — 822; `generation/correction_directives.py` — 808; `pipeline.py` — 738; `image_job_exchange.py` — 714; `media.py` — 665; `conformance.py` — 655; `generation/correction_schema.py` — 582; `generation/orchestration.py` — 552; `generation/storyboard_timing_repair.py` — 527; `frontend/src/api.ts` — 573 | bounded storage, generation, exchange/media, qualification, and client transport domains | revisit only with a concrete cohesion finding; several may be large but already domain-focused |

The source-test modules also exceed the guideline, but they are intentionally
excluded from this first-party runtime/frontend inventory.  They should be
considered only when their test ownership or fixture coupling impedes a focused
change.

## Trade-offs and decisions for review

- **Chosen:** preserve `api.py` as the public import façade and extract
  directional modules around existing domains.  This minimizes entrypoint and
  wheel risk.
- **Rejected:** a mechanical line-based split, one giant `routes.py`, a
  catch-all helpers module, duplicated routers, and a generic dependency
  container.  These move text without recovering ownership boundaries.
- **Rejected:** normalizing normal and project-folder factories now.  The
  direct-storage factory's documented limits and distinct CAS/artifact
  lifecycle are meaningful behavior, not accidental duplication.
- **Deferred decision:** whether future production cutover adopts project-folder
  storage, and whether any media/preview helper becomes truly shared.  Those
  are runtime/storage decisions, not behavior-preserving extraction details,
  and need source evidence plus an ADR if their contract changes.

## Implementation receipt

The public `plotloom.api` package façade preserves the historic factory import
surface. Normal composition lives in `api/application.py` and delegates
explicit dependencies to focused projects, text-profile, generation, video,
managed-media, image-job, and error registrars. The limited project-folder
composition lives in `api/project_folder.py` with its direct-storage media and
image-job registrars; it is not a storage-mode switch or a shared router
abstraction.

The initial moved model module is larger than the target because it preserves
the existing public DTO/helper import surface in one mechanical extraction.
Its DTO, serializer, and protocol families are the next internal split before
adding new API contract fields; no new API surface should be added there. The
same rule applies to the retained project-folder composition, whose direct
storage lifecycle is intentionally not merged with normal routes.

Focused baseline and post-move characterization covered normal route/OpenAPI
contracts and project-folder storage behavior. The stable candidate still
requires the repository's full locked Python, frontend, wheel, install-smoke,
and browser gates before release.

### Follow-up correction: admission and direct-storage media ownership

- **Baseline:** clean `28c4a2a73ec03b2e44ab796802c66463cd979cf7`; the source
  provenance baseline is the original monolith
  `5ec8ef83fc3fa6efdd9b3b41f5e76a7a8c2e1daf`.
- **Observable outcome:** normal composition delegates application-lifetime
  text admission to `api/text_admission.py`; direct-storage asset import,
  serving, visual intent, keyframe selection, preview, and workbench routes
  live in `api/project_folder_media.py`; package/export/refresh/cancel routes
  remain in `api/project_folder_image_jobs.py`.
- **Contract evidence:** an isolated `git archive` of the original monolith
  was imported through `PYTHONPATH`, never checked out over the retained
  source. It produced a complete canonical characterization of both factories:
  route registrations, OpenAPI paths and schemas, operation IDs, aliases,
  defaults, response/header declarations, factory signatures, state keys,
  static mounting, injected lifespan identity, and completion-observer
  registration. `tests/backend_core/test_api_modularization_contract.py`
  compares the post-move candidate to its provenance-bound 206,297-byte
  canonical SHA-256 (`1d33b23c3809d63654c780d7ac07ecd2bd6acfe7a8fdb6b18a8a15b98feaa72e`).
  Only JSON key ordering is normalized.
- **Resulting sizes:** `application.py` 123 lines,
  `text_admission.py` 420 lines, `project_folder_media.py` 282 lines, and
  `project_folder_image_jobs.py` 443 lines. The previously unused media
  registrar inputs were removed rather than preserved as a forwarding layer.
- **Evidence receipt:** `docs/verification/2026-09-13-api-modularization-correction.md`.

## Audit closeout

The next action is director review of this proposal and selection of a bounded
code slice.  Worktree and commit state, check results, and usage deltas are
recorded after the documentation commit and Relay release; no new usage metric
was available during the audit.
