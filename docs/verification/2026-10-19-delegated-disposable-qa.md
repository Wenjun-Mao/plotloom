# Delegated disposable-QA source checkpoint

> Historical local artifacts in [the cleanup scope](../roadmap/2026-10-25-top-five-cleanup.md) were retired
> on 2026-10-25. References to those files are not available attachments or resumption
> instructions; recorded outcomes, limits and current project-owned media stand.

Scope: ADR 0198, exact project `326a5137-1851-4b5c-8ab2-b600ec7bda23`, board
`b4da9c96f5bfa09548446249960605e7a87671936d75e8fbec62ecef73043295`, two retained
ImageGen originals, existing quality-8 portrait H3 gateway, `cover_center_crop`,
at most two submissions / ten requested source seconds. The manager owns the
live six-second playback journey and actual visual/native-audio inspection.
The worker changes source only and performs no live review/provider/control calls.

## Root operator preflight

Use the actual workbench runtime's existing `ProjectFolderStorage` configuration
and original project home. The workbench runs in Docker; do not use host macOS
device/inode values to create a Linux-runtime grant. After verifying the exact
original fixture and no competing writer, root invokes once inside that runtime:

```python
from contextlib import closing
from plotloom.project_storage.delegated_qa_grants import bind_original_qa_scope

with closing(storage.projects.open("326a5137-1851-4b5c-8ab2-b600ec7bda23")) as store:
    bind_original_qa_scope(store, storage.application)
```

Here `storage` means the runtime's owning storage with its actual outputs and
application roots, not a new default installation. This trusted operator helper
checks the frozen board and original hashes and records an immutable runtime
scope binding in the existing app grant store. It creates no project tables,
reviews, selections, jobs or provider calls. A missing/mismatched grant refuses
QA writes and dispatch. Never rebind a restored or copied home to evade refusal.

## Root API payloads

Every QA actor is exactly:

```json
{"kind":"agent_operated_qa","scopeId":"disposable-qa-20261019"}
```

1. `POST /api/v2/projects/{project}/storyboard-approval` retains existing
   `expectedRevision`, `contentHash`, `decision:"approve"`,
   `gateSetVersion:"storyboard.v2"`, with the QA object in `attribution`.
   The manager has already inspected the board and originals; source code does
   not fabricate those observations or a human handoff.
2. For each original, `PUT .../authoring-drafts` with
   `editorScope:"visual_intent"`, `entityId:"{shotId}:{assetId}"`, current
   `baseCanonicalRevision`, exact `expectedDraftRevision`, and payload containing
   `assetId`, `shotId`, `role:"shot_keyframe"`, the manager's actual authored
   composition/style observations, nonempty `sourceRefs`, and QA `attribution`.
   `POST .../managed-assets/{assetId}/visual-intents` uses the same payload minus
   `assetId`, plus exact `consumedDraft:{editorScope,entityId,draftRevision}`.
3. `POST .../reviewed-keyframes` retains exact asset/shot/scene, storyboard,
   approval, visual-intent and selection revisions, actual `compatibilityNote`,
   current presentation revision, and QA `attribution`. Read back workbench
   `reviewedKeyframes[].attribution` and immutable intent observations.
4. Existing batch setup uses
   `profileId:"minimax_h3_quality8_portrait_576x1024_v2"`,
   `aspectPolicy:"cover_center_crop"`, `maxJobs:2`, `maxRequestedSeconds:10`.
   Draft/edit the exact English sources normally. Existing Start body adds QA
   `attribution` alongside exact `expectedRevision`, `manifestHash`, and
   `basis:"whole-batch-english.v1"`. No Start is inferred from draft completion.
5. After actually viewing every proposal and reviewing its native audio, existing
   batch confirmation adds QA `attribution` and the following **completed actual
   inspection**, alongside current `expectedRevision`, `reviewHash`, and
   `basis:"whole-pack-video-native-audio.v1"`:

```json
{
  "inspection": {
    "clips": true,
    "nativeAudio": true,
    "intent": true,
    "windows": true,
    "visualObservation": "<actual observations of the exact clips and windows>",
    "audioObservation": "<actual observations of the exact native audio>",
    "evidenceRefs": ["<retained inspection evidence references>"]
  }
}
```

