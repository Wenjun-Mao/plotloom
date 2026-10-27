# Writing-model comparison and cleanup — 2026-10-27

Keep the existing **Sol/medium** default. Both blinded AI readers preferred
Sol's dramatic construction in all three pairs, while crediting Terra's economy.
Both models failed the unchanged quality bar under both readers. This experiment
answered the bounded adoption question; it did not fix story quality or establish
a general model ranking or historical decline.

## Method and actual execution

The experiment used one draw for each of three fixed Chinese Alpha Briefs per
model. Both generators used **medium** reasoning effort; Terra/high was not
tested. All 49 native session observations matched the assigned alias and medium
effort. Server-side model weights and monetary cost were unavailable. Engineering
coordination was host-confirmed Sol/high; the two fresh readers requested
Sol/high, with their effective host settings unverified.

Both arms used generation source `ec7dd08913905c5d532a25baf28f6425187f7ffb`,
based on published `6fb72a33`, with matching prompts, schemas, validators,
style authority, correction policy, CLI and checked environment. Later-stage
inputs diverged with each model's earlier writing. This was a whole-pipeline
comparison, not an identical-input test of every stage.

The predeclared first pair passed native installation, SQLite reopen and API
readback before expanding to the other four cells. Model order alternated
Sol/Terra, Terra/Sol, Sol/Terra. All six installations completed and paused at
references; no image/video generation occurred.

| Story | Sol first-pass / attempts | Terra first-pass / attempts | Sol minutes | Terra minutes |
|---|---:|---:|---:|---:|
| 雾港回声 | 8/8 / 8 | 8/8 / 8 | 21.06 | 9.26 |
| 最后一盏灯 | 8/8 / 8 | 8/8 / 8 | 19.40 | 9.04 |
| 雪线来信 | 8/8 / 8 | 7/8 / 9 | 26.87 | 8.79 |
| Total | 24/24 / 24 | 23/24 / 25 | 67.33 | 27.08 |

There were 48 completed attempts and one retained failure: Terra Snow's first
Storyboard frame lacked the required literal `extreme close-up`. The existing
single correction changed only `/episodes/2/segments/0/cuts/1/frame`; it did
not rewrite the story. First-pass counts are native host attempts, not every
draft revision within a session. Aggregate native generation took 94.4 minutes;
complete product/infrastructure/coordination timing is unavailable.

## Quality and additional review caveat

Each reader inspected all four canonical artifacts and all six routes for each
sample. Twelve initial score sheets were closed before opaque paired comparison
and remained unchanged afterward. Thresholds were unchanged: no fatal
contradiction, every score at least 3, sample mean at least 3.5, and each dimension
median at least 4, separately per model and reader across the three stories.

| Reader | Model | Clarity | Causality | Continuity | Performance | Shots | Pacing | Gate |
|---|---|---:|---:|---:|---:|---:|---:|---|
| 1 | Sol | 4 | 3 | 4 | 4 | 4 | 3 | FAIL |
| 1 | Terra | 2 | 3 | 3 | 3 | 3 | 3 | FAIL |
| 2 | Sol | 4 | 3 | 4 | 4 | 4 | 3 | FAIL |
| 2 | Terra | 3 | 3 | 3 | 4 | 3 | 3 | FAIL |

The table shows dimension medians. Sol Snow's pacing was 2 under both readers.
All six Terra sample means were below 3.5. Both readers gave Terra Snow clarity
and causality 2; one called its contradiction fatal and the other did not.

| Story | Sol mean, readers 1 / 2 | Terra mean, readers 1 / 2 |
|---|---:|---:|
| 雾港回声 | 3.67 / 3.67 | 2.83 / 3.33 |
| 最后一盏灯 | 3.67 / 3.50 | 3.00 / 3.17 |
| 雪线来信 | 3.50 / 3.50 | 2.67 / 2.50 |

The later full review found an omitted caveat: both genuinely and independently
randomized reading orders happened to place all three Terra samples before all
three Sol samples. Both assessments followed those orders. Shared order and
calibration effects therefore remain possible, alongside same-family evaluator
preference. Agreement does not establish a general ranking. No rerun or regrading
followed this finding; the conservative keep-current-default decision stands.

