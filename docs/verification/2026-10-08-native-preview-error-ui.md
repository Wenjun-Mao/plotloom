# Native preview error presentation — 2026-10-08

Status: **SCOPED UI VERIFIED; LOCAL GATES PASS**. This extends the
[whole-product visual/text audit](2026-10-08-whole-product-ui-audit.md), not
native playback or artistic acceptance. The full lifecycle remains PARTIAL.

## Demonstrated failure and diagnosis

Read the existing disposable8861 opening job
`vj_c121f94f27dc4704ac27dbc3cbdd2b8d`; no prepare/dispatch/selection was repeated.
Its frozen contract is current H3 V2, quality8,832×480,24fps,124frames. The
downloaded184434-byte original exactly matches stored SHA256
`3d5baba0069c255123894246362c10c4e133d02ce4b030767441bcc6972ac9f3`.
FFprobe sees H.264 High/AAC and5.167s; complete FFmpeg video/audio decode exits0.
This is not hearing, creative approval or browser playback acceptance.

Installed headed Chrome154.0.8037.97 received trusted play/playing, advanced to
5.167s, but never reported ended and then returned native error3:
`PipelineStatus::PIPELINE_ERROR_DISCONNECTED: video decode error!`.
CDP identifies VideoToolboxVideoDecoder, FFmpegAudioDecoder, DecoderStatus5 and
pipeline error24. This establishes a browser decoder disconnection, not its
ultimate cause. Browser GPU crash count2 was observed; causation is unproven.
A separate unchanged headless software control initially failed a15s ended wait
at clock0; a later read found trusted ended at5.167s and no decoder error. Keep
both observations: the late event is not a clean bounded interactive PASS.
Exact CDP/events are retained in `output/playwright/full-lifecycle-2026-10-07/`
as117-chrome-native-diagnostic.json and117-software-control-diagnostic.json.
Original screenshots117 retain the pre-repair reading state.

## Root cause of the UI defect and repair

The original and segment native players had no app-level media-error state,
named read-only reload or exact secondary evidence. Their shared owner now
provides those without changing the underlying file, browser decoder, generation,
selection or story-player state. Source changes create a fresh local error state;
playing one original/segment pauses the other previews in either direction.
Copy says what reload does: attempts to reopen the current video, without
regeneration, changing selection or autoplay. A player-local stacked notice
keeps recovery labels readable; raw browser evidence is preserved, not translated.

## Verification and exclusions

- New unit3PASS: exact error evidence, same-source load/no play/API, source
  identity reset, detached old errors, loaded-data reset and mutual preview pausing.
- Full frontend631PASS/84files; app/E2E types and deterministic buildPASS.
- Focused browser1PASS8.6s: explicit native read fault injection against the
  observed absolute media URL, observed requestfailed and native code/message,
  exact identity after named reload, paused state, zero non-GET writes and
  unchanged unselected job/selectionRevision0.
- Final120-preview-error-full-notice-pass has12 directly root/independently
  inspected collapsed/expanded PNGs: original and segment at1700×900,
 1280×768,1280×460. Full notices clear the58px topbar and stay inside the viewport;
  retry/summary labels are single-line, raw evidence readable, no page overflow.
- First injection failed because a relative src did not match the absolute
  intercepted request; trace showed HTTP206, not an injected fault. The corrected
  test awaits URL-specific requestfailed. Its initial trace was overwritten before
  preservation; the failure output remains in task history, not a retained-trace claim.
-118 pixels exposed squeezed segment controls.119 verified the layout but
  cropped original guidance by scrolling only its retry button; those captures
  do not qualify full original notice visibility.120 centers/asserts the full alert.
- An initial broader gate was intentionally interrupted for the demonstrated
  wrapping repair:13PASS,4interrupted,193not run; it is not qualification.

- Full backend1245PASS7m44s, with one existing Starlette deprecation warning;
  lock/API-import lint and wheel/installed smokePASS. Wheel is retained under
  `/private/tmp/plotloom-preview-error-wheel.rj4QHS/`.
- First frozen full gate207PASS/3FAIL6.9m: all three failures were45s workbench
  fixture startup timeouts before page navigation or UI assertions, with empty
  browser network evidence. Exact failures are retained in121-preview-error-full-gate-failures.
  Concurrent backend/wheel workload was present, but its causation is unproven.
- After other gates finished, unchanged four-worker/45s fixture replay passes
  all210 tests in5.9m, including both unchanged native media probes and this
  preview test. Evidence is retained in122-preview-error-full-gate-qualified.
  All851 source/test/config/static inputs have the identical before/after digest
  `fa1b61c0ad44a4af901bb5908196ca12c6813288d9ed743dba02fa9f0ba70e2c`.
  A clean replay qualifies this UI checkpoint, not the cause of earlier startup
  failures. Sequential readiness budgets and missing outer-timeout diagnostics
  remain a named harness follow-up; no timeout/worker adjustment was made.
- Fresh owner/protected settings recapture remains exact:
  `df1716a80d93bdf9aeaf2565464ac030340ab035cf86198d5355befea075f2a5`.

Executable checkpoint is committed and pushed on main as `552f1da`.
Later reader/gallery changes need their own qualification and cannot inherit this gate.
No mute, media rewrite, timeout, worker-count, fake-ended or retry workaround
was introduced. Native canvas spinner behavior is unchanged. The native candidate
remains unselected; raw/segment/all-route native acceptance remains unfinished.

## Separate source-audit follow-up

Read-only H3 audit found strict frozen-request validation gaps before capacity
reservation/polling and retained executable V1 branches. The current V2 job did
not downgrade. This is an unexercised contract gap, not the demonstrated decoder
failure. Before repairing it, root must verify preparation/admission/poll source,
preserve unknown-POST safety, reject malformed current requests before calls,
and retire executable V1 interpretation without relabelling historical evidence.
