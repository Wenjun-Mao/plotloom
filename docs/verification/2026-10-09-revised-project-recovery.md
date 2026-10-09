# Revised native project recovery — October9

Scope: E19/E21/E22 in the [current run](../roadmap/2026-10-07-full-creator-e2e-repeat.md).
This is revised-project evidence, not inherited first-install acceptance.
Project `90c0f895-48de-4b57-8725-4b6f72797633`, QA 原生重建·渡口信号,
on isolated8865/8866 with backend95074b1. Normal8841 and protected owners/settings
were not modified. The first close/archive slice performed no generation,
selection, deletion or lease cleanup. Later deletion targeted only the separately
restored disposable copy described below, never the original native project.

## Executed recovery

- Saved/closed through the actual UI, observed closed directory state and reopened
  the same project through its named control (POST open200, operational revision3).
  Eight full API-response hashes were identical before and after.
- Archived through the directory with archived rows visible. Without reload,
  the selected East shot switched to retained-evidence reading; prepare/review/
  selection actions were disabled. Retained segment
  `3b54b242-ab81-46f7-8a28-7fac46a22451` played to trusted native ended at5s,
  media error null, volume1/unmuted. This is playback, not sound-quality approval.
- Restored through the actual directory action (09:45UTC,200,lifecycle revision3),
  without reload. Preparation/selection controls re-enabled, selected segment
  remained selected and played again to trusted ended5s/error null. The correct
  one-missing-clip warning remained; neither revised route is qualified yet.
- A second archive tested the toolbar's standalone playback destination and
  exposed the defect below. Final restore returned200/active/lifecycle revision5.
  Final eight API hashes and all42 managed asset path/hash entries exactly match
  the pre-close baseline. Lifecycle/update fields are intentionally not part of
  those eight response hashes; no claim of byte-identical project database.

Evidence root: `/Users/wjmao/projects/HU/plotloom/output/playwright/native-intent-2026-10-08/`.
`revised-recovery-preservation.json` retains before/after-close/after-first-restore
hashes and full42-file inventory. `revised-recovery-final.json` retains final
second-restore checks. Browser snapshots: `revised-closed.yml`,
`revised-reopened.yml`, `revised-archived-workbench.yml`,
`revised-restored-workbench.yml`, `revised-final-restore-dialog.yml`.

## Pixel and wording audit

Root and independent retained E22 reviewer inspected six archived segment/control
captures at1700×900,1280×768,1280×460. Disabled actions and retained-evidence copy
are readable. Short-height captures represent distinct scroll positions, not
whole-image visibility. All three closed-directory captures were root-inspected.

Independent review flagged awkward “听看片段首尾” and the active-looking Play link.
Root exercised the link: it remains read-only navigation, but its destination
misdiagnosed archival as four missing clips and invited unavailable review.
`revised-archived-play-retry.yml` preserves that incorrect destination.

Root cause: PlayView read project lifecycle but ignored it when choosing between
production and clip prerequisites. Archived media correctly loses currentness;
the lower clip projection cannot infer why. The repair belongs in the owning
page: typed archived prerequisite before production/clip guidance, preserving
read errors and all media admission. ADR0132 records this ordering. The page now
explains restoration through the directory and keeps Return to workbench, with
no review link or video. No automatic restore or compatibility branch was added.
Segment instructions now explicitly say to inspect picture and sound, rather
than the unnatural “听看”.

Native fixed page was directly inspected at all three desktop sizes in
`revised-archived-play-fixed-*.png`; heading, explanation and return action fit.
No backend restart was needed for this frontend-only change. The initial native
Play read once returned `project_busy: another local writer is active`; a named
manual read retry exposed the separate archived-message defect. The lock-holder
cause is not established, and this repair does not claim to fix that transient.

## Verification and limits

- Archived precedence unit regression failed before the repair; final focused
  Play/segment wording suite9PASS. Full frontend874PASS; both typechecks and
  deterministic build PASS. Static assets rebuilt.
