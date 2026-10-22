# Cast and Art report reading audit — 2026-10-08

Status: **PUBLISHED / LOCAL QUALIFIED / EXACT-HEAD CI RUNNING**. This extends E22 in the
[whole-product audit](2026-10-08-whole-product-ui-audit.md), not completion of
Create → Revise → Recover or native-media acceptance. Current implementation is
published at executable `60921d69709ffb2678d6a1049dc78fe9574e9614`.
[Exact-head full CI](https://github.com/Wenjun-Mao/plotloom/actions/runs/37780741950)
is running; remote verification and product acceptance remain separate from
the completed local gates. Normal8841 already serves the checked assets.

## Demonstrated wording and capture repairs

Art's primary explanation previously required readers to reason about `art.json`,
“当前 JSON” and whether reading would “接受” a proposal. Root inspected the178
inline/enlarged report at the short desktop. The owning explanation now says:

> 报告保留助手交付时的美术设定；提示词已完整展开，报告内的复制、导出和图片放大功能已停用。如果之后修改了设定，请以当前内容为准。阅读报告不会确认或修改设定。

Only app-owned guidance changes. Original reports, current accepted content,
report URLs, CSP, sandbox, referrer policy, confirmation and generation handlers
remain unchanged. Original mixed-language creative prose is retained, not treated
as interface wording to rewrite.

Two failed capture contracts were repaired at their owning test layer:

- 178: a long paragraph's end remained0.34375–0.453125px beyond an exact frame or
 viewport boundary. Use ordinary8px reading margin and round necessary scrolling
 upward; retain exact bounds, not a numeric tolerance or a centred partial paragraph.
- 179: short-desktop Cast reopening waited for embedded geometry while its parent
 frame was outside the outer viewport. Expose/verify the parent frame before
 waiting for the child target. This repairs sequencing; it does not establish
 Chromium scheduling as the underlying cause of the45s wait.
- 180: an incorrect patch working path left old code running. That run was
 explicitly interrupted:14PASS,2interrupted,2not run. It is not qualification.

## Final focused reading packet

`output/playwright/full-lifecycle-2026-10-07/181-cast-art-report-final/`:
**18PASS49.8s**, including9 expanded static-report journeys and9 adjacent Art
journeys. The new report matrix is1700×900,1280×768,1280×460 only:

- 42 Cast captures: four roles, full long synopsis/prompt endings, relationship
 text/list, image caption, disclosures, prompt collapse/reopen and report reopen.
- 15 accepted Cast captures: original report before and after an explicit disposable
 reopen/edit/save, with the current-content divergence note.
- 39 Art captures: inline top/anchors/prompt/image/bottom, disclosure and prompt
 collapse/reopen, enlarged report top/prompt/bottom, Close/Escape/focus restoration.

These96 captures use disposable real FastAPI/file-SQLite projects with pinned
renderer fixtures, not native creative generation. Cast's four-role report-only
fixture is distinct from its admitted one-character candidate. Its1px image is
not artwork evidence. Accepted Cast uses an original identity marker, not a rich
report. Art's report-only image is also a fixture. Reading performs zero API
writes; exact accepted/candidate state and original report bytes/hashes remain
unchanged. Cast's appended hostile scripts remain sandbox-blocked; report copy,
export, search and zoom controls retain their static reading boundary.

Independent GPT-6 Luna/Max directly inspected all102 PNGs in181:96 report
captures plus6 adjacent mocked/simulated Art captures at1920/1440. No confirmed
report clipping or app-owned wording defect remains in that packet. Root separately
inspected short Cast reopen/prompt-end, short Art guidance/modal prompt, accepted
Cast divergence and wide fourth-role captures. Relationship-heading/list pixels
do not establish the entire map's visual state; image placeholders do not qualify
art quality. Full-page/element crops are not viewport-reachability evidence.

The independent reviewer flagged a toolbar crossing the lower action row in four
adjacent mock full-page/element captures. Root inspected those crops and the actual
normal8841 retained Art reference at all three supported sizes in184:
the complete action clears the58px toolbar, is inside the viewport and its centre
hit belongs to that action, with zero writes. All three actual viewport PNGs were
directly inspected. The existing action is correctly disabled for stale content;
no selection was attempted. This establishes viewport visibility and hit testing
only, not action operability or a new reference-selection qualification. The crops alone do not
demonstrate a product overlay defect.

## Reboot and retained native failure

The owner confirmed a computer crash/reboot during unfiltered182. No Playwright,
Vite or fake-runtime processes survive, and no final `.last-run.json` exists.
Before the observer repair, the875 inputs remained unchanged after reboot at
`74639d20b26d3bdeb5658bc99a63d69da2c5dc5391e796f175b1cedda42c35b8`.
**182 is incomplete, not236PASS.** Preserve its artifacts; do not manufacture
completion or redispatch native jobs because processes disappeared.

Its branching playback failure is a separately completed assertion before the
later interruption. Correctly attributed CDP player `05C1DEE19FD2BE67BE70768503E9A33F`
loads canonical playback, records Starting → Suspended → Resuming and Play/rate1,
but no decoder selection or Playing. Clock0, zero presented frames, connected,
unpaused, fully buffered0–6s and no native error remain at failure. The earlier
FFmpeg decoder properties belong to another authoring player, not this player.
The9s poll completes at12:14:55.411UTC; snapshot/attachment/teardown complete
by12:14:57.183. Reboot alone cannot reclassify that failure as a truncated poll.

Independent GPT-6.1 Sol/High reviewed exact CDP, trace and code. Underlying
pipeline-startup cause remains unproven; no product playback fix is justified.
It also found a diagnostic observer skipped videos inside inserted wrappers.
The test now observes descendant videos and installs listeners on existing videos
when clearing a measurement phase. Native clock/ended and9s bounds remain intact;
additional Playing-event assertions strengthen the supplemental trace. This is
an observability repair, not a media-clock fix. Independent Sol/High found no
substantive observer defect. The185 focused native replay passes3 tests in1.8m;
the final candidate further requires six distinct Playing identities in each
measurement phase, rather than six aggregate events. All three native cases pass
in186 as well; its independent bootstrap transport failure is recorded below.

183's single plain-player control serves the exact retained119093-byte derivative
unchanged over actual loopback206, SHA256
`9db2ca070c77bec620130338cb4494bb1a7058aa99c66d8e708349b11810eb49`.
Default bundled Chromium151.0.7922.34/Desktop Chrome, real click and9s playback
bounds: native ended at6s,144 presented frames, zero dropped frames, visible,
no native error. FFprobe and complete FFmpeg decode also pass. Fresh-context
success narrows the diagnosis; it does not explain the earlier application stall.
The control uses preload auto and Starting → Playing; the shipped player uses
preload metadata, and182 stalled during Suspended → Resuming. Thus183 does not
exercise the implicated suspended-start resume path or establish its cause.
No mute, transcoding, worker/timeout/retry or decoder override was introduced.

188 repeats the exact-byte plain control with the shipped metadata preload:
same Chromium151/default launch, actual206, real click and unchanged9s bounds.
Native ended6s,144 frames/zero drops, visible/error null. This control also passes;
its correctly attributed CDP player traverses Starting → Suspended → Resuming →
Playing and selects FFmpeg video/audio decoders. Independent Sol/High verifies
the same evidence and final distinct-identity assertions. This closes the plain
control's preload/startup-path mismatch, not182's cause: a fresh context does not
reproduce the accumulated authoring/application conditions or qualify that gate.

Normal8841 recovered automatically and is healthy after reboot; no restart or
generation redispatch was needed. Fresh protected-owner readback remains exactly
`df1716a80d93bdf9aeaf2565464ac030340ab035cf86198d5355befea075f2a5`
(Wind17/Rain67 managed files, complete owner DB rows/schema and three settings).
The later host read-only SQLite checks could not open WAL state within the
host sandbox. The same mode=ro/query_only snapshot inside the recovered service
container, with host file/settings hashing, returns the identical aggregate.
No database content, file permissions, deployment or settings were changed.

## Final local qualification

Fresh frontend713/96files4.72s, application/E2E types, deterministic build,
lock/API F401 and diff checks pass. Observer source review and185 native replay
pass; E2E types pass again after the distinct-identity assertions. Unfiltered186
finishes235PASS/1FAIL6.9m, with875 inputs unchanged before/after, SHA256
`b18496812ff8b9a83ccd7636761e89f73c4fe774c2b4cbf898da001d5f0a44c3`.
The failure is before Brief rendering or geometry checks: first onboarding click
waits45s on an empty root. Independent Sol/Medium and root pixels/trace attribute
the missing UI to initial creator-ui.css and required dependency-module requests
returning `net::ERR_NETWORK_CHANGED` at12:40:47.555UTC. The source of Chromium's
network-change signal remains unknown; later Vite teardown is not its cause.
No Brief patch, retry, timeout or worker workaround is justified.187 verifies
both unchanged alignment/bootstrap criteria:2PASS4.6s. That focused read does
not convert186 into a pass. Fresh unfiltered189 completes **236PASS6.6m** at
the same875-input fingerprint, verified unchanged before and after. It includes
all three native playback cases and the final six-distinct-Playing-identity
assertions.189 qualifies this local candidate;182 and186 retain their failures
and evidence limits. Default workers, retries, decoder and timing bounds remain
unchanged. No older gate is used to qualify this final candidate.
Fresh wheel/installed smoke and archived prompt reader pass. Wheel directory
`/private/tmp/plotloom-cast-art-report-wheel-20261008/`, SHA256
`d8a1f1f0545a7d6585ea665687fdefc5e112290f701cf33a7f99b1c4e603c21c`.
Executable publication is complete; the one full, unfiltered CI dispatch binds
to the exact executable revision above. CI is not yet claimed as passed.
Python1245 is reused from unchanged backend source/tests, not freshly executed.

Normal8841 remains healthy and serves the checked assets byte-for-byte:
workbench.js `5d5b2deb71057b94d5cf98206447bc2e88103430a0761e8d0505cb61b97b33a7`,
workbench.css `000aac5623f5ce4cf63f007979f7e7d1e09f9aa3698a1da3556fe400dbec3b7c`,
workbench2.css `42beb639a4681beb6bea3a3b04916ee1eb63481a821eb42994f152de7e2d6850`.
No backend source change, manual restart or generation redispatch was made.

The native Art view also exposes the raw English prerequisite
`an accepted source, outline, current section map, and installed graph are required before preparing cast`.
Its plain StageGuide is separate; the raw line remains a named wording finding,
not creative prose and not repaired in this checkpoint. Independent Sol/Medium
traced successful GET `/art` → Art `_stale` → shared context delegated to Cast:
the Cast-specific exception is projected as `staleReasons: string[]` and rendered
directly. This is not necessarily an HTTP failure. Shared source/map/graph
prerequisites and current-Cast prerequisites need distinct named ownership and
structured diagnostics; string-matching translation in ArtPanel is not a durable
repair. A separate contract checkpoint must retain raw evidence, content and
stale action restrictions while directing readers to the correct owner.

Prepared/waiting/stale Outline and other Creator/Professional permutations,
original Outline's fractional-minute tile, actual native route playback and
same-project post-install revision/rebuild remain open. This checkpoint does not
turn those states into PASS.
