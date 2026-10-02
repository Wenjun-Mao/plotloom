# Isolated launcher preflight checkpoint

Date: 2026-10-02, checkpoint at 06:16 UTC / 02:16 Toronto.
Authority: [unattended walkthrough](../roadmap/2026-10-02-unattended-creator-walkthrough.md),
step 1 prerequisite repair for steps 2–3. Source baseline: `196c43a`; scoped
changes are uncommitted on retained `main`, pending independent manager review.

## Result and boundaries

The isolated launcher now owns server storage, exact bridge settings identity,
outbound executable, URL/credential environment and both ports together. Actual
HTTP send routes for text Art and an image Art reference exercised the complete
shim subprocess → authenticated bridge → fake native executable path. Each sent
exactly once to its test-generated role UUID with copy-local frozen package paths.
Foreign-installation UUIDs, health probes and authentication failures queued
nothing. Nonzero native exit remains unknown; its exact lease/receipt survives
restart and blocks rebinding/replay.

The final restored installation was reused. A real launcher subprocess served
health, empty specialist settings and staged `/v2/` assets, then terminated with
exit 0. Both ports and its ephemeral shim were cleaned up. No real native
assignment, package preparation, ImageGen, H3 call or creative acceptance occurred.
No normal static assets, bridge, LaunchAgent, deployment configuration or token
were changed. The earlier configurable standalone bridge-port draft was removed;
only the isolated runtime config owns test ports.

The first no-queue CLI probe showed an additional root cause: Uvicorn replays
SIGTERM after server shutdown, bypassing the outer context under the native
default handler. Its earlier `launcher-preflight.json` proves kernel port shutdown
only; it is retained unchanged. The final signal-boundary fix and subprocess
regression qualify shim cleanup. [ADR 0098](../adr/0098-isolated-workbench-native-transport.md)
records the durable composition and lifecycle contract.

## Executed checks

- Focused transport batch: `uv run --locked python -m pytest
  services/creator_workbench/test_isolated.py services/creator_workbench/test_bridge.py
  services/creator_workbench/test_manage.py tests/test_codex_image_dispatch.py
  tests/test_specialist_settings.py tests/test_specialist_routes.py
  tests/test_native_wake_art.py -q`: **64 passed** before the SIGTERM fix.
- Final launcher suite, including real CLI SIGTERM regression: **12 passed**.
  One existing Starlette/httpx deprecation warning; no new warning suppression.
- Ruff on launcher/tests/dispatcher/registry and API F401 check: passed.
  `git diff --check`: passed.
- Cast reviewer findings: retained label/control assertions now cover 26 labels
  for two characters; **12 unit tests passed**. The browser regression seeds six
  existing painterly fields in only its own fixture, verifies cancellation,
  explicitly replaces them, preserves the complete unrelated accepted cast and
  mappings, and inspects the new frozen reference context: **1 E2E passed**.
- Frontend and E2E typechecks passed. Vite staged build passed at
  `.local/unattended-2026-10-02/static`; `src/plotloom/static/` remains unchanged
  pending manager review/promotion. Existing bundle-size advisory remains.
- Real no-queue startup/shutdown probe: passed, with zero shim directories left.
- Original API state, all **73 database tables** and **67 retained files** still
  equal launch baseline. Normal specialist settings/leases and deployment bytes
  unchanged across the probe. Both quarantined attempted roots are byte-preserved.
  All **35 snapshot-manifest files** in the final copy still match the pristine
  snapshot. Final binding IDs are null, dispatch roots empty and no inflight lease.

## Evidence and handoff

Workflow-local evidence lives under `.local/unattended-2026-10-02/`:

- `evidence/launcher-preflight-final.json`: authoritative final no-queue gate.
- `evidence/launcher-preflight-pytest.log`, `evidence/launcher-signal-pytest.log`.
- `launcher-preflight-verified/` and `launcher-preflight-signal/`: retained fake
  packages, native call logs, receipts and reservations used by the tests.
- `evidence/launcher-cleanup-original-before.json` and
  `evidence/launcher-cleanup-original-after.json`, compared with `baseline.json`.
- `evidence/launcher-startup-cleanup.log`; earlier startup evidence is retained.

Final root: `.local/unattended-2026-10-02/final-installation`; intended URL after
restart: `http://127.0.0.1:8851/v2/`, private bridge port 8852. Both are stopped at
this checkpoint. The dedicated credential is outside project/application state
at `~/Library/Application Support/Plotloom/unattended-2026-10-02-isolated/bridge-token`
(parent 0700, file 0600); credential contents are absent from evidence.

Unknown jobs `ij_5a327be2cd19489d8d5f873c5c09546e` and
`ch_d5b3330baa5f41448462f39dc243ace3` remain in their original quarantined roots.
Do not clear, relabel, replay or infer definitive no-queue from later healthy
configuration. Typed trusted prequeue refusal remains an unresolved follow-up.

Stopping condition reached: source is quiescent for independent review and the
manager's scoped verified commit. `project_folder.py` is part of the pinned image
execution owner, so no live image package is prepared/sent while that owner is
dirty. After manager review/commit and explicit continuation, configure fresh
dedicated native chats through the copy UI, verify binding paths, then resume
reference review and script/storyboard. Existing test-copy Cast still needs an
explicit painterly-to-live-action revision and downstream refresh. No new UI
journey milestone or owner creative approval is claimed. Measured usage/cost
deltas are unavailable at this checkpoint.

## Manager integration review

The independent GPT-6.1 Sol / High review found no actionable defects in the
stable transport candidate. It separately passed **64 transport/manage tests**,
checked occupied-port refusal before state/queue effects, and verified that the
normal default remains `codex` with inherited environment. The manager passed
**286 frontend tests**, both typechecks, the revised Cast E2E, and **52 existing
bridge/dispatch/settings/route tests**.

The first broad Python run produced **829 passed, 1 failed**. Its failure was the
old gateway-only service-root guard, although HEAD already tracks the workbench
adopted by ADR 0095. The service ownership checks now live in a focused module
and admit exactly the two declared service owners, preserving tracked-file and
real-directory restrictions. No runtime behavior was loosened. The extraction
file was reduced from 569 to 499 lines. The combined extraction/service checks
passed **19 tests**; independent review separately passed the **7 service tests**
and found no actionable issue. ADR 0095 records this contract correction.
The fresh broad Python rerun then passed **836 tests** in 171.61 seconds, with
only the existing Starlette/httpx deprecation warning. API F401 and diff checks
also passed.

After checking that the normal specialists had no active turn or reservation,
the manager rebuilt the checked frontend. Served, checked and staged bundle
SHA-256 agree:
`6f88b314b7394021b70c079f0bb2bccbe46c61b82a2c809e410d588b88a733b8`.
The normal service/bridge was not restarted. Fresh original-project captures
before and after this promotion match all baseline API state, 73 database tables
and 67 retained-file hashes exactly. See `manager-precommit-original.json` and
`manager-postbuild-original.json` in the local evidence directory.

No fresh native package has been sent at this integration checkpoint. The real
creator journey resumes only after the reviewed source is committed; no owner
creative acceptance is implied. The repository CI is manual-dispatch only, so
a push by itself does not establish a CI result.
