# P2: bounded Wan audiovisual pilot

> **Archive status (2026-09-18):** Superseded historical plan; unresolved items remain unresolved and this file is not an active delivery plan. See [the current tracker](../../2026-09-17-playable-mvp-milestones.md) and [roadmap entrypoint](../../README.md).


Revision 1 — prepared 2026-09-12; **approved for P2 checkpoint 1 implementation**.
This remains not an implementation or video-acceptance receipt. User-selected provider, model and
100-second live allowance are settled; this planning turn makes no paid calls.
Baseline: pushed `4eb98d4dca6c0a73f91d876bf7e406a8d757bed9`, clean main;
[CI passed](https://github.com/Wenjun-Mao/plotloom/actions/runs/34675931283).

## Outcome and boundary

Produce one reviewed, locally stored audiovisual clip from an approved selected
keyframe and play it in Plotloom. Then test one adjoining clip before expanding
to P3 scene playback. One character, cinematic realism, one short canonical
DialogueCue, one simple action, environmental sound, no requested music.
Default pilot request: **5 seconds, 720p, native audio on**.

Only AtlasCloud `alibaba/wan-3.0/image-to-video`. No Grok, alternate provider,
automatic fallback, smart duration, last-frame conditioning, multi-shot generation,
voice cloning, separate TTS/mixing, general media platform, or branching player.
P1's manual image specialist stays independent; no V1 runtime imports or reads.
Text qualification Q remains open and is not a prerequisite for this manually
reviewed storyboard pilot; it is required for the combined qualified Alpha.

## Image checkpoint disposition

The [creator rehearsal](../../../verification/2026-09-12-p15-creator-rehearsal.md),
[corrections](../../../verification/2026-09-12-p15-corrections.md), and
[controlled framing trial](../../../verification/2026-09-12-p15-controlled-shot-framing-trial.md)
establish the bounded P1.5 workflow and same-person appearance across distinct
shots. This closes that development checkpoint, **not universal fidelity or
production approval of its outputs**. Identity, composition and state are
separate judgments. The profile image has a probable glove-side mismatch and
ambiguous camera/screen wording; exclude it from P2 inputs. A new input review
must bind the exact chosen asset, current character reference and intended motion.
Use the existing tight close-up only if that review passes. Off-frame glove state
is unobservable, not proven correct; keep the first clip's hands out of frame.
Do not automatically transfer any historical Approval to a new storyboard.

## Ownership and implementation surface

See [ADR 0031](../../../adr/0031-bounded-wan-video-production.md). Canonical Shot,
DialogueCue and AudioPlan remain author-owned. A video production snapshot freezes
the exact active Approval, canonical/entity revisions, selected keyframe/hash,
reference decision/review lineage, intended action, cue text/language/performance,
audio schedule, requested duration, public provider configuration and compiler
version. Provider-specific fields never become canonical story truth.

Build focused video contracts, persistence and execution modules; add migrations
after the actual current head (do not renumber history). Reuse existing artifact,
Approval and selection boundaries. Inspect `media.py`, `media_jobs.py`,
`managed_media.py`, `image_job_contracts.py`, `persistence.py` and API/frontend
integration seams, but do not revive legacy raw-Shot `MediaTask` submission.
Do not put a new catch-all subsystem into the already-large persistence/API files.

Proposed public surface (final naming follows repository conventions):

- Prepare a project-scoped video job from selected shot/keyframe plus expected
  revisions and client idempotency key; return frozen intent and admission issues.
- Explicit submit, status, reconcile/retrieve, cancel-intent, and select/review
  operations under `/api/v2/.../video-jobs`; server returns available actions and
  stable reasons. Cross-project access, archived projects and stale input fail.
- Read-only pilot-budget projection: limit, charged/reserved seconds, remaining,
  and exact attempt history. No browser-settable limit/reset endpoint in P2.
- Review/selection is immutable and revision-bound. New edits invalidate current
  applicability, not prior evidence. A provider completion is only a candidate.

## AtlasCloud boundary and unresolved qualification facts

Use one versioned Atlas transport adapter with an explicit Wan capability record;
never derive semantics from substring matches in an alias. Freeze public config;
resolve credentials only at dispatch from Plotloom's own server settings. Existing
`.env` key entries are present but not authenticated. Never put keys into jobs,
snapshots, logs or receipts; never send Authorization to artifact download hosts.
Preserve local HTTP/Tailscale service access; upload the approved image rather
than expose a local server publicly.

Model-specific docs require `image`, not V1's generic `image_url`; compile the
known fields only: model, prompt, uploaded image URL, duration, resolution, audio.
The pilot excludes `duration=-1`. Native audio is a requested capability, not
proof of correct speech. Check image admissibility and avoid silent crop/stretch.
[Wan model reference](https://www.atlascloud.ai/docs/more-models/alibaba/wan-3.0-image-to-video/generateVideo).

Upload approved bytes through multipart `uploadMedia`; the returned URL is
temporary transport data, never artifact identity. Qualify response parsing
against the documented upload envelope and one observed response.
[Upload documentation](https://www.atlascloud.ai/docs/upload-files).

Submit through `generateVideo` and persist the prediction ID before polling
`prediction/{id}`. Generic docs wrap prediction data in `data`, while the model
reference illustrates a bare object: resolve this discrepancy at the adapter
boundary with explicit fixtures/observed evidence, not arbitrary JSON tolerance.
Documented polling does not establish idempotent submission or remote cancellation;
assume neither until verified. Unknown statuses cannot become success.
[Prediction documentation](https://www.atlascloud.ai/docs/predictions).

The API-docs skill catalog had no AtlasCloud entry; official sources above were
checked on 2026-09-12. Recheck the exact 720p rate before the first paid call;
100 seconds is not a currency ceiling. Record quoted rate/currency/date and
estimated maximum separately from any available actual billing evidence.

## Enforced pilot allowance: 100 requested seconds

One durable pilot ledger shared by every P2 run/retry/project in the trial.
It survives worker and server restart; never create a fresh allowance by switching
projects, copying the test database or rerunning a script. Use one authoritative
trial database/ledger for all paid submissions. No concurrent paid trials.

In one transaction, check remaining allowance, reserve requested seconds and
claim the attempt. Two workers or repeated clicks cannot claim twice. Refuse a
request whose duration would exceed 100 seconds. Retain immutable ledger events.
No automatic replenishment or limit increase; only explicit new user authority.

Release a reservation only when dispatch demonstrably never began (for example,
preflight rejection or cancellation before the durable dispatch boundary).
After entering dispatch, conservatively count it even on crash, rejection,
remote failure, unknown outcome or later refund. A timeout is not evidence of
non-submission. An explicit new generation attempt requires a new reservation;
polling and artifact retrieval retries do not. Report this conservative local
accounting separately from provider billing. Stop at success; 100 seconds is a
ceiling, not a target to consume. Disable implicit POST retries in HTTP clients.

## Lifecycle, recovery and output

Keep execution, ingestion, cancellation intent and review applicability separate.
Before dispatch recheck active Approval, asset integrity and project lifecycle in
the same serialized admission boundary as claiming. An edit after dispatch leaves
the result retained but stale/ineligible, not cancelled remotely by implication.

- Crash before dispatch: safely resume or release an unclaimed reservation.
- Crash/timeout around POST without known ID: `outcome_unknown`; no resend.
- Known prediction ID: bounded backoff polling/reconciliation across restart;
  polling timeout retains pending/reconcile-needed, not remote-failed.
- Remote completed but download failed: retrieval-only retry; never regenerate.
- Cancel before dispatch prevents submission; after dispatch records local intent
  and prohibits adoption, without claiming remote cancellation/refund. Preserve
  enough task identity to reconcile and stop automatic generation.

Validate every returned download URL/redirect, block private/loopback/link-local
destinations for this public Atlas transport, bound time/bytes, stage files, then
probe/decode media with time/resource limits and atomically publish a managed
artifact. Validate actual container/codecs, playable video, duration, dimensions
and audio track; a successful JSON response or MIME header alone is insufficient.
Local authenticated serving must support seeking/range requests and project
isolation. Keep signed URLs private; they are not lasting delivery evidence.
Reuse reference/deletion guards; do not enable arbitrary external-file deletion.

Store measured duration separately from authored/requested duration. Expose
mismatches; do not silently trim dialogue, stretch video or rewrite the Shot.
In-app controls: play/pause, seek, mute/volume, status/errors and source lineage.
The adjoining-shot experiment needs simple ordered playback and final-frame hold,
not an editor. Non-playable codecs fail clearly; no unplanned transcoding stack.

## Delivery checkpoints and stopping rules

1. **One offline vertical slice.** Implement snapshot/admission, budget claim,
   Atlas lifecycle, ingestion and basic player together with a fake Atlas server.
   Demonstrate prepare → submit → poll → locally playable candidate; prove no
   duplicates/overrun on restart. No separate framework-only milestone.
2. **First real clip immediately next.** Authenticate safely, verify rate, select
   reviewed input, reserve 5 seconds, generate once, download and view/listen.
   Inspect exact words, speaker, language, lip sync, identity, action, anatomy,
   ambience and unwanted music. Capture execution versus creative result separately.
3. **Adjoining clip only after first is usable.** Another 5-second request with a
   complete short cue, or a deliberately silent beat if the story calls for it.
   Review both cuts at normal speed, muted and audio-only; test final hold,
   repeat/seek and refreshed/restarted local playback. Voice consistency requires
   audible speech in both; a silent second clip cannot establish it.
4. **Close and publish.** One independent scoped review, final proportional
   regression gates, source-bound receipt, main merge/push and exact CI result.

After a failed creative attempt, identify one concrete defect and review the
next frozen prompt before another request. No unattended generation loop. If a
targeted correction repeats the same failure class, stop and reassess rather than
spend the remaining allowance. Budget exhaustion, unresolved submission,
credential/rate ambiguity, or a new material tradeoff stops live work.

## Verification and acceptance

Focused tests: frozen lineage and historical-image compatibility; duplicate
click/worker races; exact 100-second boundary; failed/unknown retry accounting;
restart on each dispatch boundary; stale/cancelled results; cross-project and
archived admission; malformed responses; SSRF/redirects/oversize/truncated media;
audio absence; temporary URL expiry; retrieval-only retry; secret redaction;
duration discrepancy; immutable review and explicit candidate selection.

Real FastAPI/file-SQLite browser tests with a fake provider verify budget UI,
generation vs ingestion status, no unexpected network replays, player controls,
audible-track support and same-storage restart. Mock clips prove plumbing only.
On stable code: `uv run pytest -q`; frontend unit, typecheck, build/static
freshness, `npm --prefix frontend run test:e2e`; wheel build/installed smoke.
The browser job explicitly installs and version-checks portable `ffmpeg` and
`ffprobe`; runner images do not provide an implicit P2 media-decode contract.
Run focused checks during development; full gates once stable and when material
changes require them, not after every prompt trial.

P2 single-clip pass requires real downloaded playable audio/video, exact cue
review, no blocking visual defect, valid frozen lineage, and durable reopening.
The adjoining-clip exit separately requires no blocking recast, state/action
contradiction, repeated/cut dialogue or unacceptable sound discontinuity. If it
fails, report single-clip success and adjoining-shot failure, not P3 readiness.
Use attributed Codex review; actual listening must use available audio-capable
review tooling, not waveform/track presence alone. If unavailable, keep the audio
quality gate open and request only that specific review help. Never fabricate a
human review or auto-create Approval from a test receipt.

Publish a concise receipt with commit, contract/input/output hashes, attempt
states, requested seconds, observed durations, rate evidence, checks and review
limitations. Keep credentials, signed URLs and raw provider payloads out of Git;
retain a local review pack and safe supporting evidence for GitHub-only readers.
No repeat whole-project audit. Director remains attached to bounded Terra work;
no Flow or unattended agents. Token/cost telemetry absent from tools is reported
as unavailable, not estimated from call count.
