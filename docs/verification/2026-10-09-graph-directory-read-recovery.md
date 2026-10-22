# Graph and project-directory read recovery

Bounded candidate on retained checkout `/private/tmp/plotloom-one-story-rebuild.gfnqlc`,
branch `codex/one-current-story-rebuild`, base `772c78b`. Uncommitted software
qualification; initial independent review closed before the full gate exposed
the additional drain regression described below. The writer performed no service
restart, dispatch or protected-data change. Manager-owned static activation and
native read-fault evidence are recorded separately below.

## Demonstrated cause and repair

The manager's native8865 GET-only before evidence is retained at
`/Users/wjmao/projects/HU/plotloom/output/playwright/native-intent-2026-10-08/read-recovery-before-notes.md`.
Initial graph503 falsely said `当前内容仍保留`, offered no retry, and Professional
confirmation/application could be enabled after its independent Source GET.
Directory503 offered no retry. These are controlled read faults, not actual backend
outages or mutation evidence. [ADR0145](../adr/0145-current-read-authority-for-graph-and-directory.md)
records the owning read/admission/autosave diagnosis and adopted contract.

Read errors now have separate owners from command/lifecycle errors. Shared graph
authority is explicit, GET retries preserve unsent inputs, and graph-only autosave
admission blocks queued timer/blur/new drain writes during pending/failed reads.
Valid already-started ACKs and selection/project/CAS ownership remain preserved.
Initial absence and retained content receive different guidance. Source retries
work in both graph modes; canonical read-only and stale explicit recovery retain
their distinct semantics. Directory retry preserves the failed filter/cursor,
known same-filter rows and inputs; list failure pauses row actions, whereas a
lifecycle action failure does not permanently freeze a valid list.

The manager additionally demonstrated three copy mismatches in native Trace/Brief:
`任务启动后，运行详情会显示在这里。` when API execution is absent,
`待审阅的故事提案` without editorial-state evidence, and choice-edge count labelled
`个选择`. The owning copy now uses neutral empty-event guidance for false/unknown
capability, `故事设定与分支图`, `个选项`, and `每次完整播放约`. No review workflow
or numerical contract changed; ADR0118 terminology remains authoritative.

## Executed qualification

- Final frontend suite after confirmation-read repair: **941 PASS**,116 files; both frontend and E2E TypeScript
  checks PASS. Focused provider, real provider/autosave integration, timer/blur,
  in-flight ACK, late-project, Source/directory ownership and copy tests pass.
- Browser after confirmation-read repair: **10 PASS**,24.9s: nine new read-recovery cases at1700×900,1280×768,
  1280×460 plus existing graph transaction/cancel/Undo/unfinished-prose journey.
  Initial held/failed graph reads in both modes, held retry, directory held/failure
  and retry, Creator and Professional Source503/retry, disabled admission, unchanged exact
  canonical/graph responses and zero browser mutations are asserted. These use
  disposable project-folder runtimes, Vite and deterministic fixture deliveries;
  they are not real specialist or native after-activation acceptance.
- Pixels:24 captures preserved under
  `output/playwright/2026-10-09-graph-directory-read-recovery/`.
  Writer directly inspected all12 initial graph/directory/Source failure pixels
  across the three sizes; copy and recovery controls fit, including1280×460.
  Waiting and retry pixels are captured for independent review. Directory images
  are element captures; graph/Source images are viewport captures.
- Temporary production build PASS at `/private/tmp/plotloom-read-recovery-build.ZeYaMB`;
  existing large-chunk warning remains. Checked static is intentionally untouched
  while native8865 serves it. Manager must build/verify static after the activation
  boundary permits replacement.
- Focused Python: inventory + project-storage-image workflow + runtime-capabilities:
  **4 PASS**, one existing Starlette deprecation warning,2.64s.
- `git diff --check` PASS. No Python source or Python tests changed.

Earlier frontend checks exposed two obsolete expectations permitting typing/saving
during pending graph reads and one conflated error assertion; they now assert the
new read boundary while retaining selection/latest-ACK preservation. Initial
browser attempt passed two graph cases but timed out on the wrong onboarding
button name; stopped owned test runner, corrected locator to `打开项目目录`, and
reran successfully. No product workaround was introduced for either test failure.

