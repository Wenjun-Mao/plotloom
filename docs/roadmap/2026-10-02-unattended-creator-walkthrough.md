# Bounded unattended creator walkthrough

Status: approved and executing. The owner issued the final start command with
Relay direct and explicitly required its model-choice guide for every delegation.

Launch: 2026-10-02 01:34:18 America/Toronto / 05:34:18 UTC.
Stop new work: 09:04:18 Toronto / 13:04:18 UTC; reserve the final 30 minutes for
verification and handoff. Hard cutoff: 09:34:18 Toronto / 13:34:18 UTC.
Manager: `01a04525-e907-7630-9640-78790d69e8ae`.

## Goal and confirmed choices

Continue the creator journey while the owner is away, find and repair actual
functional/usability blockers, and leave a reproducible morning handoff. Run
for at most eight hours after approved launch; finish earlier if the scoped
journey and verification are complete. This is not eight hours of compulsory
generation or a promise that unsupported production capabilities will be built.

The owner explicitly chose a clearly labelled **test copy with provisional
content approvals and reference selections**. Keep the original 雨停以后
project's accepted content, media, selections and lifecycle unchanged. Test-copy
choices are agent-authored test decisions, never the owner's creative approval.
Code fixes may be delivered to the normal workbench after verification.

The owner subsequently removed the proposed submission caps and blanket
exclusions on live H3/video enablement, remote access, additional providers and
broad redesign. Those may be pursued when needed to complete the walkthrough.
This scope revision and execution are approved.

Current baseline: `370e46b` on clean `main`. Read-only preflight found:

- Source/outline r1, cast r2 and art r1 accepted; script and storyboard not started.
- S01/S02/P01 images have been delivered. The creator confirmed the S02 native
  chat-opening flow works; the additional-candidate form is deployed.
- Text/image specialist reservation state is idle. Verify again at launch.
- Persistent workbench: localhost:8841; Mac bridge: localhost:8842.
- The current server explicitly sets `video_provider=None, video_adapter=None`.
  Full real-video production/playback is therefore not a current runnable path.

## Operating boundaries

- Preserve the original project. Use the existing verified snapshot/restore
  workflow into a distinct installation root and separate local port. Do not
  raw-copy live SQLite or overwrite project identities. A snapshot may be created
  as test-copy source; it must not close or rewrite the original project.
- Before mutating the restored copy, prove path/identity confinement, including
  frozen package/delivery paths. Do not replay historical assignments. If safe
  copy isolation cannot be established, fall back to a fresh labelled test
  project through supported authoring APIs and disclose the prepopulated steps.
- Only test-copy approvals, reference choices, canonical installation, and
  reversible edits needed to exercise the journey are authorized by this plan.
  Do not backfill test choices into the original or change its Brief/shot policy
  to make a test pass.
- Use supported UI for the walkthrough. APIs may establish inspectable setup
  and verify state; record every setup/API-only step rather than calling it a
  creator UI success. Keep all disposable data and evidence workflow-local.
- There is no fixed text, ImageGen or H3 submission-count cap. Generate and
  iterate as needed within the eight-hour window, reusing valid retained assets
  where useful. Keep attempts purposeful and evidence-backed; no blind retry of
  an unknown queue outcome and no clearing its reservation to force progress.
- H3/video enablement and real submissions, private remote access, additional
  providers and broader architectural corrections are in scope when they serve
  the walkthrough. Prefer established integrations where they work; repair the
  underlying contract when needed rather than protecting a narrow patch budget.
  Unrelated speculative features remain outside the walkthrough's purpose.
- Use authorized accounts and credentials without exposing them. New purchases,
  subscriptions or billing commitments still require explicit approval; enabling
  a provider is not permission to bypass missing access or account controls.
  Remote access must remain private and access-controlled, not public exposure.
- Real and fixture outputs remain separately identified. Simulated playback is
  useful diagnostic evidence but cannot establish real-video completion.

## Ordered work and evidence

### 1. Establish isolation and the run boundary

Record an absolute eight-hour cutoff at launch in America/Toronto and UTC, the
source revision, original-project semantic/file baseline and owned local
resources. Verify Docker, native app, specialist availability, and no competing
source writer. Create the isolated test installation through the current recovery
contract and verify it cannot write the original project. Keep a stable test URL.

Acceptance: original baseline unchanged; test root/port and provisional-decision
labels recorded; no old handoff replay or duplicated native queue item.

### 2. Finish the image-reference review loop

Exercise delivered-image review, the new revised-requirements form, cancellation,
explicit new preparation/send, delivery inspection and comparison. Make any
reference choice only in the copy. Cover scene/prop scope and character-reference
prerequisites needed by downstream work without regenerating every asset.

Acceptance: old candidate/request/choice remains intact until explicit test-copy
replacement; a new job is distinct; no auto-send or auto-select; refresh/reload
is coherent. Continue iteration where it reveals or verifies a material issue;
there is no per-stage generation allocation.

### 3. Script and storyboard through normal review controls

Prepare, send once, inspect completion and read the complete script. Record
coherence/source-faithfulness problems separately from technical admission.
Provisionally accept only in the copy; then repeat for storyboard. Exercise
readability, section navigation, scoped editing and refresh/reopen behavior.
Preserve the one-choice/two-ending contract and existing timing/identity gates.

Acceptance: current, source-bound script and storyboard; all pilot sections are
inspectable; changes visibly invalidate affected downstream content; no hidden
editor/terminal action is required to cross a claimed UI milestone.

### 4. Production handoff, real media and playback

