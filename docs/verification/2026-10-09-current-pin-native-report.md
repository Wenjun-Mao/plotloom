# Current-pin native report and retained-production qualification

The full Create → Revise → Recover run remains PARTIAL. This closes a bounded
native renderer-execution and replacement/cancellation check, not new story
acceptance, media generation or media-quality acceptance.

## Identity and actual execution

Application4bbf8c2; documentation headab441eb; native QA8865 project
`90c0f895-48de-4b57-8725-4b6f72797633`, project revision2/lifecycle9.
Exactly one optional Storyboard candidate was prepared/sent through the mounted
UI, using the configured existing text task without model/settings changes:

- Job `ch_2642aec3f64e43879f75881c951ec9f1`; request hash
  `84e29fd7f73858d2a142f0e407fc4f6a25a7cebee93999c323d42885a4fce231`.
- Owned renderer fork `4f9b2128c82adf623f594ba714c97d0afcfc16a2`.
- Native task `01a0dfa6-40ae-7cf2-82eb-edcde7a8fcc0`, completed turn
  `01a122fb-e4b6-7f11-9fa8-72d4fd11febf`; delivered ready, not accepted.
- Delivery `1e37af79-f285-4e6c-9cac-c85dcd34cfa2`; candidate SHA
  `b4ea3c5e0ffed28a9a8dec8b5951d921b1b5783b6fbaa75c3e50f13db6c19c71`.
- Report/archive SHA
  `d2c747bb30044ca65005e9cb23ec4211e776523cc5bf39a967b45fa0fbf43bc1`;
  completion SHA
  `e9f0f994d82bf112bc860f65473a8fc85505b2654787463b24cbf6453fd39d4a`.

The server ingested this real native delivery. Its report shows16/16 executed
checks and1 explicitly skipped optional recipe gate; the total20 seconds is
labelled aggregate, not one15-second playback route. Planning/reference grouping
is not represented as actual generation. Native model/effort selectors were not
exposed in the completion receipt; no inferred model claim is made.

## Browser provenance correction

The long-lived Source tab had loaded JS SHA
`7d3a70d77a31325e0cdd5eb0d83db20eef07dfdbf0f5df7889330a41959c9bf6`,
not the served/file SHA at that earlier reload checkpoint
`f0c658027cb4e90ab8f3b9c60826ad55938721ba68e061db8dcd28a43cbc2d5e`.
The UI-owned prepare response already said retained; that old client lacked
`acceptedReviewState` handling and displayed stale authority labels. This was
not evidence of a missing refresh dependency in current source. All six native
prepared/waiting captures from that client are disqualified current-client proof.
After reload, actual network response1012 matched that checkpoint's JS bytes, and all
three desktop ready-state captures correctly show retained accepted evidence
and blocked production. No generic refresh workaround was added.

## Actual reading and clean cancellation

Root inspected current ready-state pixels at1280×768,1280×460,1700×900, the
mounted read-only report and its direct supported static-report route. Root and
an independent agent inspected top/long-prompts/gates/end viewport slices; all
12 report captures are readable without overlapping columns or a fabricated
PASS on the skipped gate. Short-window views require ordinary scrolling; they
do not establish that an entire report fits at once. A timed-out smooth-scroll
locator was replaced with real wheel scrolling after diagnosis; the subsequent
capture command's hung completion was terminated, not counted as a test PASS.
The retained PNGs were separately inspected. CSP still blocks report scripts.

The archive GET returned exact delivered bytes. Static GET returned a separate
presentation projection, SHA
`efa8b4af17050cce4ecb9e7bd0f3526166fd9f664c6006e07a1262446d888333`;
neither request rewrote the archive. The historical accepted report remains at
old pin266af29/report8ac6996 and is not current-pin execution evidence.

The named “拒绝并取消此评审” action cancelled the optional candidate, without
acceptance or a rebuild. Fresh23:38:09 readback restored accepted Storyboard3
and r12 installed production to current. All eight content/media responses are
deep-equal to the pre-prepare baseline, all58 managed asset hashes and all four
selected records are unchanged; revision2/lifecycle9 and idle registry remain.
New cancelled-job history is an expected QA write, not whole-database equality.

Evidence: candidate worktree `output/playwright/board3-r13-2026-10-09/` contains
before/after JSON, loaded-client diagnosis and current ready-state PNGs. Normal
repo's ignored directory of the same name holds12 fresh report PNGs plus mounted
reader/before-cancel/restored-current captures. Only disposable QA was changed;
normal8841, protected owner content/media and settings were not activated/reset.

## Findings and remaining scope

The independent audit also directly inspected all18 current archived Bible
character/location/prop top/bottom desktop fixture pixels. No clipping was found.
The [presentation-authority follow-up](2026-10-09-presentation-authority-qualification.md)
repairs primary provider protocol wording, availability-readiness projection,
read-only Bible editing labels and premature version-change/rebuild guidance during
a cancellable replacement-review pause; its own gates remain separate from this report.
Single-segment report cards using half the width are optional polish, not a
blocking defect or authority to expand this fork. No further native dispatch is
required for these frontend presentation repairs.

A bounded client-side503 snapshot fault was also exercised in the same current
native QA tab. Exactly one POST was intercepted before the server; no snapshot
was created, the named action became available again, and no receipt appeared.
Root directly inspected all three `native-snapshot-fault-*` desktop captures:
the natural failure text and Close control are readable. The interceptor was
removed in `finally`, and Close cleared only the error. This qualifies failure
presentation, not a naturally occurring server outage or server-side recovery.

Exact CI38000995714 on ef16210 completed SUCCESS:1,464 Python,1,025 frontend
and both browser shards (142+132) pass. It does not qualify the later frontend delta.
Current software results, earlier OS blur/recovery and unresolved capability
boundaries remain in the [final-candidate receipt](2026-10-09-board3-recovery-and-final-qualification.md).
