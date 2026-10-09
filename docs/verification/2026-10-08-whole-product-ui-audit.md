# Whole-product visual and text audit — 2026-10-08

October9 continuation: [native rebuilt-production evidence](2026-10-09-native-rebuilt-production.md)
adds real original/segment playback and preserved quality caveats. Two E22 defects
have source repairs qualified in66b1cbd: overlong composition-as-title and raw
video-state badges. A review found and closed the related selected-original versus
selected-segment status/navigation mismatch. The hand-only identity gate remains
an open semantics question. Its raw English refusal is repaired in source95074b1
under ADR0143; matching native backend activation and actual retained-shot409
guidance are verified in the rebuilt-production receipt's09:34UTC checkpoint.
The [revised recovery audit](2026-10-09-revised-project-recovery.md) additionally
finds and repairs standalone Play mislabelling archived media as missing clips;
these changes do not complete the whole-product state matrix.
Nine revised Art report captures additionally verify full reading and modal
close/reopen/focus at the three desktop sizes. The report's skipped-Cast claim
is a confirmed generation-context defect: validation receives Cast, but the
upstream renderer recomputes gates without it. Retained HTML remains unchanged;
an owning-layer repair is still outstanding.
The revised East native waiting card is directly inspected at all three desktop
sizes. Queueing is distinguished from completion, but the external specialist
capacity failure is not surfaced in Plotloom. The1700 capture also demonstrates
cropped faces in media candidate thumbnails, caused by the shared96px cover-fit
rule. The October9 08:27UTC continuation repairs that shared rule to contain-fit;
the comparison panel's separate contain-fit did not qualify thumbnail cards.

### H3 aspect-choice layout — October9 08:48UTC candidate

The prior refusal frames exposed a form incorrectly using `.notice`'s horizontal
flex row; the nonshrinking heading left little width for prose and radio labels.
A scoped `h3-aspect-options` class now stacks the notice contents and aligns each
radio with its full-width label. Defaults, disabled eligibility, consent, request
fields and provider handling are unchanged. No narrow-screen support was added.

The extended existing H3 browser journey failed before the repair with a105.6px
label width at1700px. After repair it passes12.2s, including all three desktop
viewports, notice/control containment above the fold, labels wider than400px,
nonoverlap,16px controls, no page overflow and selecting every choice. Reject
keeps source reading disabled; explicit crop or padding enables it. The journey
then retains its exact frozen crop request, offline submit/reconcile, segment
selection and actual backend-restart checks. This is a product-shaped offline
fixture, not additional native video generation or quality acceptance.

Root and independent GPT-6 Luna/Max review directly inspected all three repaired
screenshots, with no material findings. Before capture exists at1700px; earlier
identity-refusal frames separately show the1280px defect. Evidence directories:
`output/playwright/native-intent-2026-10-08/h3-aspect-layout-before/` and
`h3-aspect-layout-after/`. All872 frontend tests, types and deterministic build
pass. The combined full browser gate passes243 tests in7.9m. Product/test diff
SHA256 `72db13c1b2591786b7a3b601d92ba2723ce1ca658af20a75115d0428fb36774f`
and all three new test-file hashes match the pre-run snapshot. Evidence lives in
`frontend/test-results/identity-and-aspect-full-gate/`. Normal8841 is unchanged.

### Identity-review refusal — October9 08:40UTC candidate

The existing still-preview/video gates correctly reject identity-bound keyframes
without a current passing review. Their generic English refusals and the panel's
preview-only explanation hid the video consequence. ADR0143 introduces one typed
Chinese diagnostic with exact shot/binding identity. Both API compositions use
the shared serializer; eligibility and dispatch predicates remain unchanged.

The initial implementation registered a handler only in the general composition;
the real project-folder tests caught the resulting generic code. The shared
serializer repair passes both compositions. Browser checks use actual endpoints
for missing and explicitly failed reviews, exact refusal identities, no created
jobs/previews, and the existing subsequent explicit-pass preview flow. The UI
correctly disables still-preview creation; its server refusal is tested directly,
not by forcing a click on a disabled control. A failed helper iteration and a
missing approval/revision fixture payload are retained, not product failures.

Four focused browser journeys pass (final identity image journey20.8s; three adjacent
H3/still/restart journeys10.1s),124 focused Python checks and all872 frontend
tests pass; application/E2E types, deterministic build, lock and scoped lint pass.
Independent GPT-6 Luna/Max review caught an incorrect disclosure name in the
initial guidance. The final message names “准备与参考 · 图片、角色、导入”, and the
browser now asserts that this exact disclosure contains the identity panel.
The reviewer rechecked source and all three final frames, closing the finding.
The11 identity/graph Python checks and browser journey pass again after the
wording correction. Full Python finished1,414 PASS/1 FAIL in22m36s. Its process
started before that wording-only correction, so it is not a frozen final gate.
The sole failure was the authored retained-coverage inventory: this test's old
inline409 assertion/hash had not been reconciled with the new response variable
and typed diagnostic assertions. Comparing the complete test confirms original
missing-reference, delivery, passing-review and stale-reference behavior remains;
the new assertions strengthen refusal identity/copy. Only this catalog entry's
hash/assertions were updated; no checker, baseline or disposition was changed.
All four inventory/identity API/storage tests then pass2.46s. Earlier final-copy
11 focused checks remain valid. No claim of a second all-green Python run.
The final combined wheel builds and passes installed smoke outside the checkout;
lock, scoped Ruff and diff checks pass. Native8865 still loads66b1cbd Python;
normal8841 remains unchanged. The existing independent reviewer checked the
inventory delta and AST-extracted hash, finding no weakening or unrelated edit.
Root directly inspected all three `identity-refusal-{width}x{height}.png` frames
at1700×900,1280×768,1280×460: the complete refusal is readable without horizontal
overflow. Evidence is under ignored
`output/playwright/native-intent-2026-10-08/identity-refusal-reviewed-guidance/`;
the earlier `identity-refusal-verified/` captures pre-review wording; sibling
`identity-refusal-disabled-control-failure/` and
`identity-refusal-fixture-payload-failure/` preserve the harness failures.

