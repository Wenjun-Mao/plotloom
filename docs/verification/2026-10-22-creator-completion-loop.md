# Creator completion loop: implementation and acceptance evidence

Status: generic checkpoint `da1f9bc0` plus reviewed capacity-recovery candidate;
live acceptance and final local
qualification remain manager-owned and are not complete in this record.
Baseline: retained checkout `1edae591`; approved scope is the
[creator completion plan](../roadmap/2026-10-22-creator-completion-loop.md).

## Implemented contract

- Distinct exact native-material QA grant freezes run, bundle/closure, complete
  reference decision/original identities and shot/frame originals. Atomic bulk
  handoff v4 carries typed actor through approval, intent, bindings, identity
  observations and portable receipt validation. Existing grants stay intact.
- Read-only project QA context distinguishes ordinary creators, verified eligible
  QA and known QA whose grant/current material is unavailable. Browser opt-in is
  explicit, project-local and resets on navigation; unavailable QA blocks writes.
  Every native write independently verifies its actual actor and original runtime.
- Gallery rejection records a reason without dispatch; exact predecessor cancel
  and successor preparation remain separate native operations. Recovery reads
  persisted state and recognizes explicit successor lineage. Good siblings and
  rejection history remain intact; new directions and Start stay explicit.
  Rejection reasons remain visible when preparing the successor.
- Timing is response-only, uses explicit UTC creation/observation and immutable
  adoption/handoff/AV-receipt facts, and shares the effective run state with the
  status response. Image preparation authorization is not adoption. Browser ticks
  use a monotonic clock; failed reads and terminal dates remain labelled honestly.

## Focused software evidence

Commands use the repository's locked environment, not hosted CI or live providers.

| Check | Outcome |
| --- | --- |
| `verify.py focused --pytest tests/test_bulk_material_handoff.py --pytest tests/test_delegated_qa.py` | 64 passed; existing human/manual-QA safety |
| Native-material QA, replacement and timing focused union | 32 passed before final review deltas; existing replacement 23 cases unchanged by later timing/context fixes |
| `tests/test_native_material_qa.py` after QA-context fixes | 9 passed; exact bundle, explicit actor, portable copy, changed pre/post-handoff closure |
| `tests/test_workflow_timing.py` after review fixes | 4 passed; immutable creation/GETs, explicit UTC, image authorization excluded, effective stale terminal |
| Focused material/autopilot/timing frontend checks | Pass; full quick below includes final versions |
| `verify.py quick` | Pass: 167 frontend files / 1,473 tests, API unused imports, dependency lock, frontend and browser-fixture type checks |
| Affected `frontend/e2e/video-batch.spec.ts` | Final 8 cases passed in 144.56 seconds, including cancel failure, cancel lost response, successor lost response and unavailable-QA refusal |
| Known-QA-unavailable browser case | Passed separately; no Start or job creation |
| `npm --prefix frontend run build:deterministic` twice | Identical seven-file SHA-256 trees; current `workbench.js` SHA-256 `4e509e09dd8c93c178c3070a2b26546af5364e9a7fba974d1c894b4d887d7fa8` |

The browser fixtures use synthetic provider media. They establish native UI,
persistence and failure-boundary behavior, not the live ImageGen/H3 journey.
Desktop 1280×768 pixel inspection confirmed readable successor rejection reasons,
truthful batch timing and the final saved confirmation controls without clipping.
Retained ignored screenshots are under `frontend/test-results/`:
`video-batch-selective-repl-54920-or-cancelling-its-successor/selective-cancel-response-lost-1280.png`,
`video-batch-selective-repl-fee50-or-cancelling-its-successor/selective-successor-response-lost-1280.png`,
and `video-batch-native-batch-s-d03d3-atomic-audiovisual-decision/batch-saved-1280x768.png`.

## Retained failures and diagnosed corrections

- The first new attributed native handoff failed at same-person review because
  its existing human reviewer encoder called `.strip()` on a typed QA actor.
  The identity write owner now admits typed QA only inside exact atomic bulk
  handoff and preserves its actor in readback. Native handoff/portable tests pass.
- Independent review found that unavailable QA was displayed as ordinary creator
  context, and that discovery omitted exact native material currentness. The
  context now distinguishes required-but-unavailable QA and uses existing native
  bundle/handoff readers; server refusal and browser blocking both have guards.
- Review found IMAGE authorization could be labelled as adoption and stale-view
  timing could keep ticking from persisted running state. Projection now selects
  only genuine adoption and shares one effective state; focused regressions pass.
- The first effective-stale regression used `manual_command`, which correctly
  changed the persisted run to `taken_over`. Its fixture now deliberately creates
  an external closure mismatch through the low-level test transaction, preserving
  the intended running-versus-effective-stale condition. No product workaround.
