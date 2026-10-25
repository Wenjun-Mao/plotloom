# Batch-video publication and activation attempt, 2026-10-18

> Historical local artifacts in [the cleanup scope](../roadmap/2026-10-25-top-five-cleanup.md) were retired
> on 2026-10-25. References to those files are not available attachments or resumption
> instructions; recorded outcomes, limits and current project-owned media stand.

Current status: locally activated at `93441fc1` on October 18, 2026, 22:01 EDT.
See [completed activation](#completed-activation-october-18-2201-edt). Hosted
qualification remains failed and GitHub CI is held pending Wenjun's direct request.

Initial attempt status: source published; activation blocked by the existing native process-group
revocation guard. The old installation remains running and healthy. This is not
an activation, restart, provider-smoke or creative-acceptance receipt.

## Published source and independent evidence

Qualified product source is `20e3c65b`. The manager independently retested clean
`468b2d0e`: 13 backend, eight frontend and 23 browser cases passed, exit zero in
97.703 seconds. Historical log:
`.local/batch-video/manager-correction-retest.log`. Both independent correction
reviewers closed their concrete findings, as reported by the manager. See the
[correction record](2026-10-18-batch-video-corrections.md) for exact selections,
contracts and reuse of unaffected full-run evidence. No unaffected full gates
were rerun during publication.

After a fresh fetch, retained `main` had zero incoming divergence and ten local
commits. Normal `git push origin main` published
`00773e659fa95a311d8c6ec0c714182352bd9e06` without force. Subsequent delivery
receipt edits are documentation only and do not alter qualified executable
inputs. The retained checkout is `/Users/wjmao/.codex/worktrees/b30f/plotloom`.

The repository's manual CI workflow was dispatched for that exact revision with
`browser_grep=.*`, preserving the unfiltered verify job and all four browser
shards. [Hosted run 39146800414](https://github.com/Wenjun-Mao/plotloom/actions/runs/39146800414)
was in progress at the recorded snapshot; no hosted CI success is claimed.
Local evidence: `.local/batch-video/hosted-ci-state.json`.

## Fresh installation preflight

The deployment checkout `/Users/wjmao/projects/HU/plotloom` was clean and detached
at `7b90bbc70d69aeb7a1bfda2c4af1b6e25759560f`. Native settings were not busy;
both configured specialist roots had no `inflight.json`. The host ledger held
79 attempts: 78 completed and one `outcome_unknown`; zero queued entries and
zero validator rows. The one UNKNOWN image slot remained reserved.

Both exact homes were regular, confined directories with matching native
manifest/database project IDs and SQLite integrity `ok`. Both lacked the new
video-batch tables and were incompatible with the published current schema.
No migration, backup or recovery copy was created. The owner and manager have
explicitly authorized permanent removal of this disposable development data;
this is not an unresolved data-retention preference.

- `a99d5422-61fd-4768-89f4-118e82bbed75`: autopilot
  `895c339a-c4ec-4faf-8840-9489cd6a94ae` is `handed_off`, 55 completed attempts,
  zero video jobs. Native abandonment preview is blocked as detailed below.
- `765ce4d9-12e3-4d96-8944-b49ba381fdf2`: autopilot
  `2c90f653-a315-45af-8532-0635425ea1ea` is cancelled, with 13 completed attempts,
  one UNKNOWN attempt and zero video jobs. A fresh native preview was eligible
  with no blockers and explicitly preserved remote outcomes.

The broad process scan found the existing host bridge, no active Plotloom worker
or validator executable. This does not override the stronger native per-project
process identity/publication checks. Derived hashes and safe fact summaries are
in `.local/batch-video/activation-before.json` and
`activation-processes-before.json`; these are not project-content backups.

## Exact permanent removal and UNKNOWN preservation

Only this exact incompatible home was removed:

`/Users/wjmao/projects/HU/plotloom/.local/creator-walkthrough/outputs/20261018T002817202399Z__765ce4d9-12e3-4d96-8944-b49ba381fdf2`

The old installation's supported `abandon-and-delete` route revalidated the
current preview, manifest/revisions and immutable native attempt set under the
project's exclusive writer lease. The host acknowledged exact publication
revocation under its own fence before erasure. The route returned HTTP 204; the
home is absent and the pending-deletion list is empty. This deletion is
unrecoverable; no backup/recovery was made. Receipt:
`.local/batch-video/activation-deletion-765.json`.

All 79 host attempt rows remain byte-equivalent by canonical full-row hash:
`5075b9dcf691d0bbe0551801ed31c8af01bc5cf32a85f199fae928ace4275e66`.
UNKNOWN attempt `06e80972-9dde-41ff-be71-b477c1477465` retains its original state
and reserved image slot. Slot hash remains
`43f36bcfc07c5383b69ac6277bb68ab4347bd539d1174de75bc3bcf83271fba5`.
Queue and validator tables remain empty. The host now retains exactly one new
revocation for this removed project; no remote outcome was settled or erased.
The application removed only that project's creation reservation; its other
12 table hashes are unchanged. The completed deletion intent is retired by the
existing native owner, not retained as a recovery copy.

Hashes, owner and modes of the H3 configuration file, bridge token, deployment
configuration and specialist settings match their pre-action values. No broad
root, private host job evidence, credential file, unrelated application state or
snapshot/restore feature was removed. Post-action comparison:
`.local/batch-video/activation-after-scoped-deletion.json`.

## Activation blocker and unchanged installation

The retained home is:

`/Users/wjmao/projects/HU/plotloom/.local/creator-walkthrough/outputs/20261018T011358571296Z__a99d5422-61fd-4768-89f4-118e82bbed75`

Two fresh native previews refuse revocation with:
`ij_d8701d30216a4494af2c01ce88e2c97f: local process group is not proven absent`.
The linked host attempt `1597629c-a398-4f76-99fb-a3bb441adff6` is completed. Its
recorded worker PID/group is `90191`, born **2026-10-17 21:35:40 local time**.
That numeric PID/group now belongs to a newer process born
**2026-10-18 11:59:38 local time**:
`/Applications/ChatGPT.app/Contents/Resources/cua_node/bin/node`, with a
`node_repl` group member. Thus the observation is PID reuse by an unrelated
Codex CUA process, not evidence that the completed image job resumed.

The native `_prove_group_absent` contract deliberately refuses a live group,
including a reused leader. Its required absence proof is not satisfied. No
process was stopped to manufacture idleness, no ledger identity was cleared and
no revocation predicate or compatibility reader was bypassed. Activation must
wait for a native-guard-compatible ownership/absence resolution and fresh preview;
a separately reviewed contract change would be a separate implementation step.
This condition persists, so the approved continuation's fallback applies: finish
source publication and report activation pending.

No deployment checkout switch, workbench container recreation or host bridge
restart was attempted. The existing container
`36db1951a95dc1aee857151f6f3b3bef4b3f9cb495748b48bc2e9159d41559f3`
remains healthy, started `2026-10-18T04:55:04.32582897Z`. The bridge PID observed
was `45063`. The old revision remains installed, and its OpenAPI correctly lacks
the new batch routes. No new-schema clean-start UI or post-activation contract
qualification is claimed.

Read-only health/UI/runtime-capability requests returned 200 for localhost,
`https://plotloom.tail6040ad.ts.net` and the existing Mac HTTPS 8443 fallback.
Native bridge readiness is `ready`. These establish continued old-installation
availability, not new-feature activation. Exact checks:
`.local/batch-video/activation-held-health.json`.

No live provider calls, owner-story generation, synthetic human review facts or
creative material/video approvals occurred. Live provider smoke, owner-payload
performance, hosted CI completion and new-installation post-start checks remain
separate gaps. Manager owns independent published/installed verification and any
later safe-activation continuation; this worker did not archive itself or remove
its Relay route.

## Later bounded proof investigation

The [process-incarnation investigation](2026-10-18-process-incarnation-proof-investigation.md)
qualifies the earlier reuse diagnosis: timestamp/command inequality, unrecorded
session provenance and a later UTC ledger update do not provide conclusive
retrospective proof. No guard change or activation occurred. It also records the
subsequent hosted CI failure, superseding the in-progress snapshot above without
changing that historical evidence.

## Completed activation: October 18, 22:01 EDT

The manager completed same-installation activation at
`2026-10-19T02:01:05Z` (October 18, **22:01:05 EDT**). The deployment checkout
`/Users/wjmao/projects/HU/plotloom` is clean and detached at
`93441fc1a2e268959377bb2f18a642b54ce63c73`. This installed revision includes two
local follow-up commits; no further source publication or GitHub CI occurred.
The closeout writer verified the retained records and screenshot read-only;
the live deletion, activation and post-start checks were manager-owned.

### Exact incompatible-data removal

The manager permanently removed **最后一朵花3**, project
`a99d5422-61fd-4768-89f4-118e82bbed75`, at the exact home:

`/Users/wjmao/projects/HU/plotloom/.local/creator-walkthrough/outputs/20261018T011358571296Z__a99d5422-61fd-4768-89f4-118e82bbed75`

The old build's ordinary native `permanent-delete` route returned **HTTP 204**
after exact title/revision checks, an exclusive project lease, empty close/native
specialist blockers, 55 completed host receipts/manifests and no active queue or
validator. This supported idle-deletion path is distinct from explicit
abandonment/revocation; see [ADR 0190](../adr/0190-explicit-material-continuation-and-abandonment.md).
No guard was bypassed or weakened. No backup, migration, isolation, recovery copy
or manual erasure was introduced. The deletion is unrecoverable.

The old PID/group 90191 was already absent. Later historical numeric identities
80342 and 87175 belonged to macOS system services and were not signalled. Their
presence did not require changing the ordinary idle-deletion contract.

### Installation and usability checks

The manager stopped only the workbench through supported `manage.py stop`,
switched P to the exact revision above, reloaded only
`com.plotloom.creator-codex-bridge` with `launchctl kickstart -k`, and ran supported
`manage.py start`. The explicit bridge reload was needed because unchanged
`host_bridge.py`/plist hashing could otherwise retain already imported helper
modules. Docker rebuilt and force-recreated its container, then reported healthy.

- New container: `076a982f3ea7329f008cc337249b469cae6a847eceb683be17ed090b36441483`.
- New owned bridge PID: `1221`; authenticated bridge-health succeeded.
- Manager-observed `/healthz`: HTTP 200 at localhost:8841,
  `https://plotloom.tail6040ad.ts.net` and
  `https://wenjuns-macbook-pro.tail6040ad.ts.net:8443`.
- OpenAPI exposes eight batch routes: GET base/review and POST
  setup/draft/directions/start/control/confirm. Served `workbench.js`, the
  `CreatorWorkflowNavigation` chunk and both CSS assets match installed source bytes.
- Specialist settings/readiness and the existing enabled/default H3 backend
  configuration are readable. No provider request was dispatched.

The manager created one temporary blank project,
`14aa3c1f-af4c-4b31-8b35-bbac7fec2f62`, titled
**Activation smoke check — no generation**, saved its brief, navigated to
Storyboard and inspected the actual **批量制作视频** panel. The screenshot retains
the visible H3 setup controls and missing-storyboard prerequisite. This proves
installed UI availability, not a generated or approved batch. The temporary
project was then permanently deleted through the native route, HTTP 204.
Final project and pending-deletion catalogs are empty; the owner must start a
new compatible project. No story generation or creative approval occurred.

### Preserved authority and retained evidence

Before/after comparisons prove all five protected credential/settings files
unchanged in bytes, modes and owners, and **every host table hash unchanged**.
The ledger retains 79 attempts (78 completed, one UNKNOWN), zero queue/validator
rows and the original image slot for
`06e80972-9dde-41ff-be71-b477c1477465`. No remote uncertainty was cleared.
Every prior application table is unchanged except the removed project's creation
reservation (one row to zero); the new `video_batch_grants` table is empty.

Historical evidence was recorded under `.local/batch-video/`:

| File | Evidence |
| --- | --- |
| `activation-resume-before.json` | Pre-action revision, protected-file and table hashes |
| `activation-resume-after.json` | Installed revision and exact preservation comparisons |
| `activation-resume-delete-a99.log` | Exact incompatible-project deletion HTTP 204 |
| `activation-resume-stop.log` | Workbench-only stop |
| `activation-resume-start.log` | Docker build/recreation, healthy startup and bridge health |
| `activation-resume-batch-ui.png` | Actual new-build batch panel in the temporary blank project |
| `activation-resume-smoke-cleanup.log` | Temporary-project deletion HTTP 204 |

The before/after JSON SHA-256 values are respectively
`7fa61ca30a5a376c08473f93fe27ffc7d0ee96081db92137dcb95d9fcaef63db` and
`cc36c00b8ad745423f7e16eb79d0af7a88e849a54621fd2201d7806dfc1e4a47`.

Activation does not qualify the failed hosted suite. Latest ordinary run
[39182416805](https://github.com/Wenjun-Mao/plotloom/actions/runs/39182416805)
remains **failed**: 3,297 Python passed, one failed and one teardown error;
338 browser cases passed; wheel and installed-wheel smoke were skipped. The
paid-fixture cause remains unproven. No new full gate, hosted CI, provider smoke
or creative acceptance is claimed. GitHub CI preparation, dispatch and publication
remain held under the explicit-user-only gate; this closeout is documentation only.