- New real-server archived→restored Play browser journey1PASS, three desktop
  captures, zero browser mutations; restore fixture API is separately explicit.
- Adjacent media-bearing direct-folder restore and both-branch native-ended
  fixture browser journeys2PASS (1.8m). No live provider generation in those tests.
- Independent source review cleared the lifecycle/read-error boundaries. Its
  one paragraph-orphan finding was corrected with two short paragraphs; final
  three-size fixture pixels were inspected by root and independently cleared.
  Final focused9, full frontend874, both types, deterministic build and new
  browser journey1PASS after that text-layout correction. Final pixel folder:
  `frontend/test-results/archived-play-guidance-final/`.
- Stable6679d08 subsequently passed the full244-browser gate in7.7m. The later
  snapshot-feedback repair below is separately qualified; this gate is not
  evidence for that later diff. Prior full-Python results remain unchanged.

## Revised snapshot, isolated restore and exact copy deletion

At09:58UTC the actual8865 toolbar sent one POST snapshots request (201), creating
`7c4211dd-82bd-4cf0-8d33-ee3769ae8271`. Its139 declared files include42 managed
assets; database SHA256 is
`4bc6d5cf0ccdc05afc2ab4569bcff710d15311367234e72e0cb55484bbefe080`.
The verified `plotloom restore --source ... --outputs-dir ...` operator command
returned restored/exit0 into `/private/tmp/plotloom-revised-restore.FfALP9/outputs`.
No ordinary folder copy, configuration import or historic-job replay was used.
The first launcher attempt refused the absent application directory. Creating a
new empty application directory satisfied its documented composition requirement;
no old application data/settings were copied. Owned8875/8876 then started healthy
with H3 disabled and an empty specialist registry; recovery control is clear,
with no operations. Source8865 was not restarted.

All42 asset path/hash entries equal the source. Seven complete API responses
(Cast, Art, Script, Storyboard review, videos, images and character references)
hash identically. Production-bridge differs only in installation-owned native
capability/dispatch projection: unavailable/not_configured, and registry state
prepared without taskId. Its project candidate remains ready/reportAvailable;
stored proposal/intent/installation content is unchanged. This is not an eighth
byte-identical response or evidence of a new queued task. The UI uses the stored
ready candidate state and exposes no resend for it.

On the restored copy, root selected each existing shot through the UI and played
the Opening1, West and East selected segments to native trusted ended at5s,
error null, volume1/unmuted. No selection writes or generation occurred. Exact
segment IDs, final source hashes and observations are in
`revised-snapshot-restore-evidence.json` under the evidence root above. The UI
preserves the correct one-missing-clip warning, so neither complete revised route
is claimed playable. Root inspected all3 restored-segment desktop captures.
The short-height capture is a scroll position, not evidence of full-frame visibility.

At10:03UTC root opened the restored copy's directory, inspected the exact identity,
typed its full title and confirmed permanent deletion. Actual POST permanent-delete
returned204; directory became empty and the exact restored project folder is
absent. The observation helper mistakenly waited for DELETE and timed out; the
native request log, UI completion and filesystem independently prove the POST
success. It was not retried. All3 confirmation captures show the warning, exact
title field and both actions. Source8865 remains active/lifecycle5/content2;
all eight original API hashes and42 assets still match the pre-recovery baseline.
The original snapshot remains available for another verified recovery.

Snapshots: `revised-restored-copy.yml`, `revised-copy-directory.yml`,
`revised-copy-deleted.yml`. Pixels: `revised-restored-segment-*.png` and
`revised-copy-delete-confirm-*.png`. Independent E22 review inspected all6 with
no blocking findings. These are native retained-media recovery checks, not a
fresh provider run or creative/audio-quality acceptance.

## Snapshot completion feedback defect