- Two frontend assertions retained old wording after truthful QA/status and batch
  handoff copy changes. Ordinary human uncertainty wording remains unchanged;
  the expected navigation copy now says video production, covering the batch path.
- Two focused selector invocations were refused before tests because Playwright
  selectors lacked the existing `e2e/` file path or used unsupported line suffixes.
  Correct whole-file selectors and one direct native `--grep` run were used.

Known tooling messages: jsdom reports its existing unimplemented `scrollBy` in
passing unit checks; Vite reports its existing large-chunk advisory. Neither is a
new product failure. An extra non-gate targeted Ruff check also found the existing
unused `ImageJobCandidateRow` import in the touched identity module; the native
API-import gate passes. No lint rule or assertion was suppressed.

## Boundaries and remaining evidence

No provider submissions, original-runtime grant binding, installation, activation,
owner-story edits, GitHub Actions or push were performed by this source worker.
No new full gate has run. Exact live native scope fields arrive only after the
manager's original native bundle exists; there is no placeholder/wildcard grant.
Both native image slots were held by historical UNKNOWN attempts on deleted,
permanently revoked projects, so the initial native images could not start.
The exact read-only observation is retained in the
[native image capacity note](../../.local/creator-completion-20261022/native-image-capacity-observation.md).
The owner explicitly authorized the bounded recovery below. No live retirement
has been performed by this worker; UNKNOWN outcomes and reservations are intact.
The manager owns actual material inspection, the two-take/one-replacement UI loop,
native-audio limitations, ending playback/reopen, preservation checks, final full
local qualification and exact tested-package activation. Synthetic checks and
independent code review do not establish those outcomes or creative acceptance.

## Authorized local-capacity extension

Root cause: local process occupancy and remote outcome/spending uncertainty shared
one lifetime. Existing abandonment intentionally retained UNKNOWN slots, but the
two deleted/revoked historical attempts could never progress and prevented new
images. This is not an authentication or ImageGen retry problem. The supported
fix splits only local occupancy through one explicit, exact operator operation;
it never certifies the remote outcome or releases spending reservations.

The candidate adds typed authenticated CLI/bridge preview and commit, fresh
positive original-home/worker/CLI/separate-validator absence, exact installation
and retained-row CAS under publication fence, and atomic immutable recovery
receipt plus exact slot deletion. Missing/reused/permission/spawn uncertainty
refuses; exact lost-ack/restart readback is idempotent, restored slots refuse.
All original UNKNOWN/status/process/session/budget/receipt bytes, revocation and
disabled queue remain. No automatic retirement, dispatch, retry, cap increase,
new namespace or no-dispatch-parser change. The
[operator guide](../../services/creator_workbench/codex-exec-capacity-recovery.md)
provides the precise supported container CLI preview/consent commands.

Read-only readiness now reports actual persisted local limits/holds separately
from login/runtime health. Only image capacity exhausted exclusively by revoked
UNKNOWN holds refuses fresh material launch before any text dispatch. Ordinary
busy/running/unrevoked-UNKNOWN/queued behavior remains unchanged. Independent
review found one readiness regression: an unavailable auth/runtime response tried
to construct a supervisor. The readiness owner now returns the original typed
unavailable diagnostic first; auth-home/runtime cases guard this boundary.

Historical evidence is deliberately limited:

- `06e80972…`: 25,133-byte stdout, empty stderr and a reported pinned-skill sandbox
  denial are observed. No `turn.completed` or recorded process exit code exists;
  exact terminal cause and no-ImageGen/no-dispatch are not proven.
- `3405616d…`: the agent refused the sunflower-overlay versus empty-S01 content
  conflict before ImageGen in its final text; `turn.completed` and genuine exit 0
  were retained. The historical raw `rg`/unbound configuration census cannot
  certify no dispatch, so the attempt remains UNKNOWN.

The separate [instruction-access](2026-10-18-image-instruction-recovery.md) and
[content-ownership](2026-10-19-automatic-image-content-ownership.md) repairs were
already installed. Local retirement does not rewrite their historical evidence.

The manager completed all eight text adoptions in the current fixture, cancelled
the old run through the UI, and obtained native `not_started` evidence for its
three never-spawned images. Continuation preview is eligible. New source changes
frozen executor identity: quiet activation and explicit same-project Continue
must freeze fresh authority and inherit completed text through exact origins,
not rebind/replay the cancelled run. Exact successor QA scope waits for actual
native materials. Live recovery, native UI completion and activation remain
manager-owned and unproven here.