The manager's full Python run on base772c78b was **1417 PASS/1 FAIL**, with one
Starlette warning. The sole failure was stale authored-coverage inventory metadata:
the capability assertion changed `textProviderProfiles`→`apiTextPipeline`, but its
catalog did not. This repair changes exactly one catalog function hash and its one
assertion string; all37 assertions, review/disposition, checker and baseline stay
unchanged. Independent review must inspect this exact delta. The focused gate
passes. Independent review cleared the exact inventory delta. The manager's fresh
full rerun finished **1,418 PASS**, one existing Starlette warning, in1,357.83s;
the full frontend rerun independently finished **941 PASS**,116 files.

## Independent review follow-up: confirmation read

The independent reviewer reproduced a blocking omission using
`/private/tmp/plotloom-confirm-read-review.ePNbyu/confirmation.test.ts`:
`confirmMapping` read directly after saving the section map. Its held GET left
`readStatus=ready` and admission true;503 became a command error while read error
stayed empty, and subsequent `changeDraft` accepted new fields. This bypassed the
new contract at its actual owner, rather than revealing a button-only defect.

The direct provider read is removed. All provider/display-authority graph GETs
now go through the single refresh path. Successful confirmation stays successful
when its follow-up GET fails or is superseded. A pending confirmation receipt and
authored-content basis permit Undo rebasing only after a current exact revision,
canonical-base and payload-binding match; failed/superseded reads preserve that
basis for explicit retry, and latest ACK protection rejects older returned drafts.
The pre-existing explicit conflict-copy recovery GET in authoring persistence is
a separate CAS preflight, not a provider state projection; its session/conflict
owner and restored-payload→provider reread remain unchanged in this follow-up.

Exact external red regression now **1 PASS**; new owned confirmation regressions
cover held/failed read admission, retained fields, successful save outcome,
superseding read and latest ACK. The existing Undo test now proves failed
post-confirmation GET→explicit retry→valid same-base Undo rebasing. Focused
confirmation/provider/autosave integration **36 PASS**. Final941 frontend tests,
both TypeScript checks and10 browser tests pass. The browser cases now exercise
Creator Source failure/retry as well as Professional at all three sizes, with zero
browser writes and unchanged graph responses.

Fresh captures are retained separately under
`output/playwright/2026-10-09-confirmation-read-recovery/`; the writer directly
inspected the three additional Creator Source-failure viewport pixels, including
short-desktop scroll/action visibility. The earlier24-pixel set remains retained
and was independently inspected by manager/reviewer. Final temporary production
build PASS at `/private/tmp/plotloom-confirm-read-build.Rvs0mc`, with the same
large-chunk warning. Checked static, backend/Python/tests/catalog and all native
or protected data were untouched during this follow-up. Manager full Python and
native after-repair acceptance remain separate gates; the full Python result above
is now terminal, rather than a running-process estimate.

## Remaining acceptance

Independent source/pixel review is closed with no remaining blocking finding.
The reviewer independently ran47 confirmation/provider/autosave/directory tests,
both typechecks and the external regression, and inspected six fresh Creator/Pro
Source-failure viewports across all three sizes. It cleared the separate conflict-copy
CAS preflight; manager/reviewer also inspected the earlier24-pixel set.
Static activation/identity and actual native after-repair readback remain manager-owned.
Retained dirty/failed autosave and
project-switch/ACK cases are qualified through focused tests, not newly claimed
native pixels. Actual OS blur during graph-read failure and broader directory
lifecycle journeys are not claimed by these new nine browser cases. Wider E22,
identity-review semantics, pinned Art context and full Create → Revise → Recover
acceptance remain open; this bounded receipt does not mark them complete.

## Manager native replay and full-gate correction

The manager rebuilt checked static twice with identical inputs, then confirmed
native8865 served exactly JS `d415fe7f6826dab82222aa9a4323baa6465a8af7a632744ac270468d5f19978e`.
Python remained772c78b; normal8841 retained JS `3a8843193da3df6852f8b12731e33c90961dbe1339a9882b30fb2e03290555d5`.
No native backend restart was required for this frontend-only slice.

Actual native graph held/503/explicit-GET-retry passed in both workbench modes
at1700×900,1280×768,1280×460. Source503/retry passed at all six combinations;
confirmation/application remained disabled until a successful Source read.
Directory initial held/failure/retry and retained same-filter failure/retry passed
at all three sizes, preserving two rows and disabling their actions.
Root directly inspected12 graph,6 Source and9 directory viewports, plus the
short-directory bottom capture: scrolling revealed the complete last disabled
Delete control inside the modal body. Independent directory pixel review found
the retained warning overbroad; the owning copy correction below addresses it.
Evidence: `output/playwright/native-intent-2026-10-08/read-recovery-after/`.

