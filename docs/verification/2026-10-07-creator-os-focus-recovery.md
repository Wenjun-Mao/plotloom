# Creator editor recovery after real OS focus loss

Real OS focus loss passed for automatic380px and persisted350px editor widths
on disposable QA965671f3 at1700×900. The canceled resize did not resume;
the same textarea, text, selection and internal scroll survived. Both checks
kept the acknowledged graph draft unchanged and emitted zero mutation requests.
This closes the actual OS blur gap in C46/E22, not the outstanding native media
or post-install revision journey. Full lifecycle acceptance remains PARTIAL.

## Candidate and test object

Frontend5aff37e885fdd8b32f9282d8cc14a5366ee1a99e, documentation baseline4371464,
and unchanged e941780 Python ran on owned8871/8872. Project
`965671f3-491c-4c30-ba26-03fe20463eba` is the existing disposable structural QA,
not either protected owner project. It has eight nodes, eight edges, two nonblank
merge contracts and canonical graph revision0. The selected node was
“QA 保留输入”; its original summary was empty.

Normal8841 serves the same checked frontend bytes. This OS check operated only
the owned QA browser, did not restart/reload busy8861 or continue a native job,
and did not call any image/video provider.

## Focus emulation explained the earlier failed method

The installed Playwright CLI runtime enables
`Emulation.setFocusEmulationEnabled({enabled:true})` for its main frame.
The [official CDP contract](https://chromedevtools.github.io/devtools-protocol/tot/Emulation/#method-setFocusEmulationEnabled)
states that this emulates a focused and active page. It can therefore mask a
real foreground switch. A previous Finder activation with no observed blur
did not establish a product cancellation failure.

For this exact owned QA page, a documented Playwright CDP session disabled that
override before the check. The page began with `document.hasFocus() === true`,
a focused textarea, and a genuinely held mouse drag with pointer capture.
AppleScript activated Finder; System Events independently reported Finder PID737
as foreground. The browser then reported `document.hasFocus() === false` and
trusted textarea/window blur events. Returning to Chrome produced trusted focus;
the still-held mouse moved again before release, proving the canceled gesture
could not resume. This was not `dispatchEvent(new Event("blur"))`.

## Observed results

| Case | Held width | Width after blur and later held movement | Stored preference | Preserved selection and scroll | Graph and requests |
|---|---|---|---|---|---|
| Automatic |469px|380px|`null`|[2,8],0px|r32 exact; zero mutations|
| Persisted |439px|350px|350px|[1,7],80px|r32 exact; zero mutations|

Automatic trusted window blur occurred at23:33:24.952 UTC; persisted blur at
23:34:08.733 UTC. Both were followed by lost pointer capture at the restored
width. Both returned to the same focused textarea with the exact text
“QA OS focus recovery：保留未发送正文与光标。” retained. The scalar results and
trusted events passed explicit assertions. Event arrays also retain later setup
observations; those later events are not part of the canceled-drag assertion.

Initial setup had deliberately typed that temporary summary. The first broad
before/after comparison saw the expected draft autosave r31→r32, so it was not
a zero-write qualification. Author text changes update the draft safety buffer;
the debounce and workspace blur flush save it without canonical confirmation.
The two qualified resize checks began only after that exact save acknowledgment.
Resize cancellation restores presentation; it does not discard or suppress
legitimate author-draft saving. Independent read-only source/evidence review
confirmed this distinction and found no product defect requiring a patch.

## Pixels evidence and cleanup

Root directly inspected viewport screenshot
`output/playwright/full-lifecycle-2026-10-07/37-os-blur-restored-350.png`:
the editor remains beside the graph, its350px width and selected text are visible,
and the row controls remain centered. Screenshot SHA256 is
`716d721822a15dd6dc823e7810fd2bc1ed3c43136c99bba0bf4b45529def7c2a`.
Raw trusted events, requests, scalar assertions and cleanup are retained in
`output/playwright/full-lifecycle-2026-10-07/os-blur-evidence.json`, SHA256
`88ca4264dee0e275da6d9d8f49ad902670e365b2dcbf1b9ca27b37817235bf8e`.
These ignored local artifacts are retained evidence, not checked-in source.

The original empty summary was restored through its named UI field, awaiting
the successful exact graph-draft PUT acknowledgment r33. Independent GET then
matched the complete original payload except the intentional draft revision/time;
all eight nodes, eight edges and two contracts remain, canonical revision0.
Double-click restored automatic380px, stored width`null`, pageY545.5/chartX0.
The temporary request observer and event listeners were removed, and CDP focus
emulation was restored to Playwright's default. No application code, runtime
configuration, canonical content or owner data changed.

A cleanup reload encountered the existing leave-page guard for uncanonicalized
authoring work. Its GET-response waiter timed out while the modal blocked reload;
this is retained as a harness failure, not a data-loss claim. After accepting the
owned QA warning, separate UI/GET checks confirmed r33, canonical0, the original
empty summary and380px. Independent review matched the explicit-save contract
and the same previously recorded guard; no stale-ref or recovery failure was found.

CI37701584435 verification passed at the23:37 UTC readback; both full browser
shards were still running. CI is not yet claimed wholly PASS. Earlier failed
OS methods and software gates remain in the dated ledger/history unchanged.
