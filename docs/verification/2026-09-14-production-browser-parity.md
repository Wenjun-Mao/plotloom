# Production browser parity receipt

Captured 2026-09-14 against the clean baseline `7f95071`.

## Outcome

All retained browser journeys now enter through `build_runtime_app` with a
temporary project-folder root and a separate application-data root. The suite
uses the real FastAPI route surface and file SQLite persistence. It does not
select the retained shared repository, an old app factory, a legacy storage
fixture, a Wan video adapter, or a synthetic native media completion event.

The work exposed and repaired four production contracts: project-folder
lifecycle routes and replay identity, lifecycle quiescence for external manual
publications, structured domain-validation responses, and continuous
durable-draft CAS after an acknowledgement. ADR 0047 records the ownership
decision.

## Baseline-to-candidate parity inventory

| Journey group | Baseline fixture | Candidate production evidence |
| --- | --- | --- |
| Navigation, first save, graph, M1-B1 authoring, profiles, generation repair | Default `test`: legacy FastAPI/shared SQLite | Production `test`; project-folder SQLite, application SQLite, and external OpenAI-compatible fake |
| Project lifecycle | Default legacy route surface | Archive, restore, exact-title delete, response-loss duplicate replay, stale selection, and session recovery through project-folder routes |
| Authoring drafts and close | Five `projectFolderTest` specs already used a direct-folder shim | Same routes through `build_runtime_app`; retained drafts, close/reopen, restart, snapshot restore, and explicit canonical consumption |
| Imported stills, reviewed keyframes, references, and image workflow | Default legacy runtime | Production media/approval/managed-byte paths; restart, preview, stale/reapproval, and media-protected deletion |
| Video | Default and `h3Test` fixtures could choose retained Wan or H3 | Typed offline H3 only; selected-pair native playback, no-stretch catalog policy, direct-folder restore, range playback, and restart |

The candidate's 39 tests map to the same product journeys, but every fixture
now imports the sole `test` from `frontend/e2e/fixture.ts`. That fixture starts
`frontend/e2e/fake_video_runtime.py`, which composes the shipped factory with
`OfflineH3GatewayFake` and `MiniMaxH3GatewayAdapter` only.

Video parity is intentionally split by contract rather than provider switch:

- `video-pilot.spec.ts` proves H3 selected-pair ordering, real native playback,
  range delivery, restart, and native final-frame hold without dispatching an
  `ended` event.
- `video_backends/minimax_h3/h3-video-pilot.spec.ts` proves the frozen H3
  no-stretch profile path.
- `project-folder-video.spec.ts` proves the portable direct-folder restore
  path.
- Historical Wan adapter coverage remains backend-only in
  `tests/backend_core/test_p2_video_jobs.py` and
  `tests/backend_core/test_atlas_wan_transport.py`; no browser fixture selects
  it.

## Lifecycle and authoring contract evidence

Project SQLite owns archive/restore and canonical-prefix copying. The
application SQLite ledger owns only duplicate idempotency identity and its
copied-prefix receipt. A replay reads its reserved destination instead of
re-evaluating the source. Archive and permanent deletion share the folder-close
quiescence guard, including nonterminal manual image and character-reference
publications. Permanent deletion is further limited to archived, media-free
homes under an exclusive lease; the application run index is discarded only
after that home is removed.

The production endpoint also preserves `project_managed_assets_present` and
the structured `domain_validation` issue list. The workbench's next local
draft revision continues from the acknowledged server draft until that exact
receipt is consumed by a canonical save, preventing a same-tab revision-zero
self-conflict.

## One-time retained-caller inventory

The post-cutover caller inspection found these retained-only surfaces. They
are explicitly out of scope for this browser migration and are the next
retirement inventory; production `build_runtime_app` does not call them.

| Retained surface | Current responsibility | Next retirement decision |
| --- | --- | --- |
| `src/plotloom/api/application.py` and `api/{projects,generation,image_jobs,managed_media,video}.py` | Old shared-repository app and its route modules | Migrate or retire as one API surface; do not dual-wire project-folder routes |
| `src/plotloom/persistence/legacy_repository.py` and `persistence/__init__.py` | Retained shared `SQLiteRepository` facade/export | Retire only after its direct API and tooling callers are migrated |
| `src/plotloom/__init__.py` and `api/__init__.py` | Legacy public `create_app` / `SQLiteRepository` aliases | Remove in the same compatibility-major decision, not piecemeal |
| `src/plotloom/conformance.py`, `alpha_acceptance.py`, and `media_jobs.py` | Historical acceptance/conformance and media-job tooling | Re-home each tool on an explicit project-folder workflow or archive it with its historical evidence |

No Narrative Forge runtime/data import was introduced. No retained project
data, gateway configuration, plugin, or `.env` file was changed.

## Independent review

One read-only independent review found that archive and permanent deletion had
not inherited the existing close guard for nonterminal manual publications.
The lifecycle boundary now delegates to that same quiescence guard, and a
production API regression verifies `409 project_busy` for an active image
publication on both transitions. The focused re-review found no remaining flaw
in that finding.

## Verification

| Check | Result |
| --- | --- |
| focused production runtime API checks | passed: run progress, restart/snapshot, lifecycle/replay/delete, and structured validation |
| `npm --prefix frontend run test` | 16 files, 149 tests passed |
| `npm --prefix frontend run typecheck` and `typecheck:e2e` | passed |
| `npm --prefix frontend run test:e2e` | 39 passed on the production project-folder runtime |
| `npm --prefix frontend run build` | passed; refreshed `src/plotloom/static/workbench.js` (existing Vite chunk-size warning) |
| `uv run --locked pytest -q` | 725 passed, 9 skipped, 269 existing warnings |
| built-wheel install smoke | passed for `plotloom-0.1.0-py3-none-any.whl`; SHA-256 `88ad3436982fbc6f70ad87326c1624d93d0595fe40e35bbe00f2286697e899b4` |

The existing FastAPI TestClient deprecation warning and Vite bundle-size
warning remain informational. No test suite relies on a provider credential or
on a real provider request.
