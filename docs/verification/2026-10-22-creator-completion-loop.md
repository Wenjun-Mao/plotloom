# Creator completion loop: implementation and acceptance evidence

Status: bounded native UI journey completed on deployed `b78bc6c9`; final local
qualification failed at Python contracts. Corrective qualification remains open.
Generic checkpoint: `da1f9bc0`; capacity checkpoint: `f1a93485`.
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
At the generic checkpoint no full gate had run and native scope fields awaited
the actual bundle. Subsequent exact grant, live journey and failed final gate are
recorded below; no placeholder/wildcard grant was used.
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

## Completed bounded native UI journey

The manager completed the real UI journey on installed `b78bc6c9555bc3949a2a66c1bcfd04d81f723839`:
saved Brief → eight native text adoptions → three native references/two prepared
frames → attributed atomic material handoff → initial two-clip H3 batch → one
selective ending replacement → final whole-pack QA → story ending → Save and
Close → reopen → the same ending again. The smallest supported fixture uses one
nonhuman wooden toy robot, no dialogue/branching, and two three-second shots;
the native character contract required a nonempty cast, not an empty-cast bypass.

Final batch `5216df34-2caa-4542-b25f-9df81fc1d8ca` has two selected three-second
windows. Exactly three H3 submissions requested 15 source seconds: two initial
five-second sources and one new ending source. Opening job
`vj_6eddc5b7f1c4421aac765df247e8e2ef`, segment
`7fe2153b-b27a-43c2-b936-e48e42ae849e` and original/derivative bytes are unchanged;
the original ending remains retained and unselected. Replacement segment is
`4f93f842-2573-4c32-b896-6855e0b464e8`. No new UNKNOWN occurred.

The ending was rejected for an explicit creative QA variation, not a fabricated
technical fault. The manager reviewed/edited fresh English action and soundscape,
then explicitly started one new source. Both actual final preview videos played
three seconds to `ended=true` without media error. Final AV receipt
`35b4e43e-4acf-4ce7-b3ce-4e9cd87a5e8b`, confirmed at 16:25:53 UTC, records
`agent_operated_qa` / `creator-completion-native-20261022`, not the owner's review.
Story playback advanced from opening to replacement ending, held its last frame,
and repeated after UI save-close/reopen. See the retained
[journey notes](../../.local/creator-completion-20261022/ui-journey-notes.md),
[ending](../../.local/creator-completion-20261022/native-story-ending.png) and
[reopened ending](../../.local/creator-completion-20261022/native-reopened-ending.png).

Independent source-worker readback comparison confirms after-confirm/reopened
jobs, dispatches, selections, segments, reviews, receipts and batches are exactly
equal: three jobs/dispatches/segments, two selections, three reviews, one receipt.
Both historical UNKNOWN full-row hashes remain unchanged. Manager preservation
checks retain all three old examples and protected files; final snapshot has no
active host attempt, enabled queue entry or validator. Evidence:
`after-confirm-readback.json`, `reopened-readback.json` and
`before-final-activation.json` under the retained journey directory.

Interventions/limits: initial `reject_mismatch` setup violated the existing QA
`cover_center_crop` policy and was refused before jobs; UI cancel/reprepare fixed
operator setup without contract expansion or provider retry. The manager edited
draft soundscape to match the authored faint ambience. Technical waveform/spectrum,
decoding and playback inspection is not perceptual listening certification or
semantic proof of no speech/music. Close-up feet are outside the crop; exact
one-second remake timing was not established. This is functional delegated QA,
not creative perfection, human creative acceptance or general availability.
Operator-effort versus provider-wait totals were not continuously measured.

## One final full qualification: retained failure

On clean frozen `b78bc6c9`, the sole unfiltered command
`uv run --locked --no-sync python scripts/verify.py full` started 16:33:04 UTC and
failed at Python contracts after 1,208.514 seconds. All 3,701 native cases were
accounted: 3,603 passed, 21 failed, 77 setup errors. Worker reports remain intact;
no automatic full retry occurred. Dependency lock, ffmpeg/ffprobe, API import
guard, archived prompt reader, 1,473 frontend tests and frontend typecheck passed.
Deterministic bundle/parity, unfiltered browser and wheel/installed-wheel steps
were not reached, not skipped-as-pass.