The native POST201 succeeded, but completion and location were visible only after
opening unrelated technical Service status. This is a toolbar ownership defect,
not a failed snapshot or reason to retry creation. The prior browser test only
asserted hidden DOM text. Adding visible-receipt assertion failed at1280×460.

Move the receipt into a dedicated compact toolbar disclosure: visible completion,
explicit View location, exact selectable path on expansion. Retain the exact
current-project guard; no lifecycle, snapshot or recovery semantics change. Long
paths wrap, and expanded details enter normal document flow without covering
authoring controls. The reusable E22 checklist now explicitly requires visible
completion from a scrolled page, location reading and cross-project isolation.

Initial4 focused browser checks, full874 frontend tests, both typechecks and
deterministic build pass. Independent review cleared source/recovery captures,
then caught one expanded1700 screenshot taken before the toggle scroll settled:
CSS visibility did not prove viewport placement. The test now waits for actual
path bounds inside the viewport before capture; earlier evidence is retained in
`frontend/test-results/snapshot-visible-final/`, not counted as full pixel proof.
Final viewport-qualified run passes all4 focused checks in17.6s; both typechecks
and diff checks pass again. The source/build/full874-unit qualification above
still applies; only the stronger E2E capture wait changed afterward. Independent
review directly inspected all6 final fixture captures in
`frontend/test-results/snapshot-visible-viewport/` and all6 native
`native-snapshot-{complete,location}-*.png` captures. Completion summaries and
entire expanded paths are visible at all3 sizes; wrapped paths are not clipped.
Root separately inspected all6 native frames. The prior1700 screenshot gap is
closed by viewport bounds and pixels, not by CSS visibility alone.

The native fixed-UI check intentionally created one further QA snapshot at
10:08UTC, ID`896f6a2c-28d0-43e5-a9f5-c46055894a7b`, under the same snapshot parent
as the original, directory
`20261009T100806817321Z__896f6a2c-28d0-43e5-a9f5-c46055894a7b`. Its139 manifest
files include the same42 assets and database SHA
`4bc6d5cf0ccdc05afc2ab4569bcff710d15311367234e72e0cb55484bbefe080`.
Both snapshots remain; this was a separate UI verification, not a retry of an
unknown outcome. No provider generation or normal8841 activation occurred.

## Current revised-project idle restart — October9 10:18–10:20UTC

Snapshot-feedback source is committed as`ddcb06d`. Before restarting owned8865,
the specialist registry reported`busy:false, activeTasks:[]`; runs were empty,
all8 image jobs delivered and all7 video jobs ingested. No unknown/live task was
stopped and no accounting lease was cleared. PID80987 shut down cleanly; the same
isolated launcher/data/configuration started PID52578 and health returned200.
Normal8841 was not stopped or changed. Served JS matches the checked bundle:
`9975b691027d9de23cd0d783bbeb97857ad96825713a674f4b3e5803cc2a9021`.

All8 domain API response hashes match before/after, as do all42 asset path/hash
entries. Content revision2, lifecycle revision5/active, selected segments and job
states remain exact. After actual browser reload, root selected each of the3
available revised shots through Current shot and played its current segment to
a trusted ended event at5s, error null, unmuted/volume1. Request observation
recorded zero API mutations. This is retained-segment restart recovery, not
complete revised-route playback or creative/audible-quality acceptance.
`revised-idle-restart-evidence.json` in the evidence root records exact readbacks
and segment identities. The now-empty owned8875 restore-copy runtime was stopped
cleanly; both original QA snapshots remain recoverable.

## Completed native image reopen/check — October9 10:27UTC

On the same revised East shot, the actual browser navigated to Characters, used
Back to return to the shot, and reopened preparation. The same delivered image
job `ij_f8526d13a51d487a99e82bbcc4c97c62` remained visible, frozen hash prefix
`81687adb24a3`, with one delivery and Send disabled. Navigation caused zero API
mutations. Clicking its named “立即检查交付” control made exactly one POST to that
job's refresh endpoint:200, accepted, `idempotent:true`. Delivery
`3882a842-98a4-4b59-9bd6-53b4e49cb689` and candidate asset
`c4a37658-ed3a-42c1-919c-0b86da313cff` stayed identical. The complete image-jobs
response was byte-equivalent after JSON serialization; all8 jobs remained.
There was no send, preparation, selection, duplicate candidate or provider call.

