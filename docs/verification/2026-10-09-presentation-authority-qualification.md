# Presentation authority and final E22 follow-up

This is a bounded continuation of Create → Revise → Recover and E22. The named
native lifecycle journey and finite whole-product visual/text coverage below are
qualified, not every possible state permutation or creative/media quality.
The combined test-harness cleanup gate now passes1,469 Python (bounded reuse),
1,047 frontend and278 unfiltered browser cases, plus types/build/wheel/installed
smoke; its [receipt](2026-10-10-testing-health-cleanup.md) owns the exact frozen
inputs and retained failures. Exact hosted qualification at `0b71359` is PASS:
1,469 Python, 1,047 frontend and 278 browser cases, no flaky/skipped browser results
([CI38024405822](https://github.com/Wenjun-Mao/plotloom/actions/runs/38024405822));
normal cutover remains pending in the
[run profile](../roadmap/2026-10-07-full-creator-e2e-repeat.md).

## Candidate and root causes

Backend/application base `4bbf8c2`; reviewed frontend/test checkpoint
`2a9364947240d5da9e8d94ae674ae37aab2e8780`, published only on branch
`codex/one-current-story-rebuild`, worktree
`/private/tmp/plotloom-one-story-rebuild.gfnqlc`. No Python contract, database,
generation pin or admission predicate changes in this delta.

1. Provider settings rendered protocol states/reason codes as the primary
   instruction. One exhaustive, typed presentation mapping now gives a natural
   status and next action for all nine readiness states; exact diagnostics remain
   readable behind closed details. Save → probe → refresh ownership is unchanged.
2. Independent review exposed a related projection bug: availability PUT already
   returned recalculated server readiness, but the client merged only enabled
   and revision. Both catalog/ref and selected draft now merge that returned
   readiness without replacing authored configuration, dirty state or session key.
   Re-enable is unverified, not a fabricated successful probe. Failed/conflicting
   updates do not install unacknowledged projections or perform extra reads/writes.
3. The installed-production summary called retained cached evidence “current”
   before acknowledging its review basis. Effective currentness now requires an
   acknowledged, current review and current installation. Pending replacement
   review is not a permanent story-version change: guidance preserves old content
   and explains confirmation or cancellation/recheck. Its panel heading uses the
   same pending-review terminology. Shot handoff and rebuild guidance remain
   blocked until actual authority is restored; no refresh bypass was added.
4. Read-only Bible links and headings said “edit.” Neutral “查看” / “设定详情”
   labels now describe the same existing editable-or-disabled forms; no field,
   permission, storage or generation behavior changed.

The new nested diagnostic disclosure also exposed an integration-test contract
mismatch: a descendant `summary` selector matched both disclosure owners. The
corrective test/helper delta selects each direct owning summary and explicitly
opens diagnostic details before testing their long content; no application
change, relaxed strictness or `.first()` workaround was needed.

Lifecycle browser coverage additionally captures the first archive/restore
refusal and a single intercepted snapshot503. The latter is a client-side fault
fixture, not a natural outage or successful snapshot receipt; project JSON stays
equal, retry becomes available and Close only clears the error.

## Executed checks and failed attempts

- Before the initial presentation repair: three focused failures/26 passes.
- Before the independent-review correction: three focused failures/27 passes,
  demonstrating stale readiness and both successful/failed retained-basis headings.
- Final focused unit slice:39 PASS. All frontend: **1,037 PASS /125 files**.
  Application and E2E typechecks, deterministic build, lock, compile,
  scoped API F401 lint and archived Prompt Pipeline Lab verify pass.
- Static-freshness/extraction Python slice: **15 PASS**, one existing Starlette
  deprecation warning. No new full local Python claim for this frontend delta.
- Initial scoped browser run:20 PASS/one capture failure. The failed assertion
  expected the top status in view after editing a lower key field. Root inspected
  its screenshot, then corrected the test to use ordinary dialog scrolling;
  no product layout change or weakened status assertion. A guessed handoff filename
  was also corrected to `production-bridge-shot-handoff.spec.ts`.
- Final scoped browser: **22 PASS in1.8 minutes**, two workers, no retries.
  Output `/private/tmp/plotloom-ui-presentation-final-browser-20261009`.
- A prior276-test sweep was intentionally interrupted for the concrete review
  finding:52 PASS/two interrupted/222 not run. It is **not** a full PASS or a
  product failure. Output `/private/tmp/plotloom-ui-presentation-full-browser-20261009`.
- The next unfiltered276-test gate completed with **273 PASS/three failures in
  15.1 minutes**, all at the ambiguous outer-status selector. This is a failed
  full sweep, not a combined full PASS. Root inspected its short-window failure
  frame and the independent reviewer confirmed the same cause in all three logs.
  Output `/private/tmp/plotloom-ui-presentation-full-final-browser-20261009`.
- After that gate exited, E2E types and the corrected complete snapshot/restore
  file pass: **five tests in20.0 seconds**, actual one worker, no retries.
  Output `/private/tmp/plotloom-presentation-disclosure-qualified-browser-20261009`.
  Existing geometry, title hit-testing, close/reopen, overflow and zero-write
  assertions remain; closed natural status and nested diagnostic checks are added.
- The fresh unfiltered gate passes **276 tests in15.0 minutes**, two workers,
  no retries, exit0. Product/test inputs remained identical to published
  `2a93649` throughout and were checked again after completion. This qualifies
  the full local browser suite, not the pending exact-head CI or all native/UI
  permutations. Output
  `/private/tmp/plotloom-ui-presentation-qualified-full-browser-20261009`.
- Wheel build and installed-wheel smoke pass outside the source checkout;
  packaged `plotloom/static/workbench.js` matches the final served/file hash below.
  Wheel directory `/private/tmp/plotloom-presentation-wheel.ZkzejZ`.

Existing base CI [38000995714](https://github.com/Wenjun-Mao/plotloom/actions/runs/38000995714)
is completed SUCCESS at exact `ef162100c8d7e2191908ee7a142ac2f4f6652646`:
1,464 Python,1,025 frontend and274 browser checks (142+132) pass. It includes one
additional CI regression test relative to the1,463 local base gate. It does
**not** qualify the later frontend delta. Its exact-head full CI
[38009336409](https://github.com/Wenjun-Mao/plotloom/actions/runs/38009336409)
was dispatched once at `2026-10-10T00:30:21Z` for exact
`2a9364947240d5da9e8d94ae674ae37aab2e8780`, with unfiltered `browser_grep=.*`.
Its verify job `114085443411` completed SUCCESS at `2026-10-10T01:08:31Z`.
The actual completed-job log records **1,464 Python PASS /one existing Starlette
warning in2,147.28 seconds** and **1,037 frontend PASS /125 files**; types,
build, checked-bundle parity, wheel and installed smoke steps also pass.
Browser shards `114093851297` and `114093851328` started at01:08:33UTC and
completed successfully at01:44:28UTC and01:27:29UTC respectively; the workflow
completed SUCCESS at01:44:29UTC. Actual logs record shard1's143PASS/zero flaky and
shard2's132PASS/one flaky test, for275PASS/one flaky across276tests. First-attempt
evidence is retained, so green is not clean first-pass. The first job-log read
was refused by the CLI's terminal-escape output guard; its documented
`--allow-escape-sequences` option allowed the filtered read without rerunning
any check. This is candidate-branch publication, not a normal checkout merge
or service cutover; later receipt-only commits do not alter executable/test inputs.
The previous cancellation and reported repo-wide420 existing lint findings are
not converted into PASS; only the established scoped lint gate passed.

## Visual and independent review

Desktop only:1280×768,1280×460,1700×900. No phone/1024 support was exercised or added.
Root directly inspected final six disabled/enabled provider frames, three paused
production frames with their panel headings, and three actual native
current-production frames. Independent read-only review inspected
all12 provider disabled/enabled and production paused/restored frames, rechecked
source/regressions and closed both findings with no remaining scoped blockers.
The reviewer did not run tests. The short restored fixture starts partway down
the page; it does not visually certify the panel header, whose change is covered
by source/unit assertions and the three directly inspected paused captures.
Root and the independent reviewer additionally inspected all six corrected compact/
expanded diagnostic frames. Compact status remains readable; long diagnostic
text wraps within the content width. Expanded frames qualify visible slices,
not an entire body fitting at once; separate geometry/scroll assertions qualify
reachability. The corrective review has no remaining scoped findings.

Earlier root/independent inspected closed-probe diagnostics, snapshot and
archive/restore refusal frames plus archived Bible entity reading remain in the
scoped evidence directories. These are named states, not blanket all-state PASS.
Long forms require ordinary scrolling; no claim that all their contents fit at once.

### Final existing-evidence E22 reconciliation

After the full276 gate closed, root read the owning currentness tests and directly
inspected all15 existing fixture frames; an independent read-only pixel review
also inspected every frame and found no blocking visual/copy issue. No browser,
data or generation action was needed. All are at1280×768,1280×460,1700×900 in
`/private/tmp/plotloom-ui-presentation-qualified-full-browser-20261009`:

- `review-seam-currentness-cu-df77e-ver-stale-retained-evidence/`
  `cast-replacement-{prepared,ready}-{size}.png` (six).
- `review-seam-currentness-cu-7d33b-ver-stale-retained-evidence/`
  `script-replacement-{prepared,ready}-{size}.png` (six).
- `source-review-currentness--f6e06-hority-until-explicit-retry/`
  `storyboard-post-mutation-read-failed-{size}.png` (three).

Retained evidence is distinguished from replacement-candidate authority;
prepared/ready Script names sending versus confirming, Cast confirmation stays
distinct from reference eligibility, and failed Storyboard reads offer retry
without claiming modification/production authority. No overlapping columns,
clipped visible action text or misleading success color was found. Short frames
are ordinary scrolled slices: Cast-ready upper retained notices and the short
Storyboard error body are outside those captures. This is controlled fixture
evidence, not native delivery or whole-form/all-state acceptance.

The completion-gap review reconciled the historical register against the later
named receipts rather than reopening already qualified routes, multishot, OS blur,
provider copy or archived Bible reading. Its only concrete remaining E22 capture
gap was the first stale Cast/Script lower-action row; that gap is closed below.
Current dispositions remain:

| Requirement/boundary | Current disposition |
|---|---|
| Named Create → Revise → Recover native journey | Revised/restored routes, multishot, source lifecycle and58-asset/four-selection preservation are qualified in the Board3 receipts; no creative-quality claim |
| Whole-product E22 | Finite named view/state coverage is qualified across Home/directory, Brief/settings, Source/Outline, Creator/Pro, Cast/gallery, Bible, Art/references, Script, Storyboard/production, Media/shot details, Reader/Play, Trace/repair and specialist/provider dialogs. This includes the15 frames above and21 lower-action frames below; it is not an exhaustive Cartesian state matrix or acceptance inherited from functional tests |
| Scene/Prop downstream production consumption | Absent consumer/capability boundary; gallery/reference evidence does not prove production consumption; product expansion needs authority |
| Configured API intent | Unconfigured; native intent is separately qualified, not an API fallback or configuration PASS |
| Populated native Cast relationships | Optional native evidence variant not exercised; the four-role relationship fixture remains fixture evidence. This is not an absent-capability claim or a reason to generate more content solely for counts |
| Normal activation | Pending retained-demo/cutover choice; no mounted-checkout-only update, owner reset or schema adapter |
| Creative/audible/perceptual quality | Explicitly excluded from this technical run |
| Exact-executable CI | Current `0b71359` workflow SUCCESS on attempt 1: 1,469 Python, 1,047 frontend and 278 browser PASS (122/156), no flaky/skipped results. The historical `2a93649` run's first failure remains preserved above; [the owning fixture repair](2026-10-09-owned-browser-listeners.md) is covered by this final gate. |

### First stale lower-action closure

The final capture method directly checks Cast-ready confirmation/abandonment and
Script-prepared sending/checking/cancellation plus Script-ready confirmation/rejection.
At1700×900,1280×768 and1280×460, exact disabled/enabled action eligibility,
strict viewport intersection, sticky-header clearance and no horizontal overflow
are asserted. All21 final PNGs were directly inspected by root and an independent
read-only reviewer, with no actionable visual/copy finding. This is fixture-based
action readability/geometry, not native delivery, keyboard handling or whole-form fit.

The first scoped attempt recorded2 PASS/1 capture failure: nearest-edge scrolling
left a fractional bottom clipping at1280×768 (intersection0.9967105). The capture
helper now uses centered ordinary scrolling; the strict geometry assertion was
not relaxed and no product layout patch was made. Final three cases PASS in15.7s,
one worker, zero retries, exit0; E2E types PASS. Evidence:
`/private/tmp/plotloom-first-stale-actions-qualified-20261010`.

## Loaded bytes, data and service preservation

Final served/file JS SHA256:
`0a4fd0e721b819da4ffec7d946e0af8f7c9ae3a90e9c4d473972951ac3ace160`.
Native QA Source tab7 was explicitly reloaded. Actual network response1061 body
matches that SHA (793,714 characters), not merely a newly served file. Three
current-summary frames show actual current authority, zero alerts and page widths
equal to their desktop viewports. A first helper attempted a nonexistent nested
header selector after capturing1700; its timeout is not a PASS. The corrected
direct-strong selector completes all three frames; no runtime workaround.

Post-publication readback `presentation-published-readback.json`, timestamp
`2026-10-10T00:36:30.000Z`, is deep-equal to the settled r12 baseline for all eight
content/media endpoint projections, all58 asset hashes and four selected records.
It repeats the earlier reviewed readback at `2026-10-10T00:11:34.402Z` without
changing the disposable project's state.
The later fresh read-only comparison at `2026-10-10T02:36:07.251Z` again matches
all eight endpoint projections,58 freshly hashed assets and all four selected
records, with zero differing endpoints. Its artifact is
`/private/tmp/plotloom-e22-native-final.MuRJ51/readback.json`; no new generation,
review, selection or lifecycle write was performed.
QA project `90c0f895-48de-4b57-8725-4b6f72797633` remains revision2/lifecycle9 active.
No new job, acceptance, rebuild or media selection was dispatched in this delta.
The optional current-pin native report delivery/cancellation is separately
qualified in the [native report receipt](2026-10-09-current-pin-native-report.md).

Both protected owner projects/configurations retain exact aggregate
`df1716a80d93bdf9aeaf2565464ac030340ab035cf86198d5355befea075f2a5`
(17/67 managed files, three protected configuration files). Normal8841 still
serves JS `3a8843193da3df6852f8b12731e33c90961dbe1339a9882b30fb2e03290555d5`;
its checkout is clean. Fork pin `4f9b2128c82adf623f594ba714c97d0afcfc16a2` is clean.

Normal cutover still awaits the explicit retained-demo choice. Do not update its
mounted checkout alone, reset owner databases or add a schema adapter. Scene/Prop
downstream consumption is a new capability boundary; API intent is unconfigured
and not a native fallback; populated native relationships are an unexercised
optional variant. Generic active API Trace is not applicable to the native-only
composition. These dispositions do not claim their execution. Creative, audible
and perceptual quality remain excluded. Exact hosted qualification is PASS;
required remaining delivery is the separately authorized main/normal cutover—not indefinitely
enumerating hypothetical state permutations.
