# H3 caption reliability across a larger scene panel

## Current status

Updated: 2026-11-09. Owner: root/current coordinator, sole source writer on the
retained Plotloom checkout. Baseline: `fedc08ae59d049e1deac204b15de63f07040a8e4`;
unrelated README/story changes remain untouched. **Planning only; execution is
not authorized by this plan.** The owner agreed the six-clip sample was too small
and selected **15 percentage points** as the improvement worth serious
consideration, assuming speech and scene fidelity do not worsen. The completed
[pilot report](2026-11-09-cross-framework-results.md) remains immutable evidence.

Intended result: determine whether the configuration package or whole framework
path improves first-attempt caption-qualified output on a defined, broader
current-story challenge panel, with enough evidence to distinguish a useful
signal from the pilot's chance result. Deliver the actual effect, uncertainty,
quality tradeoffs and operational cost, including an inconclusive or unfavorable
answer. This does not promise a caption remedy, a framework winner or migration.
Next: hand off this reviewed plan; no planning blocker remains. Execution is
awaiting the owner's later instruction. Start no fresh generation or service
changes as part of this planning assignment.

## Acceptance

| Claim | Required evidence | Fresh media | Status |
| --- | --- | --- | --- |
| Larger sample addresses the chosen question | Frozen panel/distribution, independent fresh seed blocks, 15 pp target, fixed analysis and stopping rules | No | Designed below; selection/seed manifest freezes during authorized preparation |
| Every arm consumes the intended source | Full final-request/graph comparison for every fixture; original and prepared pixel pins, reference order and guide/frame contracts | Only for uncovered native paths | Pilot envelope reusable; varying shapes/ref counts need bounded qualification |
| Quality observations are comparable | Blinded frame-complete caption review, unhinted qualified audio, source-specific action scoring, fixed uncertainty rules | Yes | Retained-media readiness before campaign; no full usability claim from an unqualified checker |
| Comparisons have adequate scale | 272 paired blocks, 816 planned clips; all original first outcomes and failures; paired effects/intervals and subgroup sensitivity | Yes | Approximately 89% caption power in the specified demanding sensitivity case; not a guarantee |
| Answer informs the next decision | A→B and B→C findings, 15 pp interpretation, joint-quality guard and honest limits | Yes | Awaiting execution; no automatic adoption |
| Existing work and resources are protected | Fresh quiet windows, due-expiry preservation, before/after reconciliation, same-runtime restoration, idle/resource proof and verified evidence bundle | No extra quality sample | Required for each maintenance block and final closeout |

## Settled scope and technical choices

Keep the pilot's three arms and exact logical model/source versions rather than
mixing a version upgrade into the replication:

- A: current Comfy INT8 ConvRot DiT, NVFP4 Qwen and native RES20 reference path
  (Quality8/base20, no Turbo/LoRA).
- B: Comfy BF16 logical DiT/Qwen, Euler20, video/audio shifts12/3.
- C: vLLM-Omni BF16 logical weights, its own complete native path and Euler20.

A→B concerns the configuration package. B→C concerns whole native paths, including
already declared posterior, normalization, encoder, ingress/egress precision and
model-time differences. Reuse `qualification-contract-v3.json` and the executed
adapter snapshots in the pilot's private bundle. Do not describe B/C as identical
effective inputs/arithmetic or identify a kernel/training cause from this study.
Each arm owns its encoder and media preparation; only common raw fixtures and
B/C external noise controls are shared. SGLang/LightX2V/Diffusers are not new arms.

The owner chose output quality per attempt over throughput, original native
speech, no picture repair and no caption-driven seed search. The panel, sample
count and statistical implementation below are planner choices supporting that
direction. No provider spending ceiling or time cap is inferred from them.

## Panel and sampling

The current story has 70 segments but **17 narrative scene instances**, identified
by `(episode, sceneIndex)`, in **one story and two physical settings**. E01 has one
scene/21 segments; E02 has two/22; E03 has fourteen/27. They are not 70 independent
scenes or 17 independent environments. The estimand is this deliberately selected
current-story challenge mixture, not all H3 output or unseen stories/settings.

