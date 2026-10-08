# Fresh full creator E2E run ledger

Scope: [approved repeat](../roadmap/2026-10-07-full-creator-e2e-repeat.md).
The permanent C01–C55/P01–P06/E01–E22 checklist owns acceptance. Current status
is PARTIAL. The [native Character/gallery checkpoint](2026-10-08-native-character-gallery.md),
[media repair receipt](2026-10-07-media-selection-recovery.md)
and [C50 recovery](2026-10-07-c50-draft-recovery.md) / [C52 project ownership](2026-10-07-c52-project-ownership.md) own the latest continuation.
Dated checkpoints below and the [historical receipt](2026-10-07-full-creator-e2e-repeat-history.md)
retain earlier failures; historical present-tense claims are not current status.

## Dedicated whole-product visual and text audit added

Owner-requested scope: execute E22.1–E22.7 as part of this full E2E run, including
awkward, opaque, misleading or inconsistent wording (“weird wording”). Prior
functional walkthroughs included incidental UI inspections, not a completed
whole-product visual/copy audit. The dedicated pass has executed, with PARTIAL
state coverage and verified scoped repairs;
its [view/state observations and repairs](2026-10-08-whole-product-ui-audit.md)
and [original-report/stale-Art checkpoint](2026-10-08-static-report-art-ui-states.md)
and [frozen-configuration checkpoint](2026-10-08-frozen-profile-ui-states.md)
and [native preview error checkpoint](2026-10-08-native-preview-error-ui.md) /
[reading-state checkpoint](2026-10-08-reader-gallery-ui-states.md) are recorded separately from functional results. Desktop matrix:
1280×768,1280×460,1700×900; no phone/1024px testing.
Reuse disposable data, distinguish fixture/native states and avoid repeated
generation solely for visual inspection. All Create → Revise → Recover gaps remain.

The [current-Art reference-gallery checkpoint](2026-10-08-art-reference-eligibility.md)
adds explicit current-head authority, safe stale-task cleanup, zero-write retained
image reading and independently checked locked-field wording. Executable `3ad91e4`
is published and healthy on normal8841, with focused43/full737 frontend and fresh
unfiltered236-browser PASS. Six directly inspected normal Gallery/controls frames
at all supported sizes make zero writes; owner/settings fingerprints remain exact.
Its full exact-head CI37801077786 passed verify and both browser shards;
full native/revision coverage remains open.

The [native-route/end-frame checkpoint](2026-10-08-native-routes-endframe-qualification.md)
adds both completed minimal native routes, West reject/reopen/reselect history,
and the owned read-qualification/long-error-layout repair. Its current candidate
gate and publication are tracked there, not inherited from an older executable.
Its then-open media-bearing recovery is now covered by the
[196–197 native recovery](2026-10-08-native-media-lifecycle-recovery.md) and
[203 load/retained-media repair](2026-10-08-load-retained-media-qualification.md).
Same-node multishot and revised installed production remain open.

The earlier [post-reboot native checkpoint](2026-10-08-native-decoder-recovery.md)
qualifies exact-original playback, five-second segment preview and explicit
technical-only selection on the native opening shot. Its then-missing route shots
are covered by the newer checkpoint; the earlier decoder failure is not diagnosed.

## Recovery repair published 2026 10 07 23 19 UTC