Those frames also expose a separate1280px layout defect: the H3 aspect-mismatch
notice lays prose and three radio labels out as competing flex columns, squeezing
the labels into narrow vertical text. Its owning `.notice` flex layout needs a
scoped form layout, not shorter or less accurate safety guidance. The later
H3 layout section above owns its repair; identity-copy checks alone do not
qualify the aspect-choice layout.

No native backend restart or dispatch occurred. The held East job remains a
terminal pre-tool capacity failure (same thread/turn confirmed08:40UTC), not a
running generation. Native8865 still loads66b1cbd backend; checked static was
rebuilt, but the new server refusal is only qualified on isolated test runtimes.
Normal8841 and protected projects/settings remain untouched.

### Thumbnail framing repair — October9 08:27UTC

Root cause: `.media-candidate img` combined a fixed96px height with `cover`,
cropping portrait heads/feet and source edges. The shared presentation rule now
uses `contain`; card height, selection semantics and asset bytes are unchanged.
No backend, generation contract or historical delivery was rewritten.

New `reference-gallery-layout.spec.ts` regression imports synthetic240×480 and
640×240 edge-marker PNGs into a disposable project. It failed on the original
`cover` rule, then passed at1700×900,1280×768,1280×460 with decoded dimensions,
96px contain-fit, centered positioning, no horizontal page overflow, unchanged
selection and readable expanded provenance. Five focused browser journeys PASS
(21.6s): gallery directions, selected identity sources, new thumbnail check,
image-job/refinement/stale delivery, and real backend restart with retained still
selection. Application/E2E typechecks and deterministic build PASS. This CSS-only
change does not require or claim a new full Python gate.

Root directly inspected three fixture and three native gallery captures; an
independent GPT-6 Luna/Max read-only review inspected all six and found no material
issues. Native8865 readback has13 decoded gallery images, including three1024×1536
portraits, all contain-fit; their faces and feet are now visible. The medium
viewport naturally ends before some actions; actual short viewport shows the
first-row controls. No project writes, dispatch, or service restart occurred.

Evidence under ignored `output/playwright/native-intent-2026-10-08/`:
`thumbnail-crop-regression-before/` retains the failing screenshot/trace;
`thumbnail-contain-verified/` retains focused test pixels;
`native-complete-thumbnails-{1700x900,1280x768,1280x460}.png` records real images.
Checked and8865-served CSS SHA256:
`c419fc5825c77b8e10ef4a280d88c6f800c629c666b415dbf072ac511e7dd9fe`.
JS remains `7d3a70d77a31325e0cdd5eb0d83db20eef07dfdbf0f5df7889330a41959c9bf6`.
Normal8841 is unchanged. The broader E22 state matrix and native revised routes
remain incomplete; this is framing verification, not creative acceptance.