Current `confirmedPositives` contains 13 caption events across **8 segment IDs**
in five narrative scenes. Absence from that index means no indexed positive,
not demonstrated clean output. A read-only inventory found 142 local attempt
packets and 513 ordered reference entries with matching retained hashes; final
fixture preparation still revalidates the selected bytes. Remote receipt paths
are not proof their files still exist.

Use all 17 scene instances. These source-backed candidate fixtures retain varied
speakers, face coverings, phone speech, voiceover, dialogue lengths and cut counts:

| Scene instance | Candidate segment(s) | Source coverage |
| --- | --- | --- |
| E01/1 | E01-13, E01-08 | Longer female speech; multi-speaker cuts; caption history |
| E02/1 | E02-09, E02-10 | Masked male speech and longer dialogue; caption history |
| E02/2 | E02-21 | Exterior phone report; rain-masked audio instruction |
| E03/1 | E03-01 | Short phone denial; caption history |
| E03/2 | E03-04 | Single-shot female declaration; one reference |
| E03/3 | E03-05 | Exterior identity report |
| E03/4 | E03-09 | Longer multi-line female confrontation |
| E03/5 | E03-15 | Exterior factual report |
| E03/6 | E03-16 | Brief male speech before mask removal |
| E03/7 | E03-17 | Phone/door-gap address |
| E03/8 | E03-18 | Mask removal and confession |
| E03/9 | E03-19 | Intentionally no intelligible speech |
| E03/10 | E03-20 | Explicitly unmasked male confession; caption history |
| E03/11 | E03-21 | Exterior relay of the louder statement |
| E03/12 | E03-24 | Female inner voiceover/closed lips; caption history |
| E03/13 | E03-26 | Silent phone-message action; no invented visible wording |
| E03/14 | E03-27 | Unmasked male/female exchange; six references, 14-second request |

Two fixtures in a long scene remain one scene. Before generating outputs, review
source-only eligibility and use the earliest complete, internally consistent
retained packet for each candidate. A stored correction for a source defect may
be used if its reason and exact revision are recorded before freezing. Do not
choose a later take because its generated picture looked better. If a candidate
has no valid retained packet, select an existing segment from the same scene
that preserves its stated coverage, before sampling; loss of a scene/coverage
class requires a visible plan amendment. No new creative skill, source rewrite
or reference-image generation is part of this plan.

For **each of 272 independent blocks**, draw scene uniformly from the frozen
17-scene roster, fixture uniformly within that scene, and a fresh signed-64-bit
seed. Draw with replacement from the prescribed scene/fixture distribution;
freeze the complete list and exact decimal seed strings before any new output.
Keep the resulting allocation, including unequal counts; do not redraw or
rebalance to obtain favorable coverage or outcomes. Expected allocation is
16 blocks per scene, not a promise of exactly16. Check and report actual coverage
before launch. If a scene is absent, retain that fact; coverage cannot be claimed
for it, and any separate descriptive supplement is excluded from confirmation.

Render A/B/C on every block: **816 planned clips**. Pair all raw inputs and seeds
within a block. Use independent random arm order within blocks; record/replay the
frozen order rather than grouping arms by observed quality. Fixture preprocessing
and each arm's own deterministic encoder bundle may be cached by exact input,
source and configuration hash. Never reuse another arm's features, mutable
conversation/KV state or an unintended generator state. Pilot clips and historical
retries are excluded from the new confirmation sample.

## Outcomes and blinded assessment

Primary endpoint per scheduled arm/cell: **caption-qualified first output**.
PASS requires a technically valid original AV and no unowned screen-space dialogue,
subtitles, chat or speech bubbles across its complete native frame set. Physical,
source-authored text is distinct. UNCERTAIN is not PASS. Report conditional caption
presence among valid AV separately: an infrastructure failure is not evidence that
the model drew a caption.

