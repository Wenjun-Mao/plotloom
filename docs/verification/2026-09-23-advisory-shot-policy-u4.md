# Advisory shot policy: isolated U4 installation receipt

## Scope and provenance

This is implementation verification, not creative/media acceptance. The retained `暴风灯塔` U4 original and the prior live-intent source trial were not edited. A third isolated installation, `.local/relay/shot-policy-u4-trial/`, was restored from the original public snapshot `b267032e-1290-4819-859e-bb8e94dfc0ab` with the U4-era supported restore tool, then opened by current code. The original project retained Brief r1, accepted source-map graph r1, cast r1, art r1, script r2, and source storyboard review r2. The current runtime served the isolated copy at `127.0.0.1:8822`; no provider or media dispatch was made.

### Preview service lifetime (2026-09-23 follow-up)

The first `8822` preview was a turn-owned terminal process. Stopping that terminal session stopped its Uvicorn listener, so a later direct browser open returned `ERR_CONNECTION_REFUSED`; this was a service-lifetime problem, not lost project data or a failed bridge. The isolated copy is now served by the user's macOS LaunchAgent `com.plotloom.shot-policy-u4-preview` (`RunAtLoad` and `KeepAlive`), with no provider dispatch configuration. Its plist is `/Users/wjmao/Library/LaunchAgents/com.plotloom.shot-policy-u4-preview.plist`; its entrypoint and logs live only under `.local/relay/shot-policy-u4-trial/`. At verification, `launchctl print gui/501/com.plotloom.shot-policy-u4-preview` showed `state = running`, PID `32246`, and `lsof` showed that PID listening on `127.0.0.1:8822`. The exact browser URL opened successfully with the confirmed r2/27-cut proposal:

`http://127.0.0.1:8822/v2/?project=fbb913c8-534b-4439-ba68-211e70ec743d&stage=source#storyboard-review`

On this host, start an unloaded preview with `launchctl bootstrap gui/501 /Users/wjmao/Library/LaunchAgents/com.plotloom.shot-policy-u4-preview.plist`; inspect it with `launchctl print gui/501/com.plotloom.shot-policy-u4-preview`; stop only this preview with `launchctl bootout gui/501 /Users/wjmao/Library/LaunchAgents/com.plotloom.shot-policy-u4-preview.plist`. Stopping it does not delete or reset the isolated project. The LaunchAgent remains loaded for handoff. The isolated database still contains **zero** bridge intent jobs and **zero** media tasks; the accepted proposal remains r2 with hash `e22ef5e5ee815781c3836d04e8b56715fe034aca80c38011e4575f301da6d7b1`.

The public Brief API changed only `shotCountPolicy` from legacy strict to explicit advisory, retaining the 2–4 preference and every other Brief field. The Brief became r2. Source-map graph admission remained `current`; cast, art, script, and F5 source review remained `accepted` with no stale reasons. The canonical graph stayed ready. This is a policy edit, not a rewrite of F1–F5 source evidence.

## Exact bridge transaction

The public bridge preparation API created proposal r1, retaining **3 source scenes and all 27 F5 cuts**. It showed three `shot_count_preference` advisories (each source scene has 9 cuts against the 2–4 preference), no shot-count conflict, and the expected pending-intent conflict. The proposal froze the new Brief r2.

For the intent package, the prior live trial's r3 reviewed text was used as identified previous evidence. Before the public whole-package save, all **57** new targets were matched one-for-one to the prior r3 package by ID, target kind/ID, source coordinates, source content hash, and exact source excerpt; every retained reviewed text was nonblank. The new proposal did **not** claim a new inference: its `suggestionOrigin` stayed `none` and its `reviewState` became `author_saved`. Original model suggestions and their job provenance remain only in the earlier, unchanged [live trial](2026-09-23-production-bridge-live-intent-trial.md); they were not fabricated as fresh suggestions here. This is a technical carried-forward review, not human creative approval.

The public save produced installable proposal **r2** with hash `e22ef5e5ee815781c3836d04e8b56715fe034aca80c38011e4575f301da6d7b1`, zero conflicts, and three visible advisories. Explicit confirmation of that exact revision/hash atomically installed StoryBible r1, SceneBeats r1, and Storyboard r1. After an actual service restart, the public API still reported an accepted bridge, the same proposal hash, 3 scenes, 27 cuts, 57 intent entries, ready canonical heads, and current/accepted F1–F5 states. The isolated project has zero `v2_media_tasks`.
The installed storyboard's `storyboard.v2` review contains three `shot.count.*` results with `required=false`, `status=not_applicable`, `severity=warning`, and actual/preferred evidence of 9 versus 2–4; its other gates remained installable.

At 1440×900 and 1920×1080, the rebuilt workbench displayed the confirmed bridge, 27-shot count, and three nonblocking notices without layout clipping in the inspected viewport. Screenshots: `output/playwright/shot-policy-u4/bridge-1440x900.png` (SHA-256 `9dc0b3a743355db8b36c634530f9c6ab396d6924824ae58cf5f24011b1cfc271`) and `bridge-1920x1080.png` (SHA-256 `4b5a241290a379ec848f270c72054bd1d4f12e1c151ea43e318c46a31aab7bcc`). The browser console only reported expected sandbox blocks for scripts inside optional upstream report iframes.

The protected original's post-trial hashes still match the pre-trial record: `project.json` `e4ad93038f1d7972cd7e48ef208aaeae53eeeabd3fef6fd124e3fe27bf9873ff`, `project.sqlite3` `8daae34d30a97d2847f514a3270183eb4985564d63db589d29b5f91f3a86ad97`, and `application.sqlite3` `4a550c52c4449a1848a7bc7f20697993f312483a0d7ddac54d985e2ff3f175df`.

## Boundary

Installation proves the revised policy and bridge contract can admit the retained source shape without splitting, omitting, regenerating, or retiming cuts. It does not approve the creative quality of the carried-forward intentions, select references, generate images/video, or establish playback acceptance. Those remain separate owner decisions and workflow steps.
