# U4 canonical-shot handoff and preparation visibility — 2026-09-23

## Scope and outcome

This is a bounded technical implementation, not product, creative, storyboard,
image, video, or playback acceptance. The accepted/current production bridge
opens each installed cut's exact canonical Storyboard shot through the existing
workspace route. That shot's existing media workbench now displays a read-only
summary of bridge source binding, exact source duration, current Storyboard
Approval, character-reference decisions, reviewed keyframe, video-backend
availability, and request-duration catalog compatibility. F3 art references
are identified as a separate owner, not misreported as consumed media choices.
The summary neither creates nor changes any decision, selection, job, or asset.
After review, its media evidence read now has explicit loading, ready, and
error ownership. A refresh immediately withdraws current media-derived data
from the full workbench, disables media mutation controls and exported-job
polling and durable media-draft writers, and shows unknown reference/keyframe
state with a read-only retry. Session draft text remains available for retry.
Bridge/backend read failures likewise offer retry rather than permanent
unknown status.

The root cause was split across owners: bridge review had no shot-specific
navigation; an invalid Storyboard route could retain a previously selected
shot; and the disabled H3 backend response hid the qualified-duration catalog.
Independent delta review also found that accepted F5 status alone could leave
links visible after a downstream canonical Storyboard edit. The current-ready
installed-revision projection and drift regressions close that gap.
The fix belongs in those respective contracts. A current bridge-cut parser
gates links on accepted installation and an exact current ready Storyboard
revision, without changing the upstream bridge's acceptance; Storyboard
rejects an unowned shot ID; the read-only backend projection exposes its
catalog even when disabled. [ADR 0079](../adr/0079-f5-production-canonical-bridge.md)
records the durable boundary.

## Real-runtime evidence

The original retained preview at `127.0.0.1:8822` and its project were left
unchanged. An initial transient clone was used to test the patch; it was
stopped and moved to Trash. A separate retained, current-code walkthrough now
runs at
`http://127.0.0.1:8823/v2/?project=fbb913c8-534b-4439-ba68-211e70ec743d&stage=source#storyboard-review`.
Its isolated roots are `.local/relay/u4-shot-handoff-preview/{outputs,application}`,
copied only from `.local/relay/shot-policy-u4-trial/{outputs,application}`.
Its loopback Python process serves this checkout's `src/plotloom/static/` and
is supervised by `~/Library/LaunchAgents/com.plotloom.u4-shot-handoff-preview.plist`
(`com.plotloom.u4-shot-handoff-preview`). The preview script forces
`PLOTLOOM_ENABLE_H3_GATEWAY=false` and clears provider keys before importing
the app. Preview-only middleware rejects non-GET/HEAD/OPTIONS requests with
HTTP 405; a direct POST probe returned 405. This intentionally diverges from
the normal writable app only for the retained inspection copy.
`launchctl print gui/$(id -u)/com.plotloom.u4-shot-handoff-preview`
checks ownership; `launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.plotloom.u4-shot-handoff-preview.plist` stops only
this preview, and the matching `bootstrap` command starts it again. Its local
README carries the same controls. No preview roots are committed or pointed
at the original project.

The retained live copy returned `enabled=false`, `reason=h3_video_not_configured`,
and `qualifiedDurationSeconds=[5,8]`. Browser interaction showed:

- `opening-s1-c1` opens by its bridge cut action with exact source coordinates
  `opening / 1 / 1 / 1 / 1 / 1` and 6 seconds. It reports missing Approval,
  reference/keyframe prerequisites and disabled backend separately from
  “6 seconds outside the 5/8-second request catalog.”
- `dock-s1-c8` opens as its own route with exact 8-second source binding. It
  reports catalog compatibility, but explicitly does not equate that with
  physical output duration, media readiness, or playback proof.
- Reload, back/forward navigation, return to bridge, project switching, and
  an invalid shot route do not substitute a different selected shot. Unsaved
  source edits keep the established leave-page guard. Staling the bridge in
  a disposable test fixture removes its handoff action. Editing only the
  canonical Storyboard in that fixture also removes the action even while the
  source bridge remains accepted.

The retained current-code URL was manually inspected at 1440×900 and
1920×1080: exact bridge handoff to `opening-s1-c1`, return to bridge, and
handoff to `dock-s1-c8` all showed the corresponding source binding and
distinct duration state. The summary layout fits both widths; the final
1920 view had no horizontal overflow. Manual browsing produced GET requests
only. The browser regression creates and changes only its own temporary
fixture project; it has a request monitor asserting no browser writes.

## Executed verification

- Frontend focused unit suite: 5 files, 33 tests passed.
- Full frontend unit suite: 26 files, 207 tests passed, including same-mounted
  initial media-read failure/retry, prior-success refresh failure, old-context
  late responses, bridge/backend retry, and a populated-workbench integration
  case that disables media upload, stops exported-job polling and draft
  persistence after failure, and retains the unsaved direction text.
- Frontend and E2E TypeScript checks passed.
- Backend boundary suite: 14 passed (one existing Starlette/httpx deprecation
  warning).
- Bridge and H3 transport suites: 20 passed (the same deprecation warning).
- Real-runtime Playwright handoff scenario: 1 passed on a separate
  contract-valid 3-second-cut fixture, including project and route transitions,
  source and Storyboard revision drift, stale-link absence, and no browser
  writes. The 6/8-second contrast above is from the retained-copy manual view.
- The same Playwright scenario passed again after the media-read correction.
- Deterministic frontend build passed and refreshed the checked-in static
  bundle. Vite retained its existing large-chunk warning.

An initial generic F5A test fixture failed twice because its fractional cut
durations and scene count could not satisfy the bridge installer; this was
not a product regression. The test method was changed to the repository's
contract-valid installable-bridge helper before rerunning. No validator was
weakened to accommodate that fixture.

## Remaining boundary

The isolated copy still has no Storyboard Approval, selected identity
references/keyframes, media jobs, or playable routes. Twenty-six source cuts
are exactly 6 seconds while H3's currently qualified request catalog is 5/8
seconds. Source inspection of the deployed gateway's frame-grid function
computes 124, 158, and 192 *requested* frames at 24 fps for nominal 5, 6,
and 8 seconds (about 5.167, 6.583, and 8 seconds). The retained
[real 5/8-second canaries](2026-09-15-h3-unified-contract-live-canaries.md)
confirm those two physical outputs; no actual 6-second video was generated or
measured in this work or the separate H3 function check (specialist task
`01a0983e-0e5f-7171-950e-011adaf53303`). Thus simply admitting a nominal
6-second request would not prove exact physical source-duration equality.
Source/provider duration policy,
F6 quality and selection, and F7 playback require separate decisions and
evidence. No provider/media dispatch or acceptance occurred in this slice.