Root directly inspected `completed-image-reopen-check-1280x460.png`: completed
status, frozen identity, disabled Send, enabled Check and the delivery/candidate
record fit without clipping. This covers a **completed** native job, not an
active queue, actual OS-hidden-tab delivery, or specialist-capacity reporting.
Entering Characters also logged the expected script refusal in its sandboxed
static report; that is not a generation or delivery failure.

## Snapshot project ownership and draft-recovery reading

The new real-server fixture A→B→A journey stays in the same mounted app and uses
the actual project directory. A's snapshot receipt is absent in B, then returns
with A's exact location; switching sends no snapshot POST. The focused case
passes2s (4.5s including setup), strengthening the existing project-ID guard.

Two further real-server fixture journeys induce a503 draft-save response after
actual typing, without seeding UI state: tab-only recovery and a tab draft
different from the saved project draft. Each captures ready and held-verification
states at all3 supported desktop sizes. Canonical content and server drafts stay
unchanged while verification is held; both actions are disabled. On successful
restore, the local input is autosaved, and confirmed content remains unchanged.
Initial2 cases pass11.7s including setup; root inspected all12 screenshots.

Those checks exposed a wording defect, independently confirmed: the reconcile
dialog promised “供你比较并重新保存”, but the existing restore handler schedules
autosave immediately. There is no two-draft comparison step before the project
draft is replaced. The owning dialog now explicitly discloses automatic saving
and replacement of the corresponding project draft, while confirmed content
remains unchanged. The session-only message also explains automatic saving.
Independent review found that the promise must respect the existing runtime
capability: the required `autoSaveAvailable` prop now follows durable-draft
availability and a persisted project ID. When unavailable, both local-draft
variants instruct manual saving instead. This changes presentation only.
No recovery behavior, draft version contract or compatibility path changes.
Two revised copy regressions failed before the repair. The reusable E22 checklist now checks this exact
action/copy agreement rather than treating fitting text as sufficient.

The unchanged `ddcb06d` full browser gate finished244PASS in7.9m before these new
tests/copy changes. It is not evidence for the later recovery wording delta.
The full Python job completed1,415PASS with one existing Starlette/httpx
deprecation warning against unchanged Python source/tests. Final frontend
qualification passes876 tests in108 files,19 focused recovery tests, types and
deterministic build. The final capability-copy browser run passes both recovery
journeys; the preceding wording candidate also passed7 focused snapshot/recovery
and6 adjacent current-contract recovery browser cases.

The retained independent reviewer closed the capability finding with no concrete
remaining bug, inspecting all12 final durable-path captures under
`frontend/test-results/recovery-capability-final/`. Root rechecked both short-height
ready dialogs. Manual-save copy is covered by dialog and actual App-harness tests,
not separate pixels. The native completed-image capture was independently inspected
in the preceding review. These are scoped results, not a new unfiltered browser gate.

## Assistant settings held/failure states — October9

Actual8865 UI with controlled GET503 and PUT503 interception exposed an unlabelled
initial wait, an `Error:` prefix from `String(reason)`, no in-dialog read retry,
and a disabled save button still labelled as an idle action. The exact server
settings JSON stayed unchanged through each journey; the single attempted PUT
was answered by the fault handler, not sent to the server. No specialist task
was checked, sent or resumed. Root inspected all12 before-state captures in the
native evidence root, named `settings-{read|save}-{pending|failed}-{size}.png`.