A cell's first model execution under the qualified frozen contract owns its
first-attempt outcome. No-admission/pre-model failures are reconciled before
starting it. Once model execution starts, a terminal execution/decode failure
counts as non-PASS in the primary denominator even if later technical recovery
succeeds. Retain recovered output separately; do not replace the primary outcome
or add a new seed. Unknown acknowledgments are reconciled by identity, never
blindly resubmitted. Finish unstarted planned cells after safe recovery.

Freeze caption-independent component endpoints before outputs. **Speech fidelity**
requires complete intelligible source speech/voiceover and applicable attribution,
with missing AV/uncertainty non-PASS; its denominator is every sampled block from
the15 speech-bearing scene instances, regardless of caption result. **Critical
scene fidelity** requires the source-owned visible beats and applicable speaker/
observable-sync requirements; its denominator is all272 blocks, including failures.
Report intended speech absence/unwanted voices separately on the two silent-scene
subsets; they do not pad speech success. Compare components on these original
applicable denominators, never only clips that passed captions or the joint score.

Define required words, intentional silence/voiceover, permitted physical writing,
critical visible beats and whether speaker/sync is observable before outputs.
Do not score a masked mouth as demonstrated lip synchronization or mistake
rain-masked audio for a face covering.

The joint observable-quality endpoint requires primary PASS, complete intelligible
source speech or intended speech absence, and supported critical action/attribution/
sync requirements where applicable. Any unresolved applicable critical component
is non-PASS. Source-declared unobservable synchronization is labeled unassessable,
not a sync PASS; disclose it in the endpoint definition and final breakdown.
This joint endpoint is qualified agent QA, not certification of full creative
usability, subtle ambience, stereo spatial quality or owner personal acceptance.

Use fresh anonymous IDs with no arm/seed/runtime metadata exposed to assessors.
Fix primary scores before mapping disclosure. Use the same protocol on every cell:
all consecutive native frames at original detail, actual continuous native browser
playback, and direct unhinted waveform listening by the qualified delegated route.
Retain exact material/coverage, raw responses and source comparison after the
first observation. Captions and scene actions are separate judgments. Do not treat
muted playback, static images, ASR or a model's fluent answer as proof of hearing.

Before the campaign, exercise retained examples covering the actual speaker,
mask, voiceover, silence and multi-line classes, with known silence/truncation
controls. Use existing retained media; calibrator copies never replace originals
or count as experiment outputs. Qualify each claimed assessment capability.
The pilot route established only bounded source-speech perception; it did not
qualify precise speaker/sync or subtle sounds. If readiness remains insufficient,
report affected components as unqualified and the joint advantage as inconclusive;
caption observations can still be collected and reported under their valid scope.
Do not promise a useful-quality ranking when its measurement route cannot prove it.

A uniform, predeclared secondary adjudication may investigate uncertain judgments
with fresh blinded context; retain both findings. It cannot silently promote an
uncertain primary endpoint or introduce unequal source hints between arms. Checker
failures may be repaired and assessed on the same retained originals with a new
frozen scoring version applied consistently to the affected set. If preservation
of blinding is no longer possible, retain that limitation rather than claim
independent primary scoring.

## Analysis and decision rules

The independent sampling unit is the scene/fixture/seed block. Random scene draws
make the primary pooled estimate target the predefined uniform-scene mixture.
Do not reweight realized counts into a different equal-count-per-scene analysis.
Repeated seeds add stochastic evidence conditional on these fixtures; they do not
add stories or physical settings. Display per-scene/fixture, caption-history,
mask/voiceover and maintenance-batch results, plus leave-one-scene-out sensitivity.
These subgroup checks are descriptive, not additional opportunities to declare a win.