Exact [log](../../.local/creator-completion-20261022/final-full-b78bc6c9.log)
SHA-256: `722abf8bd5e2237f0f2ecc36dc69fc94e02a9259d93661113b233477efddf5fe`.
[Fingerprints](../../.local/creator-completion-20261022/final-full-b78bc6c9-fingerprints.json)
retain source/dependency/host identity: input
`00a743e736cbf87c08018c2226e89a497525aa218de1283b5cf4dc20186c927b`,
native inventory `904e4ac52f88a7aac5697d1b04648e44d296291bdce0456ca8f4c4d73f02383e`;
macOS 27.0.1 arm64, Python 3.12.13, uv 0.13.1, Node 24.18.0, npm 11.16.0.
This Mac envelope is distinct from the deployed Linux container.

First causal report: the actual paid-outline operator composition validated
readiness but returned `None`; test/qualification shims also returned `None` from
the now-consumed typed readiness method, causing launch `local_capacity`
dereference failures, including repeated shared-fixture errors. Other failures
identify a precise receipt method/field collision: legacy v1's `attribution`
validator classmethod was read as actor data by `getattr`, rejecting retained
named-human receipts. Other failures were isolated view fixtures missing newly
queried timing tables and
remaining equality assertions comparing response-only `timing.observed_at`.
These failures remain failed; narrow corrections need separate evidence. No
integration edits or expensive reruns were made before reporting their causes.

## Prospective duplicate-reference host consistency repair

A separate prevention audit demonstrated an avoidable UNKNOWN path, not a cause
claim for this fixture or historical attempts. The host's post-generation matcher
required unique reference SHA values although native admission/delivery support
distinct ordered roles/paths with identical bytes. A smallest host-path test
first reproduced the refusal; its log is retained as
`duplicate-role-host-reproduction.log`. Remove only that extra hash-uniqueness
rule, retaining the complete ordered reference inventory and exact view evidence.
The synthetic real `_run` regression produces a completed receipt/manifest and
consumed image budget, while wrong path/view order stays UNKNOWN/reserved.
An initial expanded test fixture reused a view event ID for generation; the
strict parser correctly refused it. Distinct fixture event IDs fixed that test
setup; no production telemetry tolerance was added. Initial focused union passed
18 host/failure/publication/ingestion cases; a further 102 affected delivery,
receipt, runtime, telemetry and profile cases passed. This repair does not settle or retry
old UNKNOWN, change local caps, or claim that uncertainty can be eliminated.

## Corrective qualification in progress

The owner explicitly authorized the bounded UNKNOWN consistency repair and the
four diagnosed qualification corrections. Production remains strict: the real
paid-outline registry returns its already-validated typed readiness, matching
SpecialistRegistry; test shims do likewise. No `None` fallback is added. Receipt
parsing discriminates typed v1 before reading current observation actor fields;
eight schema-only tests preserve all four receipt roundtrips, v2/v3 QA-smuggling
refusal and exact v4 actor matching. Existing retained-v1 integration checks also
pin the validator-method collision and unchanged historical bytes/recovery.

The isolated view fixture now includes both timing tables and explicitly expects
the added adopted-decision select and its exact bind values. Parse/derivation,
failure priority and cache counts remain asserted. Nine view cases pass. The
durable-fact helper omits only `timing.observed_at`; creation/terminal/milestone,
run revision, all authority/material fields and exact retained rows stay compared.
The first corrected owning-file run exposed the old exact query-count expectations
and an additional duplicate HTTP response equality in text-retry; these are the
same response-projection test-contract issue, not a runtime fallback. Narrow
updated file checks are recorded separately from that intermediate run. Its
216-case selection ended 205 passed / 11 failed (518.92 seconds); the exact
remaining nine view cases passed in 0.13 seconds and two API retry cases passed
in 46.63 seconds. All 98 original failed/error IDs are selected, 87 passed in the
owning run and the other 11 passed those corrected whole-file reruns. No original
case is missing and no unexpected residual family remains. The ignored
[reconciliation](../../.local/creator-completion-20261022/qualification-failure-reconciliation.json)
and `corrected-full-families-focused.log` retain this composite accounting;
neither the original full nor intermediate failed run is rewritten as passing.

Native test ownership discovery initially refused five new Python files not yet
mapped by the existing manifest. Exact current module owners and the shared
duplicate-role helper dependency are now registered; frontend timing belongs to
shared presentation. No runner, tier or filter changed. Read-only native discovery
passed the final 3,713 Python cases / 306 files (inventory SHA-256
`2b1af69d5005b224643afbab371f5a7e5b0f207b67c37f64c45c1b4199435686`),
1,473 frontend cases / 167 files and 351 browser cases / 97 files, including the
eight new receipt-actor unit cases. The original
full gate remains failed. Corrective file checks and previously unrun downstream
gates form composite local qualification, never a rewritten full-pass claim.