Do not send placeholder observations or treat authorization as proof of listening.
Final confirmation remains atomic and source/rejection/hash/CAS/byte-bound. A QA
rejection uses existing `POST .../video-jobs/{job}/review` with QA `attribution`,
`decision:"reject"`, actual nonblank `note` and exact selection revision; omit
`reviewer`. It blocks pack selection. Rejection does not authorize another call.

Readback exposes QA on storyboard decisions, material bindings, batch
`execution.reviewAttribution`, final receipt `attribution`/`inspection`, job
review history and selected `playbackSegment.attribution`. The UI labels it
“代理 QA 审阅（经用户授权）” on review history and story playback. Human named and
unnamed decisions remain distinct. Portable snapshots retain these facts; no
runtime dispatch grant is exported with them.

## Verification and remaining gates

Focused checks cover ordinary-project refusal, reserved reviewer forgery,
agent/human distinctions, exact material draft consumption, scope expansion,
copied-home refusal, UNKNOWN, cumulative claims, rejection, native AV receipt,
selected playback and snapshot admission. Tests use a typed synthetic six-shot
scope over existing fixtures; the production scope stays exactly two / ten.
No live observations or provider outcomes are claimed by those tests.

Final stable source is based on `fdc45ea`; delivery reports its local commit.
Executed focused backend selectors:

```text
tests/test_delegated_qa.py
tests/test_storyboard_creator_confirmation.py
tests/test_video_batch.py
tests/test_video_batch_review.py
tests/test_video_batch_recovery.py
tests/test_video_batch_adoption.py
tests/test_project_storage_image_workflow.py
tests/test_project_storage_video_review.py
```

The stable `verify.py focused` union passes **60 Python cases** in 68.89s
(runner 72.170s), plus **29 frontend cases** across
`delegated-qa-attribution`, `storyboard-creator-confirmation`,
`video-pilot-playback` and `video-pilot-review` (runner 1.039s).
Whole focused runner: **80.476s**. Retained local log:
`.local/batch-video/delegated-qa-final-focused.log`.

Earlier `quick` passes **1,425 frontend cases**, both type checks, API unused
imports and locked dependencies in 13.576s. The later third QA UI case passes
in the final focused union; final frontend type check also passes. Native module
ownership discovery passes for the final registered 3,414 Python / 1,426 frontend /
338 browser case census; discovery executed no test bodies.

Affected browser selection `video-batch.spec.ts` and
`branching-video-preview.spec.ts` passes **4 journeys**, runner 120.781s, including
native branch playback, reload, atomic confirmation, restart/pause and unrelated
dirty-edit preservation. A final batch-only rerun passes **3 journeys** (64.358s)
and refreshes desktop pixel evidence
after the QA-specific status wording; final QA label behavior also has explicit
frontend cases. Actual live QA media/acceptance remains unclaimed.

Two final deterministic builds produce the same seven-file SHA-256 tree:
`.local/batch-video/delegated-qa-assets.json`. Final `workbench.js` SHA-256:
`b95253f02eb61e4e6452579fe342f9ff97e95415d20618129d624ffece0f103d`.
Wheel build and installed-wheel smoke pass; the five new QA modules match source
bytes inside the wheel. Wheel SHA-256:
`64a5d20dd72317ed9e5b6067b83b3f9b98ac3c49608b81c842cab773305a3138`.
New-module/test Ruff checks and `git diff --check` pass.

Independent static review identified the human-only reopen hole and missing test
ownership. Both are corrected, with original/copy review-state preservation and
ownership evidence. The reviewer confirms no remaining findings after those
fixes, the exact-approval image reader correction, optional-direction observer
and QA-specific UI status. No independent live calls or test executions occurred.