Root approved and pushed the frontend-only repair as
`5aff37e885fdd8b32f9282d8cc14a5366ee1a99e`; origin/main identity was verified.
Full unfiltered [CI37701584435](https://github.com/Wenjun-Mao/plotloom/actions/runs/37701584435)
finished success at00:02 UTC with205 first-pass browser results and one retry pass. Final
206-browser gate PASS6.0m; all856 source/test/config/static inputs stayed unchanged.
Their aggregate is `bbc702df320b991ae67a0dba5eed064866fa642d2a6dafe1da7f0b1da7430c3c`.
Normal8841's Python remains the qualified e941780 source, unchanged;
its checkout mount already serves the newly built JS
`efcf31dcf30926e4a88a9577a3ebc0bff5b2764b5017ca8e5daa5afd77b36114`.
Both CSS files are unchanged. No restart/reload/resend touched busy8861.

On disposable8871 QA965671f3, connected start reassignment was refused without
changing r19. Explicit incoming-edge detachment then legal start reassignment
r20→21 preserved all sections, identities and nonblank contracts; two Undos
restored the exact baseline at r23. Separate outgoing-edge detachment permitted
scene→choice r24→25 without invented options; two Undos restored r27. An explicit
optional merge contract permitted scene→join r28→29 with edges retained; two Undos
restored the exact r19 mapping at r31. Canonical revision stayed0. Pixels24–26
were directly inspected; this is finite type/start coverage, not every permutation.

UI-origin image-recovery QA `94a5b5ac-e1bf-4d4e-9509-685d0e424aff` imported one
existing QA browser screenshot, explicitly labelled not provider generation or
creative acceptance. Asset `d965a5d7-c07f-4079-9bdf-8a14c2748ddc` stayed identical
through Save-close/reopen and archive/restore; original SHA256
`0342ac0f075da18dd29f70f4c941ef464631cf56b486ded19631b2ae09b6f209` and display SHA256
`cb7aedfe7b4de35739f878a05fbd6abd326e3f903c5f912974b96d56bdb2791e` matched independent
HTTP byte readbacks. Provenance retains unknown rights, null rights note and the
explicit synthetic addition; selection revision stays0. Pixels28–33 directly
qualify loaded1700×900 image bytes and access states. Last restore is active at
lifecycle r5; this retained object was not deleted.

UI snapshot `75c90f42-968a-4d7e-9863-81d9bbcd7fcc` is format1 containing current
project format11. Operator restore into `/private/tmp/plotloom-image-restore.OzkaVw`
matched all five manifest files by independent SHA256, including both images and
the SQLite bytes. Repeating into that exact identity refused overwrite (exit2),
with retained hashes unchanged. Separate8873 then opened this restored copy with
fresh application storage, no provider keys and no native specialist. Its UI
loaded the same1700×900 image; independent original/display HTTP hashes and
provenance matched. Explicit1700×900 pixel35 was inspected (body width1700,
scrollX0); pixel34 inherited tab sizing and is not desktop-layout qualification.
Project/source r1 and selection r0 stayed unchanged. The owned8873 tab/runtime
was closed/stopped; restored files remain. Video/native lifecycle is unqualified.

Archive inspection demonstrated false “正在保存…” labels on Story Bible, Scene
Beats and Storyboard. The owning controller conflated read-only access with save
progress. ADR0129 separates them; the disabled workspace fieldset and Storyboard
media/confirmation locks remain enforced. Actual archived QA retest has three
normal disabled Save labels, no false busy label, locked upload/snapshot and the
retained image. Restore re-enables Save/upload without changing that image.
Independent source/test review found no lock regression. Focused14 and full597
frontend checks, app/E2E types, lock, API import lint, diff, wheel and installed
smoke pass. The pre-transport206-test browser gate PASS7.0m with all856 inputs
unchanged. Earlier e941780 CI37694754831 finished FAIL: verify and browser1 PASS,
browser2 had101 PASS/1 FAIL including retry, a renderer fixture exceeding Linux
single-argument limits (`spawnSync node E2BIG`), not a browser/product assertion.
The same report JSON now uses stdin, with renderer and assertions unchanged;
focused three-repeat3 PASS12.9s. Its full gate retained205 PASS/1 FAIL6.7m,
exposing a separate Source-edit ACK race: the independent GET started17ms
after the UI PUT began, before its102ms successful r2 commit. The trace retains
the exact revised prose and declarations; the test must wait for that ACK before
reading back. All856 inputs stayed unchanged during that failed gate. The test
now checks the exact successful PUT/r2 response and visible r2 before its persisted
readback; independent review is clean and three repeats PASS11.8s. The final
206-test gate PASS6.0m; this is harness ordering, not product data repair.
Failed artifacts remain under `readonly-stdin-final-browser-gate/`.
Final artifacts are `readonly-stdin-source-ack-final-browser-gate/`. A repeat
deterministic build retained the exact JS/CSS bytes. Python1,245 PASS/381.25s is
reused from e941780 because its source/tests/config are unchanged, not rerun.
Wheel/installed smoke PASS; wheel SHA256
`2940646f28e9388fd0c9c86e5c059c820acce3b7d1534fd2be62f9e42e7a7cbc`.

The strengthened archive fixture imports a still and compares its full asset
projection plus original/display bytes before, during and after archive. Exact-title
delete has a successful ACK, project/asset404 and no matching project home. Final
focused journey PASS4.6s; this is offline fixture deletion, not native video deletion.
Three retained harness failures did not establish product data loss: a blind toggle
closed the already-open Tools menu; two final assertions assumed deletion/New Blank
navigated to Brief, whereas both preserve the current tool route. Existing helpers
and explicit named Brief navigation correct those assumptions; no timeout weakening.
Artifacts remain in `readonly-focused-browser/`, `readonly-media-focused-browser/`
and `readonly-media-reconciled-browser/`; PASS is `readonly-media-final-focused/`.

Post-publication owner recapture matches `df1716a80d93bdf9aeaf2565464ac030340ab035cf86198d5355befea075f2a5`
(Wind17/Rain67 files, both DB row/schema sets and three protected configurations).
The earlier global helper refuses the five-project registry; the scoped recapture
checks only the two protected owners, without modifying or weakening that helper.
[Real OS focus recovery](2026-10-07-creator-os-focus-recovery.md) now passes automatic380/persisted350 with trusted events, retained text/cursor/scroll, zero post-ACK writes and exact QA cleanup r33; the earlier dated unsuccessful methods below remain historical.
Native image continuation, post-install rebuild and configured inference remain
separate gaps. Full lifecycle acceptance is PARTIAL.

## Published repair release 2026 10 07 22 13 UTC

Root approved the independently reviewed repair batch after the final local
gates and exact855-input readback. Executable `e941780302c9d97be0b1f0fd9cb1bace4549d5d8`
is committed on main and pushed to origin/main; remote HEAD was verified, with
no force push. The21:53 section below records its pre-publication state, not the
current deployment. Full lifecycle acceptance remains PARTIAL.

Normal8841 was activated through the existing `manage.py start` at22:10–22:11.
Container and native bridge health passed; HTTP entry and healthz are200.
Its loaded Python is now this repair candidate rather than the earlier backend.
Served JS `e0cb4a2a60d17bfff68d71c1ac79a683c2de34c57eeaaabfbdd902d831fd11fd`
and CSS `d430ea5d72528c509b27446c10eb5ae34cada9c5e8808e8ad72c616570ea10cb`
match the qualified build. The accepted Rain Cast r2 still reports its original
job `ch_212cad5ded684740b1d1e6672a570ea4`, `reportAvailable:true` and
`differsFromDelivery:true`; its static report is200/54,886bytes with the original
sandbox CSP and nosniff header. Its existing stale status was not changed.

Post-activation owner DB/row/schema/file/settings hashes still equal aggregate
`df1716a80d93bdf9aeaf2565464ac030340ab035cf86198d5355befea075f2a5`:
Wind17/Rain67 files and three protected configurations. Separate8861 PID44523
and8871 PID91539 retain their original start times. The pending image package
still has the same request hash, zero outputs and no completion; it was neither
resumed nor resent. No native media or H3 call was made during this release.

[Full unfiltered CI](https://github.com/Wenjun-Mao/plotloom/actions/runs/37694754831)
is running on the exact executable revision; it is not yet claimed PASS.
Local1,245Python/594frontend/206browser and the other release gates remain the
qualified results below. Outstanding native creation/media, supported post-install rebuild, configured
model inference and actual OS blur remain separately unqualified.

## Current repair batch 2026 10 07 21 53 UTC

The current batch is uncommitted and has no freshly activated normal8841 backend.
Its loaded QA runtime is separate8871/8872, with empty disposable storage under
`/private/tmp/plotloom-preview-qa.QBEXwD`. Normal8841 and busy8861 were not
restarted; existing8861 tabs were not reloaded and its frozen image job was not
resumed, resent or modified. The18:37 publication below is a prior deployment
checkpoint, not qualification or activation of this repair batch.
Read-only HTTP checks at21:51 establish that normal8841 already serves the current
checked JS/CSS hashes below through its read-only checkout mount. Building the
static assets therefore updates those served bytes without restarting Python;
normal's loaded backend is still the earlier checkpoint. Healthz is OK, but the
mixed served-static/loaded-Python state is not a qualified full-batch activation.
The earlier shorthand “not activated” must not be read as “static bytes unchanged.”

Independent reviews closed the installed-proposal project-ID lookup correction,
accepted Cast original-report lineage, candidate-only Branch static report,
typed graph-safety guidance, distinct merge-contract preview impacts, and centered
row-add icon. The Branch candidate reader preserves original archived HTML and
static sandbox boundaries. Adopted Branch report association remains separate
schema/capability work; no latest-candidate fallback was added.

Full Python1,245 PASS/381.25s and frontend594 PASS/5.31s. The first full browser
run206 PASS/6.1m preceded the final icon fix. The next gate retained205 PASS/1 FAIL:
the graph-interactions harness reloaded21ms after starting Save, aborting the
browser PUT receipt while the server committed r4 with the exact prose. Its local
buffer still bound r3, so the explicit conflict guard correctly protected it.
Root and independent read-only review identified an E2E ACK race, not data loss.
That checkpoint waited for Save-owner settlement and exact server prose; the current
media repair receipt adds owned ACK/full-payload readback without bypassing conflicts.
Focused three-repeat3 PASS/6.4s; final206-test browser gate PASS/6.3m.
App/E2E typechecks, lock, API F401 lint, diff and deterministic build
PASS. Final checked JS is
`e0cb4a2a60d17bfff68d71c1ac79a683c2de34c57eeaaabfbdd902d831fd11fd`.
Checked and normal-served CSS is
`d430ea5d72528c509b27446c10eb5ae34cada9c5e8808e8ad72c616570ea10cb`.
The final855-file gate input fingerprint is
`089bbfe1b2b1fd991f710b0148f200a2cfa7c943cef21be162abdd76e921794e`.
Since the Python checkpoint only eight frontend/test/static inputs changed;
no Python source or Python test changed. Wheel build and installed-wheel smoke
PASS; wheel SHA256 `5224be557d7b5ca57574b9977cb72da59ebc81c3aa976431374150edd57f34b5`.
The855-file fingerprint is unchanged across the final browser gate. Its retained
artifacts are `output/playwright/full-lifecycle-2026-10-07/final-save-ack-browser-gate/`;
the failed attempt remains separately in `final-centering-browser-gate/`, and the
three repeats in `save-ack-focused-repeat/`. Writer browser attempts denied artifact writes/Chromium launch
before assertions; these are not passing checks or product assertion failures.

Root directly reviewed repaired preview pixels15–18 on UI-origin disposable
project `965671f3-491c-4c30-ba26-03fe20463eba`: added/removed contracts identify
their direct inputs; deleting a nonblank optional contract preserves nodes/edges;
Undo restores exact mapping/fields (r5→6→7). Safe bypass distinguishes removed
optional contract from retained join input changes, preserves the retained keys,
allowed differences, notes and reconciliation, and Undo restores exact mapping
(r11→12→13). Type/footage preview visibly discloses both changes; Cancel preserves
the mapping. No canonical confirmation/application or generation occurred.

Pixels19/20 directly qualify the centered plus at1700×900 and1280×768. All six
row controls remain30×30 with zero icon-center offset on both axes; their named
row-add dialog opens and cancels without adding a node. Save-close/reopen retained
the exact saved draft. The beforeunload prompt protects retained uncanonicalized
work even after draft acknowledgement; an empty session registry is not canonical
acceptance. A batched reload that raced explicit close was dismissed, then close
settlement was verified before reload; no loss or stale-ref bug was established.

Owner protection was read-only recaptured at21:21,21:48 and21:53 with the same baseline aggregate
`df1716a80d93bdf9aeaf2565464ac030340ab035cf86198d5355befea075f2a5`:
two owner DB schemas/rows, Wind17+Rain67 files and three protected configurations.
The earlier declined inspection was recovered through the verified named
`查看版本与技术详情` control; retained pixel02 proves the inspection completed.
That does not qualify the pending image job. Full E2E remains PARTIAL.

### Additional desktop and deletion checks 22 08 UTC

The final independent read-only release audit found no concrete source blocker
in this repair batch. Normal8841's five project databases have no nonterminal
text/media/video work or prepared creative candidates; its native dispatch
directory has no inflight assignment. Both protected owner projects and all
protected files still match the exact baseline aggregate above. These are
release-readiness checks, not native media acceptance.

On disposable8871 project965671f3, explicit choice-only deletion r13→14 retained
all seven other nodes, their sections and all eight edge identities; the three
affected endpoints became pending. Nonblank retained merge fields were unchanged.
Undo restored the original mapping. Join-only deletion r15→16 removed only the
selected node and its disclosed merge contract, retained every other node/section
and edge identity, and Undo r17 restored the exact mapping and field buffers.
The UI correctly refused safe bypass into a single-entry choice without a merge
contract. Ending-only deletion r17→18 preserved the choice edge as pending and all
other nodes/sections; Undo r19 restored the exact mapping, buffers and row hints
from r13. Canonical revision stayed0 throughout; no generation or application.
Root directly inspected preview pixels21–23 at1700×900. An inspection expression
first used `draft.mapping` instead of `draft.payload.mapping` after the choice
commit; readback reconciled r14 before Undo, with no repeated deletion.

Actual OS blur remains NOT EXERCISED. Native-app inspection timed out. A separate
real Finder activation during a held divider resize produced no observed browser
blur within20s, rather than a simulated event. The temporary width380→440 was
ordinarily reset to automatic380; authored draft r13 was unchanged. This does not
qualify the cancellation handler or establish a product failure. Fresh specialist
thread inspection confirms the same image job stopped at source preflight, with
no image/completion; no continuation or reservation change was sent.

## Published checkpoint 2026 10 07 18 37 UTC

Local checkpoints `406c942` and `be876346995ff5385db16992f34298e2cf2854f0`
were published by root to origin/main at18:37:52, push exit0 and remote HEAD verified
as `be876346995ff5385db16992f34298e2cf2854f0` (including `406c942`).
This is a dated after-source-push receipt; current CI was not yet listed and is not
claimed PASS from older runs. Root restored normal8841 from the clean final checkpoint
with the established manage.py start at18:30:59→18:31:16, exit0. Docker/native bridge
health passed; HTTP healthz was OK at18:32:37. Deployment/token/specialist settings
are unchanged. The earlier17:03 idle maintenance preserved the old checked static.
Old checked static is recoverably retained in
`output/playwright/full-creator-2026-10-07/pre-capability-checked-static/`.

Retained8851/8852 Python (PID2191/session91780) started before the final shot-policy
cleanup. Its explicit-advisory QA is semantically comparable, not identical to the
final loaded Python. Its isolated static matches the checked candidate. SHA256 is
`c8fe9734faaed15142987c80fd318561260269d4e8c8415d853845dbcd6346ab`.
Fresh8861/8862 was NOT restarted: its exact image reservation remains busy.
Existing live QA tabs on8861 retain pre-capability loaded UI; its served checked
static bytes are newer, so those tabs must not reload against the old Python.
No absent-field compatibility fallback or concurrent API writer was introduced.

Final independent gates are PASS: V8 full Python 1,227 tests; frontend 582 tests;
V7 unfiltered full browser 204 tests; frontend and E2E typechecks, lock check,
API F401 lint, diff check, wheel build and wheel-installed smoke. Independent
source review has no blocker. Full 847-file final fingerprint:
`761a22ec55021b22a218d82569d2f0767600a8bf818f3f220ce5155adc2730c7`.
During the browser run only the authorized Python unit-test module changed;
the other 846 product/E2E/harness/static inputs remained identical. This is not
a claim that every input stayed unchanged. Prior interrupted/checkpoint gates
remain historical, not replacements for these final gates.

V7 Python had two failures: its dependency-invalidation fixture now began with
advisory policy, so advisory→advisory correctly remained ready rather than stale.
The single-file test correction explicitly tests advisory→strict invalidation and
advisory→advisory no-op for direct/draft saves, with unchanged no-op revision and
exact draft consumption. Focused module: 11 PASS/2.85s. Production behavior and
bounds were not weakened; V8 full Python includes this correction.

Durable gate artifacts live in `.local/full-creator-e2e-repeat-2026-10-07/gates/`:
`independent-final-v8-python.log`, `independent-final-v8-before.json`,
`independent-final-v8-python-after.json`; `independent-final-v7-browser.log`,
`independent-final-v7-before.json`, `independent-final-v7-browser-after.json`;
and `independent-final-v7-{frontend,typecheck,lock,lint,diff,wheel,smoke}.log`.
`independent-final-v7-python.log` retains the failed attempt, not a passing gate.
Wheel SHA256: `82bee9d078bcd01c4001183adf25d2661ea778dc0d546aa2c20b20d8544bdcde`.

Qualified software is activated on normal8841 and its exact source is published.
Served JS matches the exact checked hash above. The required runtime capability is
`intentGeneration=unavailable/not_configured` for normal's bare composition, not
an inference PASS. Normal Rain's four managed-asset rows each expose non-null
provenance; Wind has zero assets. Normal Art has no completed candidate assets,
so an additional candidate HTTP comparison was NOT EXERCISED: no applicable rows,
not a product regression. No owner data was seeded to manufacture coverage.
The real E2E remains PARTIAL: native image continuation requires separate human
authority; remaining media routes and controls are not qualified by fixture gates.

Parent protection recaptures match the baseline aggregate exactly:
`df1716a80d93bdf9aeaf2565464ac030340ab035cf86198d5355befea075f2a5`.
Scope is two owner DB schemas/rows, Wind17+Rain67 managed files and three protected
configuration hashes/modes/UIDs, not the global QA registry/application DB.
Root's final read-only recapture at18:24:32 matched this exact baseline and final
847-file source fingerprint. Post-activation recapture at18:34:54 again matched
the baseline exactly. Normal is idle (busy:false/zero active tasks);8861 retains only
the exact frozen image reservation, without restart/reload/send. Root receipts:
`round2_root_activation_http_smoke`, `round2_root_activation_provenance_smoke`,
`round2_root_post_activation_protection`. No full E2E acceptance is implied.

## Current coverage and explicit gaps

| Contract | Current qualification | Remaining scope |
|---|---|---|
| E01–E04/P01–P05 | Fresh UI Brief/source/Outline r1, native branch review/Confirm/Apply; actual Outline timeline/table PASS, export BLOCKED_BY_DESIGN | Richer native structure not generated merely for counts |
| E05–E06/selected C graph checks | Separate real structural QA123→222→333 sequence; bypass/unconnected deletion/Undo; Save-close-reopen; partial-key/nonblank C49; real stale-CAS refusal and matched live selection refresh; C44 footage toggles/reversal; C48 legal/refused type/start guards, explicit start/choice/join conversion and exact Undo; C50 endpoint/edge-only deletion/Undo; C51 retain/discard; C55 normal-flow help; preview pixels15–26; C46 actual OS blur automatic380/persisted350 PASS, pixel37 and exact cleanup r33 | Remaining type/kind/ownership permutations; no post-install native revision qualification |
| E07–E09/P04/P06 | Fresh native Cast/Art r1; C01 native delivery/refinement and explicit primary/complement pair revoke/restore; native S01 environment/P01 prop deliveries and reference selection with ACK/readback; final native gallery/provenance/long-text115 and independent pixels | Remaining empty/failed-state pixels and downstream reference-consumption qualification |
| E10–E13 | Fresh Script/Storyboard r1 confirmed; proposal r3 presentation reviewed/installed; ordinary first-shot handoff PASS | Model inference E12 NOT EXERCISED (runtime unavailable); physical direction realization remains unspecified |
| E14–E18 | Three native H3 originals/explicit five-second selected derivatives; raw preview/segment review and reject/reopen/reselect observed; both minimal routes complete with trusted native events,120 frames/0 drops/no error; current203 replay after restore has zero writes/jobs unchanged | Native within-node multishot and revised-media chain remain unqualified; functional playback is not creative/audio-quality acceptance |
| E19–E21 | Native196–197 media-bearing close/reopen/archive/restore,49-file/15-asset snapshot/operator restore,both-route restored playback,typed restored-copy deletion and idle restarts;203 additionally proves delayed archive reads/retained preview/restore without reload,six-view and15-asset preservation. See [recovery](2026-10-08-native-media-lifecycle-recovery.md) and [203 repair](2026-10-08-load-retained-media-qualification.md) | Demonstrated closed-load and archived-evidence defects repaired/qualified; remaining installed-story revision/multishot permutations open |
| E22/C37–C39 | Dedicated whole-product sweep82–115 retained as historical qualification. Current203 adds independently inspected archive/held-read/short-height pixels, truthful disabled navigation, closed-link/matching-refresh recovery and both route-choice pixels at all three desktop sizes; final806 frontend/239 browser PASS,unchanged847-input gate | Explicit state register still lists unobserved visual permutations; no blanket whole-product/all-state or creative acceptance |

### Fresh native identities and review boundaries

Current visual/copy continuation: [whole-product audit](2026-10-08-whole-product-ui-audit.md)
has executed under E22.1–E22.7, not incidental graph-only observation. Published
checkpoints have their own gates; the current report/configuration candidate154
passes220 browser/688 frontend with868 inputs unchanged; its linked receipt owns
publication status. The earlier209 gate does not qualify these later changes.
The following first-native checkpoints retain historical failure evidence; later
native media progress is summarized in the current coverage table, not retroactive
PASS for the earlier failed or unexecuted operations.

Project `b3a933f7-b6fc-40e3-826f-5162f95a119a` is the new minimal two-route film.
Brief/Outline/branch/Cast/Art/Script/Storyboard used supported first dispatches.
Cast's capacity failure was recovered once on the SAME job with explicit human
continuation authority; no blind resend. Cast is one offscreen Lin, half-painted
F2 style, not same-appearance or live-action creative approval. Frozen F3 Art,
Script and Storyboard follow author-selected live-action and no visible people.

Art r1 hash `640131312426c031d557214faf59696a9ff125880f32a5d3e9b86dda48e166df`;
Script r1 hash `e861b07e03c5ab51f01dbbb5257f47d91a86501b3002e6900267c693bd325be7`;
Storyboard r1 hash `375f1afd164e2f8a6cadf2f4076d0778e3ae4f0b0bf4a046617c3b7361031d06`.
Storyboard's one turn completed normally after1,440,093ms; report17/17 includes
recipe-library skip, placeholder Picture1 and unspecified physical east/west
realization. Pixels28–31 qualify visible report reading;27 does not.

Authored-intent checkpoint r2 hash `dec232ca6958789678713689bb68f53e5f2a21df77ec0a24a130b14225fc72d6`
has nine source-bound author intents (`suggestionOrigin=none`,
`reviewState=author_saved`, absent model provenance). Only presentation_required
remained then; later functional presentation classification/install is below.
No inference retry or invented physical direction.

Image `ij_5be49304cccb4b1bbbc215f08b2f75cd` stopped at committed-source preflight.
Frozen request hash `9bf2758335113c686f921d6f6f283e867911552c6762f8e39669389a483ce3ba`.
No image/completion exists. Preserve request/reservation; SAME-task continuation
still awaits separate human authority. Queue/package state is not native
execution status. Native Scene/Prop/pair/keyframes/H3 have not been exercised.

### Demonstrated repairs and separate evidence

Persisted-provenance omission is repaired in the shared public projection
(ADR0125), including earliest declaration ordering/null-vs-unknown semantics.
Character/shot disclosure-owner omissions are also repaired without inference.
Long-note layout initially stretched sibling actions; intrinsic card alignment
and all-sibling guards now pass. Four retained corrected1280/1700 pixels were
directly read by writer and parent; FAIL pixels remain separately retained.
These long-note fixtures do not qualify native image delivery or legal rights.

ADR0126 static Script/Art/Storyboard/Cast readers preserve archived bytes/hash,
CSP/empty sandbox, actual images, native disclosures and anchors. Pinned scripts
remain forbidden. Original live readers and final Script owned-note suppression
passed; duration/scene-table notes remain visible. Parent inspected38.
Retained8851 QA project `4ede8a69-bd36-4e3e-9e6f-5678181a29fa`, separate from
the fresh8861 native project, showed raw English as primary guidance in pixel40;
typed stale status now owns Chinese guidance, unchanged raw diagnostics remain
inspectable under technical details. Live42/43 preserve that retained project's
installed proposal r3 hash
`0dbdbfd4f3a89bf2bc7af418556cbaaaec74f785d3bd92cbcc37f3bf9992d653`.
No unsupported post-install reprepare or automatic regeneration is promised.
This is not the fresh native installation, whose current r3 hash is `ef1d922c5cb266cb5192d9a1f49846f46d19a77bb151c0b4d7f5d9019b8da6bd`.

Runtime-only intentGeneration capability (ADR0079) is available iff both service
owners are wired, never persisted into proposal/hash; typed503 refuses before
jobs/writes. Unconfigured UI disables service operations but retains authored
intent saving. Strict declared preset validation now precedes installation/key
bootstrap (ADR0011); explicit CUSTOM remains valid, no migration/relabel fallback.

### Structural and recovery readback

Structural project `0eabd058-b8a6-4ad1-8764-d2bbf11155be` retained exact unfinished
edge JSON and two-line prose through Save-close-reopen without Confirm/Apply.
C49 join `join-a5801402-05aa-52b8-a238-6e90dd2e660f` retained nonblank partial keys
`lamp.partial_QA_`/`lamp.unfinished_QA_` through blur/mode/select/save/close/reopen,
server draft53/baseCanon0. Blank separators/trailing list newline normalize by
the typed list codec; that is not nonblank content loss.

Matched8851 UI-origin QA `274ea714-6506-4396-9520-f1b818d79919` independently
proved stale draft3→4 refusal, no repeated stale POST, explicit reread preserving
this tab's surviving join despite another tab's stored start preference, newer
prose readback and new preview Cancel. Pixel39 qualifies the corrected selection.

Snapshot `20261007T171218926407Z__540792a9-a7e1-4436-b207-4ecbcde33ec5` was created
by UI. Operator restore into separate `.local/full-creator-2026-10-07/e21-restored-outputs`
has byte-equal project.sqlite3; no second API/writer or configuration restore.
Actual archive/unarchive and wrong-name/cancel/exact-name typed delete passed for
disposable brief-only copy `1154579c-dc16-4915-ba9d-e32778bea500` only (API404).
Source QA274 and snapshot retained; this does not prove media-bearing deletion.

C51 on QA274: unsent two-line prose retained by 保留草稿, then separately explicit
放弃图草稿 cleared draft/Undo. Server draft:null/baseCanon0 and original nine node IDs;
empty start title/prose, Undo disabled. Pixel45 directly read by writer/parent.
No accepted content existed, so accepted-media preservation is not claimed.

Graph18 pixels qualify readable/clamped graph-area editor, three horizontal
siblings, curved joins, footer, fixed dark composition under both color preferences.
Top graph-area clamp intentionally prevents literal viewport-only centering.
Pixel26's document selection is a prior nonqualifying attempt; clean pointer34
has empty selection before/after. No OS blur or six-sibling extrapolation.

### C55 current root cause, repair and retest

Pixel44 demonstrated focused help intercepting the required input. The owning
ContextHelp CSS absolutely positioned the explanation below the trigger, contrary
to its shared dock contract. Group-owned normal-flow dock now follows the five-field
grid; one active label/content, exact active-only aria-describedby, focused/pinned
priority and trigger-scoped Escape remain. No pass-through, clipping or focus weakening.
Two unit tests and both focused browser tests PASS12.5s; both typechecks/build PASS.
Changed legal input values plus exact restoration are tested, not only same-value fill.

Actual QA274 all five hover/focus/pin/Escape controls at1700×900,1280×768,1280×460
have own help text, no field/dock overlap and unforced associated/next input clicks.
Durable46 top views qualify unobscured fields;47 at1280×768 shows readable dock.
47 short view alone did not expose the dock and is not readability proof; ordinary
wheel scrolling reaches full dock/next settings in48 at1280×460, directly viewed.
Save scroll visibility is not save-action acceptance; existing Brief save checks
remain separate. Parent directly reviewed46-1700/47-768/48-460 and independently
ran both unit tests PASS305ms; source review closed without blocker. First live
alternate-value loop transiently made nodeBudget1/endingCount3 invalid and was
refused by background Brief validation. Exact values restored and error ordinarily
dismissed; no accepted write. Fixture alternatives now increment within valid
ranges instead of reducing node budget below ending count. Existing pinned help
closed on the first repeat-click observation; explicit Escape reset plus changed
values1/2 retest preserved pinned help. All15 pairs changed/restored; no blanket
claim that every transient combination was collectively valid.

## Final finite structural checks — 17:41 UTC

On QA274, edge `edge-11dfd08f-d8ab-5f56-bf5a-9e65035a0bdb` terminal cleared via
preview/Confirm and restored to `node-6dfd1b52-dfa7-591f-8c34-aa078cc9a97f`;
nine nodes retained. Delete EDGE removed only that connection, not either node;
Undo restored the same identity/target. C48 current-start type select is disabled,
and nonstart start option disabled. Connected scene `node-f0aa134f-bed2-5703-b302-64b585a7d1c4`
to ending correctly refused out_degree; scene to decision refused edge_kind.
After two failures, reassessed the edge/type contract rather than bypassing it.
Cancelled add-node dialog without preparing/adding a tenth node; deleted outgoing
`edge-0f415931-b5c7-582a-bb3f-31b673b223aa`, then legal scene→ending preview/Confirm
succeeded. Undo restored scene type; second Undo restored exact outgoing edge.
No complete type/kind permutation claim.

34s free-form exploration17:40:26→17:41:00 inspected ending Story/Production,
Professional layout/scroll and Creator join without a predetermined expected
sequence. No new defect. Final explicit discard restored exact original nine IDs,
draft:null/baseCanonical0/Undo disabled. No Confirm/Apply or accepted-media claim.
Presentation classification was authorized as functional QA, not creative/media
approval. Initial keyboard/pointer selection attempts were no-ops, not product
qualification. Plain readonly textarea reproduces the same behavior; editable
counterfactual arrows work. Ordinary native Shift-click works on both plain and
current readonly fields. Exact current source0:15 selected the lamp-stays prefix,
active:true/disabled:false, then Split produced two exact fragments with original
source unchanged. Native selection and existing full presentation fixture2 PASS22.1s,
no setSelectionRange or DOM mutation. Nine-source classification is paused to
prioritize source/gates at that checkpoint; later normal classification is below.
No image/H3 send, lease clearing or image continuation occurred.

## Uniform shot-policy cleanup — 17:54 UTC

Root/independent audit confirmed a compatibility split: absent stored policy was
strict while absent new-project input became advisory through helper stamping;
gate hashes excluded implicit policy. Owner's cleanup instruction supersedes this
dated ADR0080 clause. One current ProjectBrief default is now advisory; explicit
strict remains strict, helper/export/import/calls removed. Effective policy is
always hashed: implicit advisory equals explicit advisory, differs from strict.
Missing-field read preserves exact stored Brief/revision; no migration/read-time
write. Protected owners have explicit advisory, unchanged semantics. Strict
regressions now explicitly declare strict rather than weakening bounds.
Shot-policy/domain/source-outline34 PASS2.15s; bridge/generation63 PASS25.20s;
Idempotent missing-vs-explicit advisory creation included in final34 PASS3.53s;
API F401 lint and diff check PASS.
ADR0080 retains dated historical clauses with precise superseding current decision.

## Fresh presentation/install/handoff — 17:58 UTC

After source readiness, ordinary Shift-click source selection/splitting and role
controls classified all nine sources. Every fragment concatenates exactly to its
original source; source coordinates/hash/frozen evidence unchanged. Physical
renderings copy source verbatim; player opening→choice is runtime_choice; abstract
east/west state/termination and explicitly unspecified realization are review_only
with honest reasons excluding invented mechanisms/colors/signals/people/rescue
events and creative/media quality acceptance. Physical restrictions remain physical.
Pixel51 directly inspected the unspecified west-state reason and full restrictions
before Save/install; it does not independently prove installation.

Functional-QA completeness checkbox and Save produced proposal r3 hash
`ef1d922c5cb266cb5192d9a1f49846f46d19a77bb151c0b4d7f5d9019b8da6bd`,
reviewed:true/installable:true. Explicit Confirm installed normally: status accepted,
hasInstallation:true/installedStoryboardCurrent:true; three scenes/three exact5s
cuts, same east/west outcome IDs/coordinates and original two10s routes. No image
or video generated, no implicit media selection. Ordinary Continue opened
`shot:node-b64d6809-7161-5042-a7f8-a3c5c854e733-s1-c1` in the canonical workbench.
Pixel52 directly inspected5s/current shot/no-original candidate boundary; readback
has both route filters, exact physical opening actions, Lin unchecked/S01 selected/
P01 checked. No shot approval or further native task sent at this checkpoint.
Parent's read-only GET at18:02 independently corroborated r3/hash, accepted status,
reviewed/installable, three scenes/cuts and current installation. Pixel52 plus that
GET qualify post-install handoff; pixel51 remains pre-install classification evidence.
