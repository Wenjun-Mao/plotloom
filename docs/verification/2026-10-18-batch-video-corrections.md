# Batch-video manager-review corrections, 2026-10-18

Status: correction checkpoint for manager review. Push, publication and activation
remain held. Product source: `20e3c65b`; later checkpoint documentation changes no
executable inputs. Retained checkout: `/Users/wjmao/.codex/worktrees/b30f/plotloom`,
`main`. Review baseline: `7b711a55`.

This completes the three demonstrated corrections and the bounded proof-test gap
within the approved roadmap step 5. It does not approve owner media or change
owner project data. ADRs 0192 and 0193 record the corrected contracts.

## Startup and run-index isolation

Failure: an inspection-discovered current-schema project with an invalid retained
autopilot policy hash passed cheap discovery, then failed full authority admission
before production lifespan yielded. Startup reconciled every open discovered
project without isolating `ProjectStorageCorruptionError`. Rebuilding the run
index also trusted cheap inspection instead of admitting the retained authority.

Evidence: `startup-isolation-native-reproduced.log` retains the actual pre-fix
lifespan failure. The native fixture keeps valid SQL/JSON/project identity and
changes only the disposable project's policy hash. Earlier fixture-construction
failures remain in the preceding reproduction logs; the corrected fixture uses
supported manual takeover before creating a text run.

Fix: the dispatcher handles known corruption at each project reconciliation and
index boundary. Run indexing explicitly requests read-only authority admission,
including closed projects, and publishes no partial routes from a rejected
project. Registry discovery and ordinary inspection remain cheap. The registry's
read admission argument preserves its default inspection behavior. No authority
validator is weakened and unexpected implementation exceptions still propagate.

Diagnostics: the rejected project remains in the inspection catalog; its ordinary
GET returns HTTP 422, `project_storage_error`, with `persisted autopilot authority
is invalid`. Startup logs the exact project ID and known authority diagnostic.
Its recovery plan is empty and its routes are excluded from the disposable run
index; the healthy project's routes and GET remain usable. The corrupt database
bytes remain unchanged. Open and closed variants and an unexpected-failure
propagation guard pass.

## Adopted prepared-job execution

Failure: A explicitly starts, prepares and links an unsubmitted job, then is
cancelled. B explicitly starts with that exact compatible job in `prepared` mode.
The current batch scope and installation grant admit B, but the shared native
claim's English-basis validator additionally requires original batch A to be
running. Both controller and manual submission therefore fail.

Evidence: `review-corrections-reproduced.log` retains both failing submission
paths. The native fixture verifies the exact sequence, rather than substituting
a manually endorsed job for the batch-origin job.

Fix: immutable English endorsement validation retains its original manifest,
directions, source and compiled-prompt checks. Execution state is checked by the
existing shared current-adopter scope and installation grant, at ordinary native
submission and claim boundaries. The retired dispatch-state option on the
endorsement validator is removed. A stays cancelled; its reviewed snapshot is
unchanged. This is not a manual-path exception or fabricated endorsement.

Both controller and manual paths submit exactly once under B. Not-started,
paused, cancelled, stale and missing-grant adopters submit nothing. An adopted
UNKNOWN outcome remains one attempt and cannot be resent.

## Foreground completion ownership

Failure: image completion intent contained only project/route identity. An external
run replacement, cancellation, takeover or staleness could leave A's foreground
intent armed until an unrelated later review state, causing focus/scroll. Five
pre-fix integration cases reproduce this in `completion-owner-reproduced.log`.

Fix: the workspace owns a run-bound preparation/handoff intent above the shared
viewport helper. Initial Start binds its new run from the command acknowledgment
without rearming the original intent. Polled withdrawal/replacement clears the
owner and the underlying intent. An invalidated command token cannot rearm on
late acknowledgment. Preparation and handoff purposes are separate, so an
awaiting-review poll does not consume a pending saved-confirmation reveal.
Navigation/hidden-tab invalidation remains with the shared helper. An uncertain
Start without a proved run identity does not invent completion ownership.

Six new integration cases cover initial Start's one reveal, external replacement,
cancellation/takeover/staleness and a delayed resume acknowledgment after external
replacement. The new browser case observes A being replaced by B and verifies
zero completion scrolls/focus, with one Start write. Existing lost/delayed handoff
acknowledgment, hidden-tab and playback refresh journeys remain passing.

## Retained proof coverage

No proof-cache production changes were needed. Dedicated real geometry and human
handoff cases fill successful proofs, mutate their retained SQL evidence and
require rejection, roll back and validate restored evidence, then change a
content-addressed file within the same proof scope. The ordinary requested-byte
reader independently hashes and rejects those changed bytes. New proof scopes
validate restored files again. This verifies the named SQL-mutation/rollback and
requested-byte boundaries; it does not turn a cached retained proof into a fresh
file-byte attestation or claim an undiscovered authority bypass was fixed.