A final producer/reader consistency check found ordinary per-shot preparation
could save QA material with human-only English attribution and make subsequent
admission fail. Preparation now refuses that combination before fingerprinting,
idempotent return or insertion, while prompt previews remain read-only. The new
API refusal regression, positive QA AV journey, ordinary batch cases and existing
video-review cases pass **8 focused checks** (13.308s). Independent static review
also reports no findings in this correction. The earlier 60-case union remains
retained evidence; this last preparation change is qualified by that affected
eight-case selection, not described as another full-union run.

The first broader focused run retained one image-adaptation failure: its narrowed
`ImageAuthorityBinding` intentionally has no reviewer field. Attribution now reads
the exact retained approval row, preserving the normal currentness owner; the
failed and affected checks pass in the final union. The initial QA checks also
found missing selection forwarding, alias canonicalization and the explicit empty
ending-frame shape. These were corrected at their contract owners before final
qualification. No assertions, dispatch safety or required coverage were weakened.

Source/review/coordination timing was not separately instrumented; only check
wall times above are measured. At this earlier QA-contract checkpoint, no
infrastructure repair, live provider generation, live review writes, activation,
full suite, hosted CI or push had occurred here. The October 19 closeout below
supersedes that checkpoint's activation and qualification status; CI/push remain
held.

## Frozen planned-count wording correction

The manager's live pause after one submitted job exposed a presentation mismatch:
`manifest.newJobs` is the frozen planned inventory, but the panel described it as
pending dispatch. The label now reads `计划新作业 {n} 项`. No counters, reads,
backend contracts, provider behavior or budgets change; prior backend evidence
is retained. Running/paused component regressions include an already submitted
job and preserve the existing progress display and single current-batch read.

`verify.py focused --vitest tests/delegated-qa-attribution.test.ts` passes all
five cases (0.820s); frontend type checking and `git diff --check` pass. Two
deterministic builds match across seven files, recorded in
`.local/batch-video/planned-count-assets.json`. New `workbench.js` SHA-256:
`72d87c325fc2f0ae3a5bcac06ecd6cec08fa51b3d93bc990abea7767d3dbd826`.
Independent read-only review reports no findings in the source/test diff. This
is a scoped presentation checkpoint, not a new release qualification. No full
suite, package sweep, live/provider actions, activation, queues, CI or push ran.

## October 19 correction, composite qualification, and activation closeout

Executable source is committed on local `main` at
`14e7bce5798cef2779b5232098f94311974a2710`, after
`446db168cdbf7866f384e87048c955e3a0c0c622`. The checkout is clean and unpushed.
An independent stable review found no correctness or security findings in the
correction. The exact-prior validator now receives an explicit
`prior_without_video_batches` capability only after the frozen schema is checked;
all ordinary QA, approval, intent, material, job and review checks remain active.
Current-schema admission still rejects a missing `v2_video_batches` table. ADR
0190 records this boundary.

The local result is composite scoped evidence, not a passing full gate:

- The one authorized full run at `bb65510af17b7d9943f8a08969e26f0d7c91b8a8`
  remains failed: 3,412 Python passed and two failed; 1,428 frontend cases and
  the earlier type/early gates passed. Its failures were the retained-runtime
  inventory freshness assertion and ordinary retained-video diagnostic owner.
  Both corrected areas passed their affected focused checks; the full run was not
  repeated.
- On `446db168`, deterministic production build, checked static parity, and
  unfiltered browser-shard coverage passed (95 specs, 338 cases, no gaps or
  overlap). The unfiltered browser suite then failed: 335 passed and three
  failed in 554.812 seconds. Two prior-layout abandonment journeys exposed the
  new QA observer's unconditional query of a table absent from the exact frozen
  schema. The third test expected an approval button after its fixture had
  already approved the storyboard. The first two failures were fixed at the
  exact-prior admission boundary; only the stale test control assertion changed.
  The original run's outcome remains documented here; the 338-case suite was
  not rerun.
- The approved four-file focused Python union passed 113 tests in 67.79 seconds
  (runner 76.077 seconds). The delegated-QA file was rerun after an import-only
  formatting change: 44 passed in 30.64 seconds (runner 34.068 seconds).
- The two approved Playwright files passed all 13 tests in 64.724 seconds,
  including the three previously failing journeys. Their run also passed
  `typecheck:e2e`. This focused result does not replace the failed unfiltered
  browser-suite result.