Status: **EXECUTED / PARTIAL COVERAGE**. Included in the current full E2E run,
with scoped repairs verified; unqualified states remain listed below. This is
not full lifecycle acceptance. Artistic image/video quality remains owner/H3 scope.
The [native intent checkpoint](2026-10-08-native-bridge-intent.md) adds the exact
initial Bible failure/retry audit at all three desktop sizes and its page-neutral
recovery wording repair. It does not close other Bible states or native revision.
The [current-story rebuild checkpoint](2026-10-08-current-story-rebuild.md) adds
directly inspected stale-proposal/installed-production pixels at all three desktop
sizes, currentness-safe editing and accurate rebuild guidance. It is an isolated
software fixture, not native revised-story playback or a normal-service activation.
Latest [203 read/lifecycle checkpoint](2026-10-08-load-retained-media-qualification.md)
is published and healthy as `6284118`. It adds actual closed-route/failed matching-refresh,
delayed archive reads, retained native preview, restore without reload and independently
inspected final archive/short-desktop pixels. Both minimal current routes also replayed
after restoration with trusted ended events and unchanged media. This closes those
specific gaps, not within-node multishot or installed-story revision. The older
checkpoint statements below retain their original qualification boundaries.
The [Cast/Art report checkpoint](2026-10-08-cast-art-report-ui-states.md) adds96
independently inspected report pixels and actual native toolbar-clearance reading.
Its focused18 journeys and fresh unfiltered189 (236 tests) pass; earlier182 was interrupted by the owner's
computer crash, retaining a separately completed native playback failure. Neither
the interruption nor a later plain-player control closes that diagnosis.
The later [native preview error UI checkpoint](2026-10-08-native-preview-error-ui.md)
extends failure-state coverage; it does not qualify the native decoder or all routes.
The [typed Cast/Art guidance checkpoint](2026-10-08-review-context-diagnostics.md)
adds36 independently inspected disposable diagnostic frames and three root-inspected
native notice frames, preserving exact technical evidence and prerequisite ownership.
Executable`c26920b` is published and activated; fresh1256 Python,723 frontend and
unfiltered236 browser tests pass locally. Exact-head CI37786734259 has completed success.
The [reference-gallery checkpoint](2026-10-08-art-reference-eligibility.md) repairs
stale Art's image-task affordance and contradictory disabled-field guidance;
its own qualification and activation are tracked separately. Executable `3ad91e4`
is healthy on normal8841 with fresh737 frontend/unfiltered236 browser PASS;
six directly inspected normal Gallery/controls frames make no writes. Its full
exact-head CI37801077786 passed verify and both browser shards. This does not
close native-media/revision gaps.
The [native-route/end-frame checkpoint](2026-10-08-native-routes-endframe-qualification.md)
adds actual both-route terminal pixels and end-frame pending/error/recovered
qualification. Expanded long raw diagnostics now wrap instead of widening the
page; all three actual native after frames were independently inspected.
Its current repair gate is separate; broader state/native/revision coverage remains PARTIAL.
The earlier [post-reboot native checkpoint](2026-10-08-native-decoder-recovery.md) separately
qualifies the opening original/segment/selection slice and three actual incomplete
Play viewports. The newer checkpoint closes minimal all-route playback, not
multishot, revised-media or decoder-cause gaps.
The [reader/gallery/Bible/run checkpoint](2026-10-08-reader-gallery-ui-states.md)
extends prerequisite, read-failure, empty and archived-state coverage. Its latest
gate and publication identity are recorded separately, not inherited from earlier gates.
The [draft/credential/lifecycle reading checkpoint](2026-10-08-dialog-credential-ui-states.md)
adds actual consent/recovery and snapshot-disclosure checks; its final gate is
qualified locally, and it does not close the remaining full-product state matrix.
That checkpoint is published as executable `0c91067`, serving exact assets on
normal8841; its unfiltered exact-head remote CI37753998839 has completed success.
The [original-report/stale-Art checkpoint](2026-10-08-static-report-art-ui-states.md)
adds72 directly inspected native/fixture captures, plain shared report copy and
actual West route/instruction/report reading. Its full browser gate finished218/2;
the earlier216/4 setup failures, native clock failures and upstream Outline duration tile
remain explicit. This does not close the whole-product or native-media matrix.
The [frozen-configuration checkpoint](2026-10-08-frozen-profile-ui-states.md)
adds all18 inspected desktop configuration-failure/settings frames, clearer current-edit vs
current-use labels and action-neutral guidance, plus three re-inspected explicit-refresh
frames. Final unfiltered154 browser qualification passes220 tests6.4m, with868
inputs unchanged. Executable35cc75b is published on normal8841; exact-head remote
CI37763010686 has completed success. This does not close the open state matrix.
The [conflict/retained-draft checkpoint](2026-10-08-conflict-recovery-ui-states.md)
adds actual two-tab conflict/failure/retry and eighteen independently inspected final
desktop captures, including explicit visible local-discard feedback and exact lineage
preservation. Final unfiltered167 passes224 browser tests6.5m, with875 inputs
unchanged. Its publication is recorded separately; this does not
close the other view/state or lifecycle/native-media gaps.
The [Source/help checkpoint](2026-10-08-source-help-ui-states.md) extends initial
pending/failure/empty, retained dirty text, explicit retry and archived guidance.
It also separates hover from keyboard/pinned help and checks the full trigger,
not merely its centre, against the actual toolbar. Final qualification is tracked
there; prepared tasks, stale Outline and remaining Creator/Pro states stay open.
Baseline: [full lifecycle ledger](2026-10-07-full-creator-e2e-repeat.md);
reusable entry: [E22.1–E22.7](../creative-workflow/graph-workbench-acceptance.md#e22-全产品视觉与文案专门检查).

## Earlier scoped delivery

Executable source `46ab176b92d6b4dec2081ac1acd78c4109ff41ec` is committed and
pushed to `origin/main`. Normal8841 returns HTTP200 and serves the exact verified
JavaScript hash `258e1fee4a4c5fb3824a5492e00b3e0072a28da368f217a6dadc18c16a49203c`.
No backend restart, protected-setting write or owner-data mutation was needed.
The unfiltered [remote CI run](https://github.com/Wenjun-Mao/plotloom/actions/runs/37733050839)
is in progress at delivery; remote success is not yet claimed. This scoped
delivery does not close the broader lifecycle/media or visual-state gaps below.

The later [reading-state checkpoint](2026-10-08-reader-gallery-ui-states.md) is
published as executable `ff1197a`; its unfiltered217 browser gate,666 frontend
tests, serving hashes and exact owner-protection readback are recorded there.
Its exact-head remote CI37745186133 is still running at publication. This is
additional scoped evidence, not completion of the remaining state/lifecycle matrix.

## Scope and evidence discipline

Audit primary and Professional views, settings, readers and recovery messages for
spacing, alignment, scrolling, actionable states, terminology and **weird wording**:
unnatural translations, unexplained jargon, awkward sentences and labels that
misstate what a handler does. Use 1700×900,1280×768,1280×460 only; narrow/phone
support remains retired. Screenshots exist under
`output/playwright/full-lifecycle-2026-10-07/`; capture alone is not a visual PASS.

Native read-only sweep uses the disposable project
`b3a933f7-b6fc-40e3-826f-5162f95a119a` on isolated8861, with structural QA in a
separate tab. No settings saved, directory mutations or provider dispatches during
this sweep. Loaded content is awaited; initial Source loading and Pro timing
captures are excluded from qualification. Original creative prose and immutable
report evidence are not rewritten for cosmetic consistency.

## Current view/state coverage

| Surface | Actual evidence / inspection | Remaining scope |
|---|---|---|
| Brief, Creator, source, Pro |82–85 native/QA;109 loaded review captures, long graph and all18 Pro viewports; root/independent direct pixels | All applicable state permutations not yet pixel-qualified |
| Cast/reference gallery |80b/86/115 native confirmed content;129–131 disposable initial failed-read, confirmed-no-images and archived-guidance viewport captures; October9 retained-refresh failure/retry plus nine lower-control frames at all desktop sizes, root and independent pixel review | Warning/retry/recovered heading and disabled lower controls qualified; exact Cast/reference response preservation and zero-write check in rebuilt-production receipt. Other proposal/report states remain open |
| Bible |88 native populated premise;129–131 disposable selected character/location/prop top/bottom and archived-character deep link; native-intent receipt initial503/retry at all desktop sizes, refreshed October9 | Initial transport failure/retry is covered; other archived entity permutations remain open |
| Art, Script, Storyboard/production review |87–89 native top/middle/bottom;94 saved/selected;109 loaded heads;112 repaired Art/production viewport pixels at all three sizes;113 actual native optional-Art-task scrolling at all three sizes, zero writes | Deeper selected/failed/stale state permutations not yet pixel-qualified |
| Script/Storyboard readers |90 native East/West;129/130 seven explicit reader states ×three sizes;145 actual native West selection, expanded instructions and original report, all directly inspected; optional failure retry preserves Script/route and performs no writes | Other reader/report permutations remain open; West slice now qualified separately |
| Play |90/95/109/112 prerequisite observations retained;194 actual two-missing-route state;195 and203 actual minimal both-route terminal playback; native-intent receipt establishes fresh four-clip/two-route baseline including two-shot opening | Baseline within-node multishot established; revised media chain and every revised route remain open; creative/audio quality is separate |
| Specialist/provider settings, Home/directory |91 native top/bottom;93 repaired overlay hit/scroll/Close;109 desktop views;112 initial top, text-ID scroll and image-ID scroll pixels directly inspected at all three sizes; readable directory times rechecked | Other operational states not yet pixel-qualified |
| Trace, repair, Beats |97 native idle/populated;109 all18 Pro and three enabled exact-repair viewports;112 one-line Add Scene;137/140 Trace/repair and Inspector pixels directly inspected;141 changed running-event recapture | Additional native event/operational permutations; running fixture is frozen-key blocked, not native execution |
| Shot/media details |83/110 reading observations;194 original/segment playback and technical-only selection;195 reject/reopen/reselect/end-frame fault reading;203 actual archived retained preview,held currentness reads,restore without reload and independently inspected final guidance/bottom actions at all desktop sizes | Minimal other routes and media-bearing recovery established; multishot/revision,remaining subcontrol permutations and creative/audible quality remain incomplete |

No page-width overflow observed in the measured native89–91 cases. This does not
prove every view or state. Captured larger frames not explicitly inspected remain
unqualified. Sandbox-blocked scripts in immutable static reports are an intentional
reading boundary, not permission failures to solve by enabling report scripts.

### Explicit state register for the next pass

This register is not a claim that every state passed. `NOT EXERCISED` below means
the named pixel/state slice has no qualifying receipt, even where handler tests
pass. Existing capture numbers identify intermediate audit checkpoints, not an
assertion that all pixels were recaptured against the latest source. Every new
entry must bind its exact candidate, native/fixture class, viewport and inspected
file; do not inherit a PASS from a different state or source revision.

| Surface / state slice | Class and retained evidence | Visual result / next check |
|---|---|---|
| Script reader, populated read-only top/bottom | Native90, six PNGs at all three desktop sizes; later145 native West route/instruction/report frames directly inspected | Original90 top retained a pending Storyboard tab; later145 qualifies loaded West reading separately. Shared wording repair and exact original-report boundaries are recorded in the report checkpoint. |
| Storyboard reader, populated read-only top/bottom | Native90, six East PNGs; later145 native West anchor/full-prompt/report frames directly inspected | East90 does not itself qualify West; the later145 slice separately covers West/instructions/original reports. Other permutations remain open. |
| Reader, no project / missing or reopened Script / stale Storyboard | Explicit fixtures129/130, four states at all three sizes, independent direct inspection | Scoped PASS for prerequisite/refusal and exact preparation-owner links; not native generation. |
| Reader, initial failed read / pending or failed optional Storyboard / named retry | Explicit faults129/130, three states at all sizes; same-Script/route and zero-write guards | Scoped PASS; Storyboard retry is isolated, missing content is not a transport failure. |
| Original video, collapsed / expanded native error | Explicit read-fault fixture120; both states at all three sizes, root/independent inspection | Scoped PASS; candidate and handler limits in the preview checkpoint. |
| Segment video, collapsed / expanded native error | Explicit read-fault fixture120; both states at all three sizes, root/independent inspection | Scoped PASS; not native successful playback or media selection. |
| Native original/segment terminal and selected state; Play missing two route shots | Native194 full CDP/job/HTTP records, inspected terminal/selected pixels and Play at all three desktop sizes | Finite technical PASS in the recovery receipt. Static“待审片段” is an optional wording refinement; selected option/status are accurate. No all-route/multishot or creative/audible acceptance. |
| Native both-route completion; end-frame pending/error/recovered and expanded long diagnostics | Native195 route CDP/events/full readbacks; three desktop GET-fault/retry viewports and independent source/pixel review | Finite minimal-route technical PASS; long-error/read-authority repair qualification in linked receipt. Same-node multishot, revised-media and remaining lifecycle states stay open. |
| Project closed-link / failed matching refresh; archive held-read / retained preview / restored current story | Native198/199/203, exact disposable UI-origin project; final203 five archive/held-read/bottom-action pixels root and independently inspected plus both route-choice pixels at supported sizes; six API views and15 assets unchanged | Scoped PASS in203 receipt: truthful unavailable state,preserved matching content/drafts,temporary authority withdrawal,read-only retained preview,accurate disabled navigation and fresh-read restoration. No generation/media-selection writes; full revised-story/multishot acceptance still open. |
| Cast/gallery, confirmed populated / expanded provenance | Native115, top/details/bottom at all three sizes | Scoped PASS; retained confirmed content, not an empty or failed read. |
| Cast/gallery, confirmed-no-images / initial failed read / archived guidance | Disposable fixtures129–132, final137 twelve PNGs at all sizes directly inspected | Scoped reading-state qualification in linked checkpoint; archived controls remain disabled, no interactive comparison/retry claim. |
| Bible, populated premise | Native88 at all three sizes | Scoped PASS for this form, not the selected entity forms. |
| Bible, selected character / location / prop / archived character | Disposable129–131 and final137, top/bottom pairs18 PNGs plus archived-character3, direct independent inspection | Scoped PASS for retained values, labels, lower-field reachability and disabled archive controls; location is not a scene beat. |
| Art, confirmed plus optional new task | Native112/113 at all three sizes | Scoped PASS for current hierarchy/scrolling; no dispatch performed. |
| Art / Script / Storyboard, stale / dirty / failed | Some fixture109 states and functional guards;145 six directly inspected retained dirty-Art/stale captures and exact accepted-object preservation | Dirty-Art/stale slice scoped PASS; Script/Storyboard and other failure permutations remain PARTIAL. |
| Trace, retained failure / pending cancellation / true idle / key-blocked running |140 twenty-seven directly inspected PNGs, including Professional Inspector;141 three changed running-event pixels; zero-write and cancellation-eligibility guards | Scoped reading PASS after helper/tone/uncertain-kind/timestamp repairs. Native active execution and other populated events remain PARTIAL. |
| Exact repair, eligible / refusal / unknown result | Enabled109 eligible viewport;140 eighteen directly inspected refusal/unknown-state PNGs, exact codes, explicit duplicate-generation warning and zero writes | Scoped refusal/unknown reading PASS; not a new repair/rebuild execution claim. |
| Directory/settings, populated / initial top / scrolled lower controls | Native91/93 and repaired112; all three sizes | Scoped PASS; not operation-in-progress or failed-save state. |
| Navigate / directory Archive / directory Close consent |143 disposable nine cases, three desktop sizes, exact intent/actions and actual cancelled entry points | Scoped pixels/operation checks; final source220 browser/683 frontend gate in linked checkpoint. |
| Project-saved recovery |143 three final recovery frames directly re-reviewed; exact payload Restore preserves canonical r2 | Scoped checks; session-only/reconciliation/busy have functional tests, not separate pixel qualification. |
| Two-tab conflict reload / pending / unsafe failed read / retry / loaded / local discard | Native155 reproduction; final166 five states ×three sizes plus short-desktop discard sequence, all18 directly inspected independently, exact zero-write/local lineage/server-draft guards | Scoped pixel/operation PASS; broad final gate/publication tracked in linked checkpoint. Other scope/graph reconciliation pixels remain open. |
| Snapshot completion / status disclosure |143 actual201 complete; three before failures and three repaired after frames directly inspected | Reading defect repaired; open-only summary reveal preserves normal scrolling. Final gate qualified; does not imply every snapshot/lifecycle failure state. |
| Permanent deletion challenge |143 disposable blank/wrong/exact title ×three sizes, all nine frames independently inspected; Cancel preserves entire project and sends zero writes | Scoped challenge reading/eligibility PASS; actual deletion and lifecycle failure-state pixels remain PARTIAL. |
| Frozen profile: missing key / missing profile / read failure / exact settings |152 eighteen directly inspected fixture PNGs;153 three changed refresh-guidance frames re-inspected; GET-only faults and zero-write/explicit same-job continuation guards | Scoped pixel/operation PASS; final220 browser/688 frontend qualification in linked checkpoint. |
| Source initial pending / failed / empty, dirty refresh pending / failed / retried, archived | Disposable real-server176 state cases, all36 final Source PNGs independently directly inspected, exact zero-write/readback guards; qualification in linked Source/help checkpoint | Scoped pixels/operation PASS; full gate tracked there. Prepared task and stale Outline states remain open. |
| Outline / Creator / Pro, populated owner views | Native82–85 and loaded109; scoped fixes rechecked112 | PARTIAL: remaining waiting/failed/stale/dirty/read-only permutations need explicit receipts. |
| Structural help, pure hover / keyboard focus / pin / Escape |176 exact toolbar/full-control/full-explanation bounds, all48 final help PNGs independently directly inspected; five settings at all three sizes | Scoped pixels/operation PASS; full gate tracked in linked checkpoint. Earlier centre-only171 frames are insufficient for unclipped-control qualification. |
| Script / Storyboard static reports |145 native33 direct pixels: disclosure/top/middle/bottom, West anchor/full prompt, reopen and archive/canonical/no-write guards;145 reader21 West route/instruction/report pixels | Scoped native reading PASS; original report covers all episodes, route reader only selected route. Other report permutations remain open. |
| Cast / Art static reports |181 disposable pinned-renderer fixtures,96 report PNGs independently inspected at all supported sizes;18 focused journeys PASS, original/canonical/hash/no-write guards;184 three directly inspected native Art action viewports;189 fresh unfiltered236PASS | Scoped reading PASS; accepted Cast identity marker is not a rich report, four-role fixture is not native delivery and relationship-heading/list pixels do not qualify the whole map. Publication tracked in linked checkpoint. |
| Native Art prerequisite wording |184 normal Art exposed raw English beside plain StageGuide; successful stale projection lost shared prerequisite ownership | Resolved through ADR0134 typed API/primary guidance in190, with actual activated normal readback. Original184 pixels and raw evidence remain unchanged; no string translation or creative prose rewrite. |
| Cast/Art typed prerequisite and preparation-refusal guidance |190 disposable real-server six cases ×three desktop sizes ×closed/open details, all36 PNGs independently directly inspected; actual preparation409 and exact no-job/retained-state guards; three additional root-inspected native notice captures | Scoped pixels/operation PASS under ADR0134; fresh local gates, publication and activation are tracked in the [typed guidance receipt](2026-10-08-review-context-diagnostics.md). Broader state/native-media matrix remains PARTIAL. |
| Stale Art reference-task affordance |190 retained failure evidence; later five real-server fixture states ×three sizes,30 initial/30 final pixels, actual zero-write zoom/details and exact stale cancel/refresh/cancel; six directly inspected activated normal Rain Gallery/controls frames | Repaired current-head authority and locked-field copy; independent review closed, fresh local qualification and normal activation PASS. Exact-head remote CI in the [gallery receipt](2026-10-08-art-reference-eligibility.md); not every native/gallery state. |
| Outline original interactive report |144 native12 direct top/table/middle/bottom pixels, all sizes; exact archive/project/no-write, bounds/hit and reopen guards | Reading controls/scroll scoped PASS. Raw fractional-minute tile wraps badly at1280; upstream renderer defect UNRESOLVED, original bytes preserved. |
| Revised Script/Storyboard typed stale guidance | October9 current isolated diagnostic bundle: seven simulated-GET captures at all three desktop sizes, root and independent direct inspection; five new backend and five new frontend regressions,18 focused browser checks and242 full browser PASS | Scoped warning/owner-link/technical-detail presentation PASS; that candidate's full1,413 Python gate passed in the native reference revision receipt. The later95074b1 Python run is separate. Fixture pixels are not native stale behavior. |
| Revised native Storyboard r2 report | October9 accepted r2 on same revised native project; root-inspected1700 top/end plus1280×768 and1280×460 top/middle/end, actual wheel scrolling and exact bottom geometry, disclosure close/reopen | Reading scoped PASS. Upstream footer hardcodes2–5s despite frozen2–8s; generation-call and environment-reference claims require owning-layer clarification. Retained report unchanged. |
| Revised native Art r2 enlarged report | October9 current Art report, nine root-inspected top/middle/end viewport captures at all three sizes; real wheel scrolling, exact bottom geometry, zero writes, Escape/focus restoration and explicit Close/reopen | Scoped reading PASS in rebuilt-production receipt. Green skipped-Cast gate remains a report-validation provenance question; original bytes retained, no creative acceptance. |
| Rebuild r5 with retained native intent job | October9 same-project actual preparation; completed task frozen to proposal1 versus current proposal5; three final native desktop captures root/independently inspected | Repaired historical/current provenance. Subsequent explicit native intent review and installation r8 are recorded in the rebuilt-production receipt; intent is no longer pending. Revised media/routes remain incomplete. |

The Outline duration source diagnosis is confirmed in the clean pinned
`shuohao-skills` submodule at `4322897e6d2bdaf66365534fd40194360c75a85f`.
A new-report generation-layer formatter can preserve numeric input, embedded
data and exported JSON, but needs a deliberate submodule/gitlink advancement
and fresh execution-pin qualification. It has not been implemented in this
checkpoint. ADR0086 preserves the retained original bytes; ADR0126 does not
authorize an Outline projection. Do not rewrite the144 report or present it as
repaired by a future-generation-only change.

Next priority: review-state/dialog/help/report
permutations and the remaining native route/report pixels. Reader/gallery/Bible
states now have a bounded checkpoint; unlisted states do not inherit that qualification.
The dirty Archive consent and frozen-key primary guidance findings are repaired
in the linked draft/credential checkpoint; its actual state and qualification
limits remain explicit. They do not imply every dialog/wording state is clean.
Use only isolated QA data for state construction. Never manufacture failure or
archive an owner project just to fill this table.

## Findings, root causes and bounded repairs

October9 native rebuilt H3 preparation exposed raw `prepared` in the primary
job badge (`rebuilt-h3-frozen.yml` in native-intent browser evidence). The shared
video-status presentation repair is qualified at66b1cbd in the rebuilt-production
receipt; retain the original failing evidence rather than reporting this as open.
The current image waiting-state UI was directly inspected at all three desktop
sizes; readable current/history distinctions and check/cancel controls pass only
that state, not the rest of the whole-product matrix.

October9 native rebuild inspection found full English composition
is projected into `shot.title` and repeated as large card/detail headings. Exact
source diagnosis and direct pixels are in the
[rebuilt-production receipt](2026-10-09-native-rebuilt-production.md).
The concise display-identity repair is qualified at66b1cbd in that receipt.
Source composition and immutable reports remain intact; this is not translation
or creative-content acceptance.

| Finding | Root cause / repair boundary | Verification so far |
|---|---|---|
| Prepare actions read like immediate generation | Copy did not follow prepare-only handlers; say准备任务/片段预览 | First repair gate208PASS; no dispatch semantics changed |
| Brief/Creator/Pro/Bible/Beats/Trace/repair guidance exposed jargon or unclear next actions | Primary guidance borrowed implementation terms; natural action/object wording, retaining exact diagnostics | Representative native captures; whole state matrix remains partial |
| Bible premise query also matched Logline | Shared wrapping label included help containing“故事前提”; direct native control gets sibling label and help description; Logline help usesField hint |611 frontendPASS and208 browserPASS; native88 at all three sizes |
| Trace with a retained failed/current run said to start a run | Empty event list treated as no run; guidance now distinguishes running/existing/true idle | Focused state tests in611 gate; native failed-state pixels still pending |
| Art confirmation drift and reference action said“替换为用作…” | Manual approval and reference decision handlers confused with technical acceptance/asset replacement |626 frontend/full209 intermediate gate; native94/96 plain reference boundary and112 Art pixels |
| Confirmed production showed“确认后，将建立…” | Help ignored accepted state; conditional past/future tense | Bridge tests, intermediate full209 gate and112 production pixels |
| Saved presentation review said media“尚未因此获得接受” | Literal technical-acceptance phrasing; plain independent media审核/选用 boundary | Presentation tests and native94 saved-state rendered recheck |
| Specialist heading hidden under topbar | Dialog mounted inside sticky sidebar stacking context; native rect within viewport but heading-center hit returnedHEADER.topbar |92before direct pixels/hit test; move to workspace overlay boundary, three-size hit/scroll/close regression added |
| Missing-video links indistinguishable / long comma-chain notice | Shot prose reused as display identity and deduplicated in prose; use node+scene/shot context and concise count, preserve exact-ID links and structural gaps |38 focused label/playback testsPASS; identical-prose/24-link desktop regression. Independent review found generated qualifier could collide with authored node title; node position now unconditional, with explicit three-node regression |
| Brief and frame-input helpers absent from descriptions | Some callers kept helpers inline instead of using the sharedField hint contract; move text verbatim into hints, retain exact constraints and fields | Brief five-control rendered-description assertions, frame-input regression and626 frontend/full209 intermediate gate PASS |
| Media candidate called“Imported” even for a native generated image | CandidateCard display assumed one ingestion source; neutral“候选图片” label leaves persisted provenance authoritative | Exact import/snapshot selectors updated; no provenance or asset identity rewritten |
| Unknown video reads appeared empty | Initial job array was empty before owned budget/backend/job reads settled; gate production guidance on successful owned read | Six pending/failure/stale-project unit regressions;110 native transport exercise, zero writes |
| Short Brief help could not be scrolled into view | Unbounded form column was sticky; put it in document flow rather than repositioning help downstream | Focused loaded six-browser PASS; direct109 short help pixels |
| Missing playback preparation said“请求未完成” | Successful missing-stage reads used the transport-error branch; typed missing-production state with preparation-owner link | Unit retry→prerequisite check, exact browser state assertion and112 three-size direct pixels PASS |
|“＋ 添加场景” stacked into three lines | Scene-card 30px number-column grid styled every button, including the generic action | Restrict card grid to non-generic buttons; one-line browser geometry at all three sizes |
| Accepted Art appeared to require an unselected style | Accepted revision and optional NEW task shared hierarchy, although the existing note distinguished their semantics | Explicit optional-new-candidate section, preserved head, focused Art PASS,112 independent pixels and113 real native scroll/read-only proof |
| Generic errors/directory times mixed English into primary UI | Default transport fallback and host-locale AM/PM formatting, not server evidence | Chinese fallback preserves HTTP status/raw details and explicit server messages; Chinese24h `<time>` retains source timestamp |
|“分镜评审确认/确认评审” was awkward | Technical noun phrase in creator guidance |“确认分镜方案与建立正式镜头内容”; no review/production/media handler change |
| Gallery said“已接受角色” while the editor said“已确认角色设定” | Manual creator confirmation used a technical accepted-state label in the adjoining gallery | Current badge/nav say已确认; stale says角色设定需重新确认;13 focused session/selection guards PASS;115 actual native scroll/read-only evidence at all three sizes. Frozen creative prose remains unchanged |

New stable reading invariants are recorded in
[ADR0132](../adr/0132-creator-ui-reading-boundaries.md). Copy-only changes do not
relax approval, overwrite creative source or select a candidate automatically.

## Gates and qualification limits

Latest stable intermediate candidate:626 frontendPASS, application/E2E types,
build/deterministic buildPASS,1245 PythonPASS (one existing Starlette warning),
lock/API-import lint and wheel smokePASS. Full209 browserPASS6.1m with849
source/test/config/static files unchanged before/after:
`fc8e31d277e8385974082fb2c06e05fa04b2340b0355ace84e3fc4aa222bb962`.
The later bounded Play/Art/scene/date/error-copy refinements are not qualified
by that gate:628 frontendPASS, types/buildPASS, focused Art/visual/repair
14PASS/1FAIL52s. The failure was the capture's assumption that the first chat-ID
field must be visible at scrollTop0 on a460px desktop. Root directly inspected
the failure: the initial explanation and first assistant card were visible;
the ID field was correctly below the fold. Corrected capture waits for the first
card legend at the top, then explicitly scrolls to both ID fields and checks
their viewport intersection. Art capability/guards remain unchanged. Corrected
focused14PASS42.3s is retained in112; an independent reviewer directly inspected
30 repaired viewport/full-page captures, with no remaining concrete finding.
Full-page captures establish copy/hierarchy only, not viewport reachability.
Native113 directly inspected all three optional-Art-task viewports after actual
scrolling, with no page overflow or API writes. Latest wheel/installed smokePASS.

Latest frozen full gate:207PASS/2FAIL6.1m,849 files unchanged before/after:
`9a5834de241d632e234e76251501f7cf976da4999643195c065621594e4064a3`.
Evidence retained in114-final-gate-failures. One failure was an old exact
Storyboard wording assertion, corrected to the reviewed wording without weakening
the source-owner navigation check. The other was the recurring plain native
Chromium clock stall; the unchanged multi-ending native sequence and application
branching-video preview passed in the same gate. That recurrence is unresolved,
not classified as a harmless retry. No clean final-gate/release claim is made.
Corrected navigation suite6PASS24.4s retains the exact preparation-owner and
stale-state checks. The later Cast wording-only candidate again passes628 frontend
tests, application/E2E types and deterministic build. Its final full browser gate
passes209 tests in5.9m with849 files unchanged before/after:
`138820796c744b2a4994781d2a6d837ef5c376999a226c8973e4f75b70cd1c95`.
Evidence is retained in116-qualified-final-gate. Both unchanged native probes
pass in this gate; prior stalls remain unresolved historical observations, not
claimed fixes. Final wheel/installed smokePASS from
`/private/tmp/plotloom-ui-audit-cast-wheel.zVCzW7/`.

The114-native-clock-diagnosis paired experiment used the identical retained MP4
and a video-only remux with a byte-identical H.264 stream. Both advanced and
ended at5.166667 seconds under the existing Chromium/default headless contract.
CDP reported FFmpeg decoders and no player errors. It did not reproduce the
stall, so the cause remains unproven: this is not a fix or a qualifying retry.
Playback-quality fields serialized as `{}`; no numeric frame-count claim is made.
No mute, timeout, worker-count or original-fixture workaround was introduced.

Evidence exclusions and false positives are retained rather than silently counted:

- 104 Art/Script/Storyboard/Player captures that only awaited headings were
  premature;109 replaces them with exact loaded-owner or prerequisite checks.
 104 exact-repair capture was layout-only before eligibility;109 requires the
  enabled exact repair control before capturing.
- 105 retains the207PASS/2FAIL native-video-probe run: loaded bytes decoded but
  Chromium's media clock stayed at0 before application choice handling. The
  unchanged probes passed alone and in the later209 gate. Cause is not proven;
  no timeout, clock assertion, mute or worker-count workaround was added.
- 106/108 native-video capture attempts are excluded for incomplete readiness or
  incorrect route-release timing;110 explicitly settles the held GET before
  removing the route and distinguishes pending, known-job loaded and failed reads.
 110 wide loaded video pixels caught initial decoding and are not media-ready
  frame evidence; medium/short show a native frame, not playback/artistic acceptance.
- 107 retains the wrong accepted-review fixture Play assumption and unreachable
  sticky Brief help failure;109 follows the real fixture's missing-production state.
- 111 retains focused14PASS/1FAIL and the erroneous initial chat-ID viewport
  assumption. Initial top, text-ID scroll and image-ID scroll are separate states.
- A previously reported report-toolbar clipping concern was retracted after fresh
  pixels showed readable labels and margins. The assistant-settings short capture
  was scrolled to image settings, not missing text settings. The Brief's reserved
 100px help dock intentionally avoids layout shift; it is not a spacing repair.

Independent GPT-6 Luna/Max pixel reviewers directly inspected42 and17 distinct
109 viewport files; targeted source review found no blockers in the new typed
state/copy/layout changes. Screenshots still do not qualify unexercised handlers.
The repaired112 set has30 independently inspected files;115 adds nine native
Cast files and a source/test diff review with no concrete defect. Main images
retain `object-fit: contain`; thumbnail crops and ordinary viewport folds are
not mistaken for loss of the full reference image. The reusable coverage/copy
documentation also received a separate read-only truthfulness check.

### Earlier gates and preserved repair history

First batch:611 frontend testsPASS, application/E2E typesPASS, buildPASS;6 focused
browser testsPASS. Initial full gate206PASS/2FAIL exposed the accessible-label
root cause; failures retained, not removed. Repaired full gate208PASS(6.2m), with
the same846-file fingerprint before/after:
`830a68ba16b886871c2e99a7e8cfd6689140be01e0c8c2cdf444764647a81645`.

Subsequent copy/modal/recovery-label changes are **not qualified by that gate**.
An intermediate focused Art run32PASS/1FAIL was an old button-name assertion;
its deferred-unmount behavioral assertion remains required. Rebuild, focused
checks followed:613 then616 frontendPASS, types/buildPASS. Focused browser19:
18PASS/1FAIL exposed a strict summary selector; focused14:13PASS/1FAIL exposed
an exact label-text query including the decorative required marker. Corrected
selectors still assert the actual accessible name and description; the final
first-save/presentation6PASS(26s). Both failures and artifacts are retained.

The next frozen full browser gate208PASS(6.7m),846 files unchanged before/after:
`de0e7c7655f0ed79fe89b069eb368519317862a59ba8767ee9ef0b99a97eca1d`.
Independent review then found the authored-title qualifier collision; its durable
fix and further copy/description refinements were **not qualified by that gate**.
Their later build/browser and direct-pixel checkpoints are recorded above; these
earlier gate receipts do not qualify subsequent changes.

Native93 confirms repaired Specialist painting/scrolling/Close at all sizes.
Native94/95 confirms saved/selected Art and presentation states and readable exact
missing-media links. Native96 directly inspected all three sizes shows the final
plain reference boundary. A capture attempt waited for an obsolete Source heading
and timed out without producing qualification; the actual Art panel/text was then
bound and captured successfully. Frozen English prompt and Chinese attribution
notes in94 are original reviewed content, not interface copy: they are retained,
not rewritten to disguise mixed-language source evidence.

Fresh owner-protection recapture matches the exact aggregate
`df1716a80d93bdf9aeaf2565464ac030340ab035cf86198d5355befea075f2a5`:
Wind17/Rain67 managed files, both complete DB row/schema sets and three protected
configurations. Scoped source qualification is complete; source/push/CI identity
is reported separately at delivery. The lifecycle run still remains PARTIAL:
the later native194 receipt separately qualifies opening H3 playback/selection;
other route media, native multishot preview, same-project post-install revision/
rebuild and remaining recovery checks are not completed by a visual audit.
