# Creator stages 2–3: final live checkpoint

Status: complete at 10:14 UTC / 06:14 Toronto, 2026-10-02. All content acceptance
and reference choices are provisional agent decisions in the isolated test copy;
owner creative acceptance and production selection remain pending.

## Source and runtime

Reviewed/pushed source is `b348cc07eda6e944d1a19f91a0837b186042f5f3` on `main`,
including source-currentness implementation `27710e3`. The manager's independent
GPT-6.1 Sol / Medium review found no remaining scoped findings. Its committed
gate passed 910 Python tests, 37 service checks, 289 frontend unit tests and both
typechecks. Those are implementation checks, separate from the live evidence below.

After confirming idle workers and free reservations, the coordinator restarted
only its owned isolated runtime and copied the reviewed frontend assets into
`.local/unattended-2026-10-02/static`. Owned PID is **83040**, exec session **86937**,
ports **8851/8852**. Data root is
`.local/unattended-2026-10-02/final-installation`. Normal services on 8841/8842
were not restarted. The static copy exactly matches `src/plotloom/static`.
External bridge credentials retain their existing private permissions; no values
were included in evidence. Workbench health on 8841/8851 and authenticated owned
bridge health on 8852 passed. Unknown earlier roots/jobs remain quarantined.

Stable UI: <http://127.0.0.1:8851/v2/?project=ee271b49-f384-414c-9711-452ee6333b84&stage=source#storyboard-review>.

## Actual UI outcome

- Reload, navigation entry and aggregate refresh visibly report retained
  Storyboard r1 stale under Script r3, with production preparation disabled.
  `currentness-fixed-stale-after-entry-refresh.jpg` records the repaired behavior.
- Fresh F5 job `ch_46006654ef0845138178aa3398b12eae` was prepared and sent once
  from the committed source, bound to Script r3, Art r2 and Cast r3. Complete raw
  JSON and original HTML report review covered three segments and twelve cuts.
  Every ordered beat is covered: five opening, three cafe and four home cuts,
  each 2.5 seconds. Routes estimate 20 and 22.5 seconds. Exact incoming/reply
  text, brief gaze, single choice, exterior cafe stop and home reply/continuation
  remain faithful; no extra people, speech or ending was introduced. Thirty
  seconds across mutually exclusive endings is not a playthrough duration.
- Explicit provisional acceptance created **Storyboard r2**, content hash
  `c89983d405464d338cb77e610ea83eea036bd20d2655c799b8f1808be74adfb0`, bound to
  Script r3 hash `bb63a123d8b0903ed94026436b71b110018550c65f2bb24575a0e000a17348c7`.
  Both cafe and home routes were exercised in the actual Storyboard reader,
  without media. Screenshots: `storyboard-r2-script-r3-accepted-ui.jpg`,
  `storyboard-r2-reader-cafe.jpg`, `storyboard-r2-reader-home.jpg`.
- P01's revised-requirements loop changed the prior three-quarter phone to a
  front, near-orthographic blank screen for later exact text compositing. Modify,
  prepare, explicit send, delivery check, enlargement, comparison and reference
  replacement were distinct UI actions. Job `ij_708a71d7b87b4a76a15ac60facf55caa`
  delivered `exec-738591fa-c131-4bcd-a069-5fab8a6f3b40.png`, SHA-256
  `da6e133790c57ddc53fe7937a39e283304ec1bc9778f12141d3ac37d91c6b373`.
  Earlier proposal and choice remain intact in history. Screenshots:
  `p01-front-view-enlarged.jpg`, `p01-front-vs-three-quarter-compare.jpg`,
  `p01-front-view-selected-ui.jpg`.
- S01's purposeful revision prioritised the existing street's two visible
  directions over the earlier broad forecourt. Separate prepare/send job
  `ij_e4a06b74e72144458feae986004bc329` delivered
  `exec-88a484de-2b1b-4995-abd6-e1ead6ca9d48.png`, SHA-256
  `6126a9c6266d8ace0280a2533423e3ec3e70ce80711ea8ee0633671fe6cc6837`.
  Enlargement and side-by-side comparison showed clearer left/right street
  continuations and a short approach anchored by the porch edge/threshold.
  It was explicitly selected provisionally, and the choice persisted after reload.
  The first new render still obscured the junction; the specialist reassessed
  within the frozen request before delivering the second, retaining both.
  Screenshots: `s01-two-directions-enlarged.jpg`, `s01-two-directions-compare.jpg`,
  `s01-two-directions-selected-ui.jpg`.

Cast r3, Art r2, Script r3 and Storyboard r2 are accepted/current with no active
candidate or stale reason. C01/S01/S02/P01 references are current. C01 and S02
were retained from their earlier reviewed copy decisions; no blanket regeneration.

## Verification and preservation

Evidence lives under `.local/unattended-2026-10-02/evidence/`:
`f5-r3-full-fidelity-review.json`, `f5-r2-current-reader-receipt.json`,
`p01-front-view-final-receipt.json`, `s01-two-directions-final-receipt.json`,
`stage23-complete-state.json` and `stage23-complete-preservation.json`.
Delivered job/request/revision/skill pins and output hashes match; new image
filenames are exact returned basenames and copied bytes equal staging sources.
Previous image proposals/decisions and both older frozen six-file job sets remain
unchanged. Historical renamed receipts were not rewritten to satisfy the new rule.
Fresh `stage23-complete-original.json` exactly equals the manager's baseline
across seven API states, 73 SQLite tables and 67 managed files.

Cleanup refused the tool-owned 0755 staging root. All generated sources remain
unchanged, including both S01 attempts. No chmod, deletion, original canon write,
normal restart, H3 call or production installation occurred. The final verification
helper was adjusted to check the package wrapper as a superset of the frozen
request, resolve unique run-job paths instead of same-named dispatch directories,
and authenticate bridge health. Initial helper failures made no product changes.

## Idle handoff and limits

Text worker `01a0fb4f-60d9-7062-883a-e00f1d17d493` (GPT-6.1 Sol / Medium) and
image worker `01a0fb4f-5f01-7e21-a8c6-ea5f662c676f` (GPT-6 Luna / Max) are idle;
both reservations are free. Native completion cursors are respectively
`b6e60f8a-d06d-4d8c-954a-1aacf62c2822:17` and
`106b2cae-44de-4f5b-8afe-cfa79cc29aa5:31`. After independently reviewing the
checkpoint and confirming idle state, the manager archived these completed
workers, then their coordinator, and unregistered the three Relay routes.
Historical receipts and specialist settings remain intact; stage 4 must bind a
fresh specialist before new dispatch. Only the main copy UI tab is retained.

Images are exploratory: no reference images were supplied, continuity is
text-guided, and detail panels are generated views rather than verified pixel
crops. S01's distant parapet/horizon is incidental/unverified, not evidence of a
sea view. The blank phone reference does not supply the story's exact visible
messages, and no text compositor currently exists. Stage 4 must explicitly
resolve their media presentation and inspect actual text fidelity. Reader
success establishes text/route behavior, not real-media playback. No measured
usage/cost delta is available. Production timing admission (2.5-second cuts versus
integer seconds), H3 enablement/media and playback remain the separate stage 4
owner's next work; no rounding or production workaround was applied here.

The manager independently read accepted Storyboard r2 and its binding, inspected
the current UI screenshot, viewed both new images, compared returned/delivered
hashes, checked every current accepted source status and served static hash,
and byte-compared the final original capture to launch. No additional code or
test changes accompanied this documentation-only completion checkpoint.