- The final candidate's wheel build and installed-wheel smoke passed in 4.493
  seconds. The retained wheel is 1,528,200 bytes with SHA-256
  `a00510f7514005b0ccb3605ef65d8626e29ded24cb5cb283e07e7783577bb957`.
  `uv build` warned that host uv 0.13.1 is outside the configured `uv-build`
  requirement range; both package commands exited successfully.

The final candidate was activated by the manager on the existing installation.
The app stopped/switched/restarted through supported operations, and the new
container was healthy with the unchanged served bundle `72d87c…`. The original
runtime QA grant remained bound to the same installation; it was not rebound.
The approved batch stayed at revision 16 with the same two selected jobs,
predictions, typed QA actors and derivative hashes. A browser reload followed by
deliberate playback advanced from the first clip at 0.186508 seconds with
`paused=false` to the second clip at 3 seconds with `ended=true` and
`readyState=4`; playback stopped on its final frame without a media error.

Both playback downloads match the selected derivative hashes. The five protected
files still match baseline; the historical UNKNOWN row hash and both UNKNOWN
exit-null outcomes are unchanged. Native totals remain 101 completed, two
UNKNOWN, 16 queued and one settled, with zero enabled queues or validators. The
owner story and native QA remain paused at revisions 128 and 56 respectively;
the only operational delta was one application-start claim. During this final
activation/playback recheck there were no new generations, reviews, provider
calls, CI runs or pushes.

The bounded provider journey used the disposable project
`326a5137-1851-4b5c-8ab2-b600ec7bda23`, within its two-submission / ten-requested-
source-second grant. Both imported-frame H3 outputs were ingested and atomically
selected by the typed delegated QA receipt. Root inspected all 72 frames in each
of the two proposals (144 frames total) and decoded/analyzed the native AAC
signal; no listening or perceptual audio certification is claimed. Imported
ImageGen frames through H3 to browser playback is established technical E2E.
Native automatic-image E2E remains separate and UNKNOWN is untouched; owner
creative acceptance remains separate.

Retained evidence and complete logs:

- Original full outcome, fingerprints and log:
  `.local/batch-video/final-full-bb65510a-outcome.json`,
  `.local/batch-video/final-full-bb65510a-fingerprints.json`,
  `.local/batch-video/final-local-full-bb65510a.log`.
- Initial suffix fingerprints and log:
  `.local/batch-video/suffix-446db168-inputs.json`,
  `.local/batch-video/suffix-446db168.log`.
- Focused logs:
  `.local/batch-video/causal-fix-focused-python-446db168.log`,
  `.local/batch-video/causal-fix-focused-browser-446db168.log`,
  `.local/batch-video/causal-fix-final-qa-focused-446db168.log`.
- Final packaging fingerprint, complete log, result and wheel:
  `.local/batch-video/wheel-suffix-14e7bce5-inputs.json`,
  `.local/batch-video/wheel-suffix-14e7bce5.log`,
  `.local/batch-video/wheel-suffix-14e7bce5-result.json`,
  `.local/batch-video/wheel-suffix-14e7bce5/plotloom-0.1.0-py3-none-any.whl`.
- Final root-owned activation and playback evidence:
  `.local/batch-video/delegated-qa-final-activation-14e7bce5.json`,
  `.local/batch-video/delegated-qa-final-av-inspection.json`,
  `.local/batch-video/delegated-qa-final-confirmation.json`,
  `.local/batch-video/delegated-qa-playback-closeout.json`,
  `.local/batch-video/live-delegated-qa-story-complete-14e7bce5.png`.

`git diff --check` and targeted Ruff checks passed. The Ruff command excluded
`I001` and `RUF059`, which were confirmed in the baseline files; no other
targeted Ruff findings remained. No second full run, unfiltered browser rerun,
hosted CI, push or product acceptance is claimed. Product/infrastructure/
coordination time and cost were not separately measured; only the runner times
above are retained. Older checkpoint statements in this file describe their
original dates and are superseded only where this closeout states newer evidence.
