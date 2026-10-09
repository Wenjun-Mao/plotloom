# Revised native project recovery — October9

Scope: E19/E21/E22 in the [current run](../roadmap/2026-10-07-full-creator-e2e-repeat.md).
This is revised-project evidence, not inherited first-install acceptance.
Project `90c0f895-48de-4b57-8725-4b6f72797633`, QA 原生重建·渡口信号,
on isolated8865/8866 with backend95074b1. Normal8841 and protected owners/settings
were not modified. No generation, selection, deletion or lease cleanup occurred.

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
- Prior243-browser/full-Python gates predate this small frontend change. They
  remain historical, not a fresh full gate for this candidate.

Remaining: revised snapshot/operator restore/copy deletion and broader applicable
recovery slices, Opening2 identity semantics/media and both rebuilt routes,
outstanding report-generation context/copy and other E22 states. This receipt
does not close the full Create → Revise → Recover run or creative acceptance.
