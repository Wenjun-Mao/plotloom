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

Remaining: broader applicable recovery slices, Opening2 identity semantics/media and both rebuilt routes,
outstanding report-generation context/copy and other E22 states. This receipt
does not close the full Create → Revise → Recover run or creative acceptance.