The owning `SpecialistSettingsDialog` now renders initial/retry loading, offers
GET-only retry after failed initial reading, uses the error message rather than
the JavaScript error object's prefix, and names the active save/check operation.
The read effect retains its unmounted-instance guard. Existing input/Save locks
and save persistence semantics are unchanged; failed saving retains edited values.
This is local request-state presentation, not a new dispatch or compatibility path.

Two of the initial three new unit cases fail before the repair. A fourth case
directly checks held task-check status, exact job identity, restored idle state
and absence of save/send calls. Final13 focused specialist tests and full
frontend880PASS; types, E2E types and deterministic build pass.
The final real-server browser journey passes in3.6s including setup and directly
checks read-only retry, one intercepted PUT, unchanged server settings, retained
input and disabled pending controls. Root inspected all12 final captures under
`frontend/test-results/settings-presentation-recheck/`. The first browser attempt
timed out because its setup stayed on Home, where the settings entry does not
exist; the retained trace identifies this fixture mistake. The corrected setup
uses the actual Open sample action before entering settings; assertions unchanged.
Independent source/pixel review closed with no concrete bug in this delta.
The reviewer noted unchanged behavior: closing during save/check does not cancel
the request, so a save can still commit and a later error is no longer displayed.
That slice did not qualify close-while-pending, successful settings persistence,
active native task checks, or every provider-profile state.

### Pending-operation close and explicit retry — October9 continuation

Actual8865 read-only settings plus an intercepted held PUT503 reproduced the
close defect: `closeEnabled=true`, `closedBeforeResponse=true`, failure feedback
and edited input both absent after reopen, persisted settings byte-for-byte equal.
One attempted PUT per exercise was intercepted; no settings write or generation
reached the server. The first CLI script failed to parse before execution; a
subsequent exercise completed, and a repeat returned the explicit boolean evidence.
`output/playwright/native-intent-2026-10-08/settings-close-pending-reproduction.png`
records the reopened UI. The actual settings were never printed or modified.

The save/check result and input are dialog-local, but close/backdrop could unmount
their owner during the request. Both now honor the existing operation busy guard,
just like editing/Save. This keeps feedback in place until settlement; it does not
cancel a submitted operation or claim browser/tab closure can be prevented.
Initial GET loading and a server-side active task do not lock Close. No API,
provider, dispatch or persistence contract changed.

Two focused assertions fail before the repair; all4 settings tests then pass,
covering failed save and successful task-check settlement, close/backdrop guards,
retained input and closing afterwards. Full frontend888 tests/109files, application
types, E2E types, deterministic build and diff check pass. Final real-server browser
journey passes4.2s: GET retry, intercepted failed save, exact unchanged readback,
explicit real retry in the **disposable fixture only**, successful name persistence
and close/reopen retention. Its two PUT attempts are exactly failed+retry, all
other settings fields remain identical and no generation/check/send is performed.

Final15 captures are retained under canonical
`output/playwright/native-intent-2026-10-08/settings-pending-final/`.
Root inspected all9 save-pending/failed/succeeded images at all supported sizes;
independent review inspected all15/source/test/bundle and found the scoped
save/check guard correct. The retained reviewer's effective model/effort remains
unverified. Review found an adjacent gap: `ImageTerminalSettlement` owns a separate
reservation-release write and subsequent settings refresh; its child-local busy
state does not reach the dialog close controls. That path remains open for a
focused follow-up, not qualified by this save/check fix. No release was attempted.
The new unfiltered browser run is active (handle46549) on frontend source/tests,
E2E/config/package files and generated static aggregate SHA256
`44d74f4af0ea6204812d34dc54088f7c25b84238ed3866282a86c7620d528544`.
It is not yet PASS; do not restart it merely for an observation timeout.
Native active task-check execution and provider-profile failed-save remain open.
Normal8841 and both owner projects/protected settings are unchanged.

Remaining: broader applicable recovery slices, Opening2 identity semantics/media and both rebuilt routes,
outstanding report-generation context/copy and other E22 states. This receipt
does not close the full Create → Revise → Recover run or creative acceptance.
