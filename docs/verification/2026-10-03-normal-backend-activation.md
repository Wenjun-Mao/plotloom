# Owner-authorized normal backend activation

Status: completed on October 3, 2026, Toronto time, after the owner explicitly
said **“go ahead”** to normal backend/schema activation. This is a follow-up to
the completed E2E-first walkthrough, not a renewed generation window.

## Scope and deployed revision

Activated the existing normal installation at `http://127.0.0.1:8841/v2/`
using its existing data root, `.local/creator-walkthrough`, and the supported
`uv run --locked python services/creator_workbench/manage.py start --data-root
.local/creator-walkthrough` entrypoint. The command completed successfully.
No data copy, reset, manual SQL migration, new provider dispatch, credential
replacement or test-copy promotion was performed. H3 remains disabled.

Deployed checkout: `aa56ffdbe3ffc374edcdb99e8b61c0070e85cc7b`, clean `main`.
Its production/test code is unchanged from the full-CI-tested
`e835d0f3a2cd8daa52257503c8d1dd1b810d32e2`; intervening commits only record
closeout and owner listening. The existing
[release run37169099225](https://github.com/Wenjun-Mao/plotloom/actions/runs/37169099225)
passed1062 backend,421 frontend and133 E2E cases, plus types, build/static,
archived reader, wheel and installed-wheel smoke. This activation is not a
claim of a new full CI run on the later documentation revision.

The normal Docker container was recreated and became healthy. New start time:
`2026-10-04T02:56:16.835285932Z` (October3,22:56 Toronto).

- Container: `a76c32802be7d59a5dde4b67c3d894a1b0656b447f9d9211d99ec92a64676d06`.
- Image: `sha256:944828dc67fe9ff6e77557a117e277b861d0f08790a21db2b3c35b0a30bb753d`.
- Served `workbench.js` SHA-256: `70b352e2921b5a01c35da42296e94fdd1c789158661a95333cbb0a685c0628db`.

## Preservation and schema result

The existing read-only capture helper recorded original project
`ee271b49-f384-414c-9711-452ee6333b84` immediately before and after activation.
The pre-activation capture also exactly matched the walkthrough preflight.
The approved [ADR0107](../adr/0107-shot-production-presentation.md) transition
ran through normal project opening, with exact predecessor-schema admission.

| Check | Result |
| --- | --- |
| Table count |73 →74; only `v2_shot_presentations` added |
| Added table rows |0 |
| All73 existing table rows |Unchanged |
| All67 managed file hashes |Unchanged |
| All7 original API projections |Unchanged |
| Normal specialist settings hash |Unchanged |
| Isolated copy's job/segment/selection/review projection |Unchanged |

Local evidence is retained in `.local/unattended-2026-10-02/evidence/`:

- `manager-normal-activation-before.json`: `621259c3578a334a9cfe6b245b41acfbe7946c3f6796123f219ad55af5d916c1`.
- `manager-normal-activation-after.json`: `7ab3d1b5d69dd6e5fb6c551caa1b2cf697959edf054ef5b314381576f431ba63`.
- `normal-backend-activation-source.jpg`: `a9530ffa2022b1e0a01f5dfd11635500dc74cac1e4bd084744447e87872223a2`.

The two capture hashes intentionally differ because of the new empty table;
the comparison removes only that named table when checking the old rows.
No claim of whole-database byte equality is made.

## Executed deployment checks and limits

Normal `/healthz` returns `status: ok`; `manage.py check-bridge` confirms the
native bridge is available. Both configured normal specialists are idle with
their existing task identities. OpenAPI now exposes GET/PUT
`/api/v2/projects/{project_id}/shots/{shot_id}/production-presentation`.
The served JS hash matches the qualified bundle; container FFmpeg/ffprobe
report `5.1.9-0+deb12u1`. `/api/v2/video-pilot-budget` still reports
`configured: false`, zero reservations and no attempts.

The actual normal browser was freshly reloaded after deployment. It renders
the original **雨停以后** source, accepted outline r1 and current story routes
without captured browser errors; no edit/confirm/generate controls were used.
The retained screenshot is the original normal project, not the completed
test-copy production. The normal original has not acquired the copy's script,
storyboard, clips or approvals. The isolated8851 copy and its17 ingested jobs,
12 selected/current segments and owner listening history remain intact.
Final-film polishing, assembled-route sound approval, copy promotion and H3
enablement are separate decisions, not implied by this successful deployment.