Capacity checks use synthetic host/process facts, not live process proof. Earlier
focused capacity/pool/abandonment union passed 52 cases; source bridge passed 36.
Final focused union passed 90 cases in 63.93 seconds: all 32 capacity cases plus
transport, authentication, profile, continuation, installed-text seed and review
readiness. The transport/pool/abandonment/auth-launch union then passed 40 cases in
7.58 seconds, including the four unavailable readiness cases and both unauthenticated
launch states. Independent bounded review and exact-fix re-review report no
remaining actionable finding. Targeted new-module Ruff and `git diff --check`
pass. Frontend bytes are unchanged from the deterministic generic checkpoint.
The post-capacity `verify.py quick` also passed in 13.48 seconds: dependency lock,
API import guard, 167 frontend files / 1,473 tests and both TypeScript checks.
Follow-on continuation/seed checks exposed test equality over response-only
`timing.observed_at`: the test helper excludes only this observation field while
retaining all durable timing/authority facts. Initial reruns retained three then
two missed equality assertions; no production currentness rule was relaxed.
One attempted focused selector used nonexistent pool/abandonment filenames and
was refused before execution; established actual selectors were then used.

## Native successor and exact source grant

Manager-reported live evidence: `f1a93485` was activated; explicit supported CLI
retirements returned receipts `d7e5c374-bd43-401b-bc56-80202336a5e7` and
`f352d7f5-1ca7-4e5d-a133-7d830374500f`. Exact readback retained those receipts;
the complete `exec_attempts` table hash stayed unchanged. Only slots and the new
receipt table changed. Readiness reported zero held images and two retired UNKNOWN
holds, unchanged limits, and no automatic dispatch. Credentials/application state
and the three finished examples were preserved. The first activation's native
launchctl bootstrap returned 5; after positive service/listener absence and valid
plist checks, the exact native bootstrap succeeded. The immediate failure's cause
is unproven, not a repaired product defect.

Visible same-project Continue inherited 12 adopted operations and retained all
eight text stages. Successor `faa941da-f566-4b8c-8b79-758664a8d060` completed all
five native images and reached `awaiting_review`, revision 38. The manager
inspected three genuine references and two prepared shot frames for delegated
technical QA, not owner creative acceptance. The ending close-up does not prove
feet continuity outside its crop.

The exact `NativeMaterialQaScope` now freezes project
`6e70451f-e9fd-4460-a475-bce50fde6503`, that successor, board
`017604f92aa0d0da9584c4016a7fa525c8841652767e4899d9cf135613594c3b`,
closure `cb0f5586bd2c3697b163c781992074622adb3e19762fea88d4942640f471286d`,
ordered reference decisions/originals and shot-frame originals, existing H3
profile and prospective null budgets. Prior four grants are unchanged.
The retained raw [review artifact](../../.local/creator-completion-20261022/native-material-review-raw.json)
was read without JavaScript normalization. Python stable hashing reproduces its
review hash `8d3859e258c5c98d0240138d2f0fa0b042547a402ba222ec15606f16f088ad0d`;
`require_native_bundle` matches every granted fact. The full immutable scope
digest is `aec7a5acc8ed3ea81eca3a3e3a01a321a51d9ea29332452aa19c00b96a6ab1a1`.

The observer's automatic bundle hash `8adb4c65…` covers
`pre-video.material.v1`; handoff's current review covers
`pre-video.human-review.v2`, including saved intent/story/current closure.
They are deliberately distinct owner projections, not evidence of a faulty
hash. A regression requires both self-hashes to match their own bundle, refuses
the automatic hash for native QA handoff, then accepts the exact current review.
No hash normalization, pin/currentness bypass or historical material rewrite was
introduced. Source registration does not bind a runtime grant or dispatch work.
The source worker still performed no live mutations or provider submissions.

Independent exact-grant review recomputed every ordered reference/frame and
review hash from the raw artifact, checked geometry project/output links and the
scope digest, and compared the prior four grant ASTs unchanged: no actionable
finding. `git diff --check` and targeted F401 checks pass. An optional broader
Ruff check reports pre-existing import-order advisories in these modules (also
reproduced from the committed baseline); no lint rule was suppressed. The latest
quick and deterministic frontend evidence is reused: this delta changes only one
closed source grant, focused tests and documentation, not frontend assets,
dependencies, hash owners, persistence or API request contracts.

Exact-grant focused verification passed: `verify.py focused --pytest
tests/test_native_material_qa.py --pytest tests/test_finished_example_qa_scopes.py
--pytest tests/test_delegated_qa.py`, 73 passed in 81.31 seconds. This includes the
new full-field grant pin and automatic-versus-current-review hash refusal,
currentness/actor/runtime/portable guards, original finite grant and all three
existing examples. No new test failed in this exact-grant checkpoint. The usual
Starlette/httpx deprecation advisory remains non-failing. No broader/full gate,
activation, binding or provider action was performed by this source worker.