For each planned contrast A→B and B→C, count downstream-only passes as wins,
upstream-only passes as losses, and all paired blocks in the denominator. Use
an exact central McNemar test at two-sided alpha=.025, with the published
Fay–Lumbard melded 97.5% paired-difference interval. This controls the two-test
family without requiring A→B success before testing B→C. Pin R and
`exact2x2`1.7.0 in a task-only CPU environment; use `mcnemarExactDP` with
`x=wins`, `m=wins+losses`, `n=272`, `nullparm=0`, two-sided, `conf.level=.975`,
`nmc=0`. [CRAN reference](https://cran.r-project.org/web/packages/exact2x2/exact2x2.pdf)
and [primary paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC9447366/).
The test is exact; general interval coverage is supported numerically in that
paper rather than a general mathematical proof. Do not label it a guaranteed
exact-coverage interval.

Run bounded provider-free package checks before generation: no discordance,
one-direction discordance, label swapping and a small synthetic coverage grid.
Zero discordance gives estimate0/p=1, never a zero-width interval. If the interval
routine is numerically unusable, retain exact test results and use the predeclared
conservative fallback: Bonferroni Clopper–Pearson intervals for win/loss probabilities
(each98.75%), subtract endpoints, and disclose wider bounds. Recalculate precision
claims for the actual method; do not build a new statistical platform.

Exact binomial enumeration for272 pairs and the central test gives the following
planning sensitivity. `q` is the chance a paired block is discordant, not a rate
estimated from the two-seed pilot:

| True caption-qualified gain | q=.20 | q=.35 | q=.50 |
| --- | ---: | ---: | ---: |
| 10 pp | 92.6% power | 68.3% | 50.7% |
| **15 pp** | **99.99%** | **97.5%** | **88.9%** |
| 25 pp | Impossible with q=.20 | ≈100% | 99.99% |

This is power to detect superiority against zero, not power to establish a true
gain of at least15 pp. It assumes a stable frozen execution/scoring distribution
and independent seed blocks; runtime/scoring drift must be examined. q=.50 is a
sensitivity case, not a worst case; higher discordance lowers power. A 612-clip
alternative gives only76.7% power at15 pp/q=.50;816 is the selected planning
recommendation. Reproduce the table by summing over discordant counts
M~Binomial(N,q), then the positive central rejection tail for W|M~Binomial
(M,(q+gain)/(2q)). The provider-free calculation is retained in
`.local/ref2va/cross-framework-replication-plan-20261109/sample_size.py` and its JSON.

Interpret every contrast using the effect and interval:

- A positive effect with p≤.025 supports improvement; a point estimate≥15 pp
  meets the observed practical target. It does not prove the true gain≥15 pp.
- Only a lower interval bound≥15 pp supports that stronger magnitude statement.
- An upper bound<15 pp rules out a gain that large under this panel/analysis.
  Failure to reject zero is not evidence of equivalence or no difference.
- Otherwise report the remaining uncertainty. Do not increase sample size or
  search seeds after inspecting an inconvenient result.

Caption or joint benefit alone does not establish the owner's no-worsening
condition. Report paired speech, critical-scene and intended-silence component
effects and97.5% marginal intervals independently of captions. **Any observed
component regression is a fidelity tradeoff**, even if the joint rate improves.
If an applicable component interval allows loss, true no-worsening remains
unestablished; do not substitute a nonsignificant regression test for that proof.
A fully resolved negative finding is still a regression, not an acceptable
“resolved defect.” No positive degradation allowance is invented.

Within each contrast, only after its caption test passes, test the joint
observable-quality endpoint at alpha=.025 as a fixed second step. This preserves
the two contrast families; secondary component intervals are explicitly marginal,
not a new family of standalone superiority claims. The combined favorable-quality
interpretation additionally requires no component regression, all applicable
component lower bounds≥0, a positive joint lower bound and qualified assessment
capabilities. Bounds allowing loss or unqualified critical checks mean **caption
benefit; quality non-regression unestablished**. That can be the completed study's
answer; it does not stop completion or force more samples. Full creative acceptance
and production rollout remain separate decisions.

The two intentionally silent scenes contribute2/17 to primary caption analysis.
Exclude them from speech-specific endpoints; the expected speech-bearing count is
240 blocks and its actual frozen count owns that analysis. Do not pad speech
success with silent clips. At N=240, a true15 pp gain on the **speech-bearing
joint subset** has about84.1% power atq=.50; the all272-block joint endpoint also
includes intentional silence. Caption-and-joint/component qualification together
has lower, unknown power.

## Execution sequence after authorization

1. **Prepare from retained evidence.** Read the pilot report/index and source
   packets. Verify current local/Spark capacity and idle authority. Copy required
   retained bytes into a new experiment directory; preserve all old controllers,
   receipts and production selections. Freeze eligible panel, source contracts,
   randomized sample/order, scoring, analysis and source/image/model versions.
2. **Adapt only demonstrated gaps.** Reuse the task-local fixture, noise, A/B/C,
   collection and review helpers. Remove single-fixture assumptions through small
   cohesive modules. Verify complete native arguments for all19 candidate fixtures:
   1–6 references PLUS their timed guides, varied requested durations/native frame
   counts, 960×544 contain/pad pixels, exact guide indices and int64 seeds. Do not
   force260 frames, three references or three guides onto every scene. All adapter
   tests remain provider-free and fail on unintended live submission.
3. **Qualify changed boundaries, then finish a real block.** Reuse unchanged
   weight/runtime/first-update evidence. Check new layout/noise/guide contracts
   offline across fixtures; probe actual largest memory shape if not covered.
   Use a sampled block for the first complete native A/B/C journey and all-frame/
   audio/playback assessment, retaining it as a scheduled outcome. Review whether
   execution and measurement serve the study before launching the remaining cells.
   No unrecorded extra quality sample or favorable-output checkpoint.
4. **Run serial GPU blocks with safe maintenance handoffs.** One source/lifecycle
   owner; parallel read-only CPU/perceptual review where isolation permits. Use
   fresh intents/known identities, actual closed admissions/native queues and
   physical memory release checks. Freeze source math during the campaign. Reuse
   immutable own-arm encoder bundles; retain per-cell consumed controls, all20
   evaluation/finite/time checks, provenance, complete original AV, technical
   decode and measured stages. Technical recovery is allowed after identity/
   termination reconciliation; two failures of the same criterion trigger causal
   reassessment, not an arbitrary total retry ceiling or automatic approval request.
5. **Assess and analyze the complete fixed sample.** Keep arm mapping from primary
   assessors, retain every failure/uncertainty, and apply fixed scoring consistently.
   No outcome-based removal, early victory/futility stop or extra seeds. Record
   latency from pre-encoding/loading through retained playable output, separating
   queue time, cold/warm/cache behavior, failures, memory and assessment effort.
   Existing pilot phase timings do not establish total throughput.
6. **Restore, verify and deliver.** Reconcile native retention, restore original
   runtime/admissions and capability readiness, verify task resources idle and
   protected state, assemble and hash-check a private portable evidence bundle,
   and publish the result locally in this roadmap. Final strategic review judges
   the actual investigation, including an inconclusive answer. Preserve a scoped
   local main checkpoint; no CI/push or production replacement follows implicitly.

Material math/model/fixture/scoring changes invalidate the affected comparison
claim. Safely settle current work, retain failures and determine the matched
set needing new evidence before continuing. Requalify a correction and use fresh
confirmatory outcomes where prior exposure would bias the claimed independence;
do not pool incompatible versions or silently expand the primary sample. A repair
that preserves arithmetic/inputs needs proportionate verification, not an automatic
repeat of unrelated qualification. A new cohort is explicit scientific scope,
not a quality retry disguised as technical recovery.

## Capacity, preservation and operational closeout

Use bounded maintenance blocks rather than leaving shared services stopped for
weeks. Restore them between blocks and during substantive waits/review whenever
safe. A block boundary may change for memory or operational reasons without
changing sampled identities/primary outcomes. The other director's user-requested
pause remains until further notice; verify actual live state nonetheless.

The last study's exact post-start equality failed because native cleanup expired
older files. Before each new quiet window, inventory outputs/assets/inputs due to
expire during the block and verify SHA-identical owner-retained copies; make only
necessary task-scoped preservation copies when none exist. Do not edit retention,
reset purge flags or restore expired server paths to fake equality. Retain strict
before/after results and derive an exact row/file reconciliation for lawful native
expiry; unexplained losses or changed current selections block closeout.

Retain original AV, inputs, model/source identities, control hashes, failures and
fixed assessments permanently for this study. Keep full tensor diagnostics for
qualification/first new layouts and failures where causal diagnosis needs them;
per-cell hashes/finite/time traces need not duplicate every large tensor payload.
Frame-complete contact pages are regenerable review inputs: generate and inspect
bounded batches, retain page hashes/coverage, then remove only explicitly declared
new disposable render buffers/pages after original MP4 retention and fixed QA.
Old pilot/production contacts and source images are not disposable by this plan.
Measure actual disk headroom before launch; never fill the shared host to preserve
hundreds of redundant raw RGB corpora. Every reported caption PASS still requires
actual complete frame inspection; hashes/regeneration capability alone do not count.

## Permission boundary and director discretion

Current authority covers planning, source reads, provider-free calculations and
these planning reviews. Standing task/model-choice permission already covers
read-only assistance. The prior six-cell execution authority is closed and does
not authorize this816-clip campaign. A later instruction to implement this plan
would cover its fixed campaign, necessary scoped diagnostics/dependency downloads,
isolated CPU/GPU environments, reversible idle-service quiescence/restoration,
targeted preservation copies and declared task-owned cleanup. It creates no new
budget ceiling or deadline. Record consequential choices in this plan/handoff.

Within that authorized assignment, ordinary batching, caching, module boundaries,
known-state recovery, review fixes and verification do not need repeated owner
sign-off. Passing an internal review means continue covered work. Native access
confirmations still apply. Do not interrupt active/uncertain work or bypass old
grants, unknown-dispatch guards or source permissions. Paid external providers,
new stories/reference art, changed arms/precision/sampler intent, broad kernel/
quantizer development, production migration, selected-clip replacement, CI and
triggering pushes remain outside scope. Present a concrete scope decision if
one becomes necessary; continue independent authorized work meanwhile.

## Estimate and review points

Forecast with the existing qualified envelopes: **2–4 engineering days** for
multi-fixture adaptation, assessment/analysis readiness and review fixes, plus
**roughly250–450 hours of serial shared-GPU work** for rendering/review, and
**2–4 days of overlappable assessment, analysis and closeout**. Allow approximately
**2–4 calendar weeks** with substantial daily Spark availability. Actual durations,
1–6 guides, caching, restarts and assessment throughput are unmeasured at scale;
these are forecasts, not quotas. No external-provider wait is assumed. Shared
resource availability or a demonstrated compatibility repair can extend elapsed
time. There is no time cap; an estimate overrun alone does not require stopping.

Review direction after the first fully assessed triplet, earlier on lost guide/
source contracts, memory failure at a new shape, unqualified measurement, evidence
of pipeline drift or inability to reserve/preserve shared resources, and at final
closeout. After the first triplet, update the end-to-end forecast and actual disk
plan using measured complete boundaries; do not use quality results to shrink or
grow the confirmation sample. This plan creates no automation or watchdog.

## Independent planning reviews

Outcome/completeness review: GPT-6.1 Sol / Xhigh explicitly requested in a fresh
read-only context. One finding: a joint gain can mask worse marginal speech or
scene fidelity. Corrected by frozen caption-independent components, original
applicable denominators, paired intervals and explicit regression/uncertainty
interpretation. The reviewer independently reproduced the sizing calculation and
found no other blocker. Its focused recheck confirmed the correction resolves
the counterexample, with no further change required.

Avoidable-restrictions review: separate GPT-6.1 Sol / Medium explicitly requested
in a fresh read-only context. PASS, no findings or plan changes. It confirmed
routine recovery/discretion, bounded sampling, resource serialization, review
points and planning-only permissions are justified; no Review1 recheck was needed
because Review2 changed no success/evidence requirement.

Both reviews are internal work steps, not execution approval. Native selectors
were explicitly requested/accepted; effective runtime settings are not separately
exposed. Planning checks verified the source corpus counts, exact sizing table,
local document links and scoped diff. No new model/media execution or runtime,
provider, production-selection, CI or publication change was performed.
