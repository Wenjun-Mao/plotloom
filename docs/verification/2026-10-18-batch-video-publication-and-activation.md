# Batch-video publication and activation attempt, 2026-10-18

Status: source published; activation blocked by the existing native process-group
revocation guard. The old installation remains running and healthy. This is not
an activation, restart, provider-smoke or creative-acceptance receipt.

## Published source and independent evidence

Qualified product source is `20e3c65b`. The manager independently retested clean
`468b2d0e`: 13 backend, eight frontend and 23 browser cases passed, exit zero in
97.703 seconds. Exact retained log:
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