Three stories, one draw per arm and two AI readers cannot establish statistical
superiority. No rendered footage, performed audio, audience comprehension or owner
creative acceptance was inspected. The original nine-run Alpha result stays FAILED;
these separately versioned pilot receipts never qualified formal Alpha.

## Actionable findings

1. **Finished on-screen wording has an ownership mismatch.** Descriptive F4 action
   prose such as “正文对同一刻…” and “警示文字交代…” was selected by the presentation
   classifier as `visible_text`, then copied verbatim into canonical literal text.
   F5 supplied durations; it did not directly author those strings. The schema,
   projection and H3 consumer agree on exact viewer-facing semantics. Four exact
   source/span/output mappings, including three 3-second inserts and a 3.5-second
   warning, are retained in the [portable trace](supporting/writing-model-pilot-20261027/visible-text-trace.json).
   Actual reading performance remains unmeasured; the first letter's wording
   after its colon may plausibly be literal.
2. **Information load and stakes remain weak in specific stories.** Sol Snow has
   22–23 shots in a minute with dense short text inserts. Terra Snow leaves all
   three letters accessible at one recipient's doorway without explaining why
   only one can be delivered. Both Lamp variants under-motivate the empty theater
   against hospital lighting. Sol Fog's observable prediction and later broken
   post give readers clearer evidence, but its bell-surrender stakes remain thin.
3. **Shared-node presentation constrains persistent first-choice effects.** The
   current player selects footage by node and does not select a different shared
   ending or final eligibility from prior-choice history. Sol Fog's conditional
   bell wording is authoring intent, not proof of realized variants. Meaningful
   actions can still occur in unique middle sections. This limit does not force
   cosmetic choices or establish the cause of historical clarity/pacing failures.
4. **Temporal decline and direct correction erasure were not demonstrated.** No
   matched earlier scored baseline was found. Inspected core prompt/topology/timing
   owners were unchanged between historical `79668e1a` and pilot baseline
   `6fb72a33`. The historical scored Outline, Branches, Script and Storyboard
   operations were first-pass. Other corrections changed visual-production fields,
   including four character image-prompt substitutions; indirect effects remain
   untested. The code supports unequal section durations and a route maximum,
   rather than requiring equal 20/20/20-second sections.

The next recommended quality slice is finished F4 wording, faithful presentation
role ownership and a one-minute information budget, through one real story before
scaling. History-dependent shared-node playback is a separate capability decision.
Neither that repair nor another model trial is authorized by this cleanup.

## Verification, preservation and retirement

The experiment passed 85 focused cases, quick checks with 1,564 frontend cases
and both type checks, and real per-arm preflights with 22 validator/render commands
and seven import/denial controls. Independent generation and final report review,
then manager review, verified native identities, installation/binding hashes,
original scores, mappings, math and the correction boundary. No full release gate,
GitHub CI, model switch or production adoption was claimed.

The owner then authorized cleanup and publication. The retained
[index](supporting/writing-model-pilot-20261027/index.json) contains metrics,
reader mappings and file hashes. Its six canonical exports provide a concrete
baseline for the next quality repair; twelve original score sheets and four
assessments preserve actionable editorial feedback; two Snow source candidates
make the exact wording failure inspectable. This compact set replaces temporary
physical-path proofs. It is not an executable native-session replay package.

The disposable model installations, neutral reading packs, checked runtimes,
worktree and unadopted branch are retired after quiescence and retained-file
verification. No experiment selector is merged: it affected general profile
construction within its branch, beyond pilot commands. Its duplicate experiment
ADR 0223 is retired rather than merged over main's authorization ADR 0223.
Current production projects, media, settings, claims, UNKNOWN state and H5 exports
remain outside disposable cleanup. The authorization fixture timeout remains
unresolved as recorded in the [repair account](../roadmap/2026-10-27-qa-runtime-authorization.md).