## Executed verification and reuse

All logs below are under `.local/batch-video/` in the retained checkout.

| Selection/gate | Result | Evidence |
| --- | --- | --- |
| Focused startup, production runtime/boundaries, routing, deletion quarantine, inspection, batch/recovery/adoption, native video submission/dispatch | 59 passed | `correction-backend-regressions.log` |
| Expanded startup file: open/closed corruption and unexpected failure | 3 passed | `correction-startup-open-closed.log` |
| Real retained proof boundaries and existing SQL proof scope | 3 passed | `retained-proof-boundaries.log` |
| Completion ownership, shared reveal, material review unit regressions | 35 passed | `completion-owner-fixed.log` |
| Quick: unfiltered frontend unit suite plus application/E2E type checks | 1,415 passed, 162 files; both type checks passed | `correction-quick-final.log` |
| Browser: `e2e/autopilot-review.spec.ts`, `e2e/video-batch.spec.ts` | 23 passed | `correction-browser-final.log` |
| Verification module-ownership regression file | 7 passed | `correction-ownership.log` |
| Complete native case ownership preflight | Passed: 3,270 Python, 1,415 frontend, 336 browser cases; no bodies executed | `correction-native-ownership.log` |
| API F401 and diff whitespace checks | Passed | Executed directly |
| Deterministic asset build, twice | Seven files identical | `correction-build.log`, `correction-static-tree-final.json` |
| Wheel build and isolated installed-wheel smoke | Passed | `correction-wheel.log` |

The backend selection is exactly the eleven `--pytest` files printed in its log,
including every new adoption and startup case. The expanded startup run adds the
closed-project variant. Module `--show` reviewed story-authoring, media-lifecycle
and project-lifecycle contract selections (`correction-module-plan.log`); no
module-suite execution is claimed. The native ownership guard was run separately
and checks all current case IDs. Earlier E2E fixture type errors remain retained
in `correction-quick.log` and `correction-browser.log`; the final fixture uses a
DOM counter and passes both type checking and its browser assertion.

The seven-file tree uses SHA-256 per file and SHA-256 over sorted compact JSON:
`c3842ef6148b933187adab6c57e25fc13853b9c14a6af16b6b7d124d72ffb1a7`.
Checked `workbench.js` is refreshed. Browser screenshots are retained under
`correction-desktop/`, including 1280×460, 1280×768 and 1700×900 native batch
states. The delayed-handoff footer was visually inspected after the new run.
This correction changes ownership logic, not layout or copy.

The [initial qualification](2026-10-18-batch-video-production.md) remains retained,
including its full-run failure and exact rerun. A new full run is not claimed:
these changes alter per-project startup/index admission, the overconstrained
claim predicate and foreground completion ownership. Their exact affected
consumers were rerun above. Persistence schemas, request/response payloads,
prompts, provider payloads, accounting, dependencies and build tooling are
unchanged. Registry inspection's default is unchanged. Existing full evidence
for unaffected owners is reused; new assets and the installed package are rebuilt
and checked. The test-owner manifest and full native discovery are refreshed.
No release coverage is filtered or waived.

## Preserved gaps and stopping condition

No live provider/supervisor smoke, paid generation, owner-story generation or
creative approvals occurred. The prior controlled 42-shot measurements remain
fixture evidence for unchanged gallery/commit paths; they were not rerun or
relabelled as owner-payload measurements. Owner-payload performance, live smoke,
hosted CI and product/creative acceptance remain separate gaps.

The deployment checkout and owner old-schema 42-shot project are untouched. The
breaking schema/data-treatment issue from the initial checkpoint remains an
activation prerequisite. Manager independently retests these corrections before
publication/safe-activation continuation. The same worker chat remains available;
no push, restart, deletion or activation is authorized by this checkpoint report.

## Manager retest and delivery continuation

The manager's independent focused retest at `468b2d0e` passed 13 backend, eight
frontend and 23 browser cases, `VERIFY_SUMMARY exit_code=0`, in 97.703 seconds.
Exact retained log: `.local/batch-video/manager-correction-retest.log`. Selections:
`tests/test_project_startup_isolation.py`, `tests/test_video_batch_adoption.py`,
`tests/test_retained_proof_boundaries.py`, frontend
`tests/autopilot-completion-owner.test.ts`, `tests/completion-reveal.test.ts`, and
`e2e/video-batch.spec.ts`, `e2e/autopilot-review.spec.ts`. The manager reports both
independent correction reviewers closed their concrete findings with no remaining
release defect in this bounded scope. No unaffected full gates were repeated.

The manager then authorized normal publication and safe same-installation
activation, including scoped permanent removal of the two exactly identified
incompatible disposable development homes without backup/recovery. Native
revocation, fresh idle proof, credential/settings preservation and retained
UNKNOWN accounting remain required. The earlier hold above describes this
correction checkpoint, not the later delivery authorization. Final operational
evidence is recorded separately.