The Source replay's first attempt released its fault before clicking; binding
hydration could therefore read successfully and remove retry. A second attempt
used an incorrect command label. Both are excluded method failures. The final
attempt keeps failures through hydration and releases only at the actual named
retry click: two failed reads and one successful explicit retry per combination.
Owned route interceptors/listeners were removed. Total browser API requests362,
mutations0, unsupported profile reads0. Eight native API-domain hashes and all42
asset paths/hashes match the preceding snapshot;8 image/7 video jobs and idle
specialist/run state remain unchanged. This does not qualify dirty native blur.

The first unfiltered264-browser gate finished **246 PASS/18 FAIL** (11.4m),
preserved at `/private/tmp/plotloom-read-recovery-release.aS7V6h/browser`.
Seventeen failures had one product cause: scope read admission was checked before
the empty graph queue, so an unmounted graph editor prevented Close/snapshot
without any lifecycle POST. The other failure was a legitimate duplicate Brief
label matched by a broad test selector. No timeout or retry weakening was used.

The owning correction joins admitted flights and accepts empty queues before
new-write scope admission. Dirty/newer graph input still refuses on read loss;
project/conflict/suspension ownership remains. Test-first reproduced two failures;
27 focused unit and30 affected Vite browser journeys now PASS. Root independently
reran the27 checks and inspected the diff. Both typechecks PASS. Synopsis asserts
its intended title container; retained directory copy now explicitly distinguishes
disabled list-row operations from available New Blank/Example actions. ADR0145
records drain versus new-write authority. Final frontend suite **945 PASS**,
116 files. Fresh checked build serves JS `d47c0844c23d3c37515d54205e1c2c19b999298c899445964d9dad4a5c53b01a`.
The corrected unfiltered gate finished **264 PASS** in8.2m, including the
checked-static video restore journey. Evidence is preserved at
`/private/tmp/plotloom-read-recovery-release.aS7V6h/browser-corrected`.
Its913 source/test/build-input fingerprint remained
`7242d10283e29a2e742492bd026086f47b8aff8d40ceddcfdc6894ab0174c118`.
No timeout, retry, test filtering or production-refusal boundary was weakened.
The paired deterministic builds finished with identical checked output.

The manager mistakenly built the first corrected wheel concurrently with the
second frontend build. Its unchanged installed smoke failed at the missing
`static/index.html` assertion, demonstrating a packaging-order race, not a
runtime product defect. Preserve that failed wheel in `wheel-corrected`.
A serialized rebuild after the bundle completed produced `wheel-final`; its
unchanged installed smoke **PASS** and all7 packaged static members match
checked source bytes, including entry HTML and the exact d47c0844 JS above.
An initial invocation also used an unsupported `--wheel` flag; that exited at
argument parsing and is excluded from smoke qualification. The developer guide
now states the build-before-wheel ordering explicitly.

The manager replayed the final retained-directory warning at all three sizes
and directly inspected six fresh top/bottom captures. Every retained-row action
remained disabled, while New Blank/Example remained enabled. The short modal
scroll revealed both complete rows and their Delete buttons above the footer.
These captures are `*-directory-corrected-retained-{failed,bottom}.png` under the
native evidence directory above. The replay made zero writes and removed its
owned interception/listener. A fresh native snapshot again matched all8 domain
hashes and all42 asset paths/hashes;8 image/7 video jobs remain terminal and
specialist/run state idle. These checks do not establish artistic acceptance or
exercise native dirty-input OS blur.

The final independent source review found no blocking issue and independently
reran all27 drain/directory/confirmation checks. It specifically cleared project,
conflict and suspension ownership before drains, latest-ACK/newer-input refusal,
the exact Synopsis title selector and retained-directory action semantics.
Independent pixel review cleared the corrected directory warning and all six
directory captures. At1700×900 and1280×768 the entire directory fits; only
1280×460 needs internal scrolling. The first Creator Source-failure screenshots
did not show the footer at the smaller sizes, so the manager collected three
separate `*-creator-source-failed-footer.png` captures after scrolling to the
disabled confirmation/application controls. Each replay kept two failed reads
through binding hydration, then performed one explicit successful retry, with
zero writes. An initial immediate bounds assertion raced the inspector's
repositioning; final qualification awaited settled bounds rather than changing
the UI or relaxing visibility. All owned fault/listener/window state was removed.
Independent review directly inspected all three additional Creator footer pixels:
the controls and guidance fit without clipping or overlap, including1280×460.
The scrolled captures complement, rather than replace, the full failure-banner
captures. No remaining concrete source or pixel finding is open in this slice.