Walk storyboard → production proposal → explicit test-copy installation →
shot/Approval/reference/keyframe controls. Use supported manual author fields for provisional dramatic
intent if the existing model route is unavailable; label that action explicitly.
Inspect and enable the existing H3 backend in the isolated installation before
dependent live work: verify account/configuration, actual capabilities, request
contracts, dispatch safety and output ingestion. Its current disabled state is a
feasibility step to resolve, not an automatic stopping boundary. Generate the
needed keyframes and clips, inspect them, make provisional copy-only selections,
and exercise reading/playback across both ending routes. Additional integrations
or architectural changes may resolve demonstrated blockers; record durable
decisions and regression coverage rather than silently weakening admission.

Prioritize a complete smallest supported journey, with no fixed media-call cap.
Also test unavailable/missing-media and recovery states. Synthetic tests may
accelerate diagnosis, but report real-media completion only for paths actually
generated, ingested, selected and played. Investigate private Tailscale access
and implement it if needed for the intended viewing path; verify confinement,
authorization and that native chat opening remains on the execution host.

### 5. Repair encountered blockers in bounded serial slices

For each material failure: capture the exact UI/request/state evidence, identify
the root cause and correct layer, implement the smallest durable fix, add a
regression, then rerun the failed user action. Reassess after two unsuccessful
attempts at one criterion. Preserve failing evidence; do not weaken validation,
add special-case bypasses or repeatedly regenerate to avoid understanding it.

Larger refactors or redesign are allowed when the root cause requires them;
scope them to a verifiable checkpoint that can be handed off safely before the
cutoff. Prioritize data integrity, wrong/stale ownership, unusable transitions and
unclear failure/retry controls. Record optional polish and creative taste as
follow-ups instead of filling the night with extra features.

Use one source writer on retained `main`, independent read-only review on stable
candidates, and Relay completion reporting for delegated implementation. Follow
the model-choice guide recorded in `AGENTS.md`/ADR 0023 with explicit native
model/effort fields at dispatch. Do not change running chats or global defaults.
Only independently verified scoped changes are committed/pushed; check remote
divergence and preserve unrelated work. Refresh generated frontend assets.
Deploy only at an idle specialist checkpoint; do not change frozen execution
inputs under an active task. No global service restart.

### 6. Close out before the cutoff

Run proportional Python/frontend/type/browser checks and source/static asset
consistency checks. Compare the original-project baseline and inspect the normal
workbench health. Preserve the labelled test copy and useful evidence. Stop only
owned test processes when safe; leave the normal workbench available.

Provide one final report: milestones actually reached; fixes with revisions;
executed checks and review dispositions; real versus fixture generation; pending
CI; original-project preservation; unresolved blockers/creative decisions; stable
URL and exact next user action. Report usage only when available, not estimates
presented as measured cost.

## Continuation, stop rules and host dependency

After explicit execution approval, use Relay's completion events and a temporary
thread heartbeat to continue across idle gaps. The heartbeat has the same stored
cutoff and scope, stays quiet on unchanged/non-actionable state, and must not
start a second writer. Remove/disable it on completion or at the cutoff.
Do not create it during planning.

Reserve the final 30 minutes for verification/handoff rather than fresh expensive
generation. At cutoff, stop starting work; preserve and report any native job
already submitted rather than cancelling/retrying it blindly. Stop early when
the supported scoped journey is covered, or when all remaining progress needs
new authority, unavailable credentials or a genuine user choice. Provider
enablement by itself is now in scope, not a reason to stop. An
isolated blocker does not prevent other independent in-scope checks.

The Mac must stay powered, awake and logged in, with Codex and Docker available.
Do not alter system power/security settings automatically. If a permission prompt,
sign-in, unavailable service or host sleep prevents progress, preserve the
checkpoint and report it; do not bypass security or claim continuous execution.

## Entrypoints and existing checks

- `services/creator_workbench/`: current deployment/bridge; keep localhost:8841.
- `src/plotloom/video_backends/minimax_h3/`, existing video-job/media/player
  owners and the H3 prompt-writing playbook: validate before live enablement.
- `src/plotloom/project_storage/recovery.py`, `operator.py`, and
  `frontend/e2e/project-folder-snapshot-restore.spec.ts`: copy feasibility gate.
- `frontend/src/pages/ArtReferenceGallery.tsx`, `ArtReferencePreparation.tsx`,
  `ScriptPanel.tsx`, `StoryboardReviewPanel.tsx`, `ProductionBridgePanel.tsx`.
- `frontend/src/features/specialists/`, `media/`: handoff and media actions.
- `frontend/e2e/art-review.spec.ts`, `production-bridge-shot-handoff.spec.ts`,
  existing player/media tests and focused project-storage tests.
- ADRs 0074/0079/0082/0095–0097 and the active playable-MVP milestone record:
  dispatch safety, production ownership, timing, deployment and revision flow.

Execution approval was received at launch. Test-copy provisional decisions and
removal of the call caps/scope exclusions are settled; the eight-hour cutoff,
original-project protection and truthful evidence remain.

## Run log

- Launch baseline: `370e46b`; only this plan and its roadmap index were pending.
- First implementation owner: GPT-6.1 Sol / Medium, selected for integration
  ambiguity in recovery isolation and real creator/native/media transitions.
  Focused independent checks use GPT-6 Luna / Max; difficult architecture or
  persistent reasoning failures warrant GPT-6.1 Sol / High explicitly.
- Original project: `ee271b49-f384-414c-9711-452ee6333b84`; original workbench
  remains on port 8841. Copy root, URL and baseline evidence follow after the
  isolation gate; no copy mutation or handoff before that gate passes.
