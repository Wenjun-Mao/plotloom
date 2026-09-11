# P1 image-workflow usability checkpoint

Status: Approved revision 1, 2026-09-11. User approved the director's bounded usability follow-up. Character-reference expansion is assessment/design only in this checkpoint.

## Outcome and baseline

Make the accepted manual image workflow understandable and loss-resistant, without weakening Approval, immutable briefs, delivery admission or explicit selection. Delivery baseline is `d23df0a8a96b6310fbe4f03b1735a665cc7d011b` on `codex/p1-image-jobs`, accepted locally; no main merge/push is authorized. Preserve that history. Use one new coordinator-owned worktree, advancing its clean initial branch to this baseline only after verifying ancestry, before admitting the fresh Flow run.

Review evidence: `/Users/wjmao/.codex/plotloom-p1-usability-review-20260911/review.md`. This private note uses retained-image simulation, not a new generation claim. Promote a concise self-contained findings record into tracked docs so future readers need no private path.

## Scope and decisions

1. Protect unsent image presentation/refinement directions across stage navigation and refresh. Define a session-only draft key including project, shot and original/refinement target, with revision/context validation, explicit discard and recovery. Never reuse another shot's direction silently, auto-submit, or change canonical facts. Integrate with existing draft patterns rather than inventing a global draft framework.
2. Make Copy assignment genuinely copy to the clipboard with accurate feedback. Provide selectable-text/manual-copy fallback when clipboard access fails or is unavailable (HTTP deployments remain supported). Export is not execution, delivery, approval or selection.
3. Treat absent delivery as understandable waiting guidance. Preserve immutable receipt history and fail-closed malformed/tampered delivery validation; distinguish ordinary absence from a broken package or invalid output.
4. Replace contradictory media-unavailable/P0 labels with capability-specific manual-image/video guidance. Explain disabled controls and give a clear next action through prerequisites, retain/intent/reviewed selection and preview. Do not collapse distinct approvals into implicit mutations.
5. Diagnose the newly saved example's missing Gate receipt; provide an explicit local Save and validate action if appropriate. Do not auto-approve or weaken gates.
6. Document the character-consistency gap: current textual canonical identity and parent-shot refinement versus future project-level approved identity references automatically frozen into every applicable original/refinement job. Separate stable identity from clothing/injury/state, composition and style. Record reference revision/staleness, multi-character identity mapping, user-supplied originals and visual cross-shot review as follow-up requirements. No identity embedding/face-recognition service, new generation schema or reference registry implementation here.

## Checkpoints and verification

- Establish baseline and short root-cause/ownership notes, implement the bounded UX changes and targeted regression tests.
- Real FastAPI/file-SQLite browser journey with retained image bytes: first saved example → explicit validation/Approval → prepare → actual copy/fallback → waiting refresh → simulated delivery → select → preview → reload. Cover direction preservation/discard, cross-project/shot/refinement isolation, stale draft context and tampered-delivery rejection. No new model or ImageGen calls required; label simulation honestly.
- Run focused tests during changes. On the stable candidate run full Python, frontend unit/typecheck/build/static freshness, E2E, wheel/install gates through existing tools. One bounded independent Terra review; reopen only specific findings. Retain 1440×900 evidence and a concise verification receipt; do not create a new harness.

## Authority and stopping conditions

One Terra High coordinator owns implementation, verification, integration and local commits. Optional one bounded read-only Terra reviewer. Admit complete required write scope up front: `frontend`, `src/plotloom`, `tests`, `docs/adr`, `docs/roadmap`, `docs/verification`, `docs/development.md`; include root config only if actually required and admitted before changes. Do not repeat historical fence omissions or rewrite frozen envelopes.

No V1, secrets, user-level AGENTS, real user data, existing pilot deletion, external API, automatic specialist bridge, video implementation, main merge or push. Do not amend prior accepted commits. Return one complete source-bound result with verification, limitations, local commit state, and character-consistency follow-up. A new schema/production contract or material scope choice requires director escalation. Stop after this usable workflow checkpoint, not after routine intermediate test reports. Usage/cost deltas only if already available.
