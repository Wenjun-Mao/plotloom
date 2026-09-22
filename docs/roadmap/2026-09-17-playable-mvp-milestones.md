# Playable MVP milestones — Shuohao-first delivery

Revision 4 — **Approved direction and checkpoint roadmap**, 2026-09-17.
The user approved the architecture and requested this full roadmap. This is the
single current tracker; bounded implementation assignments remain director-owned.
[ADR 0057](../adr/0057-shuohao-first-creative-workflow.md) records the ownership
decision. [Revision 3 history](archive/superseded/2026-09-17-playable-mvp-milestones-r3-history.md) preserves
earlier scope and evidence, not the current assignment queue.

## Current review pause

The attended walkthrough has delivered bounded presentation slices: the U2
route-focused reader, the U3 Characters appearance workspace, and the F3B
environment/prop gallery plus explicit reference choice. Their technical and
bounded usability records live in the
[usability review plan](2026-09-18-creator-workflow-usability.md); none is
creative/media approval, a production consumer, or a whole-workflow redesign.

Current work is the documentation-only U0/U1 navigation and workflow
assessment recorded there. No provider or generation work is authorized by this
assessment. A later U1 implementation may only start from its bounded brief;
language policy, broader stage retirement, F5-to-production integration, and
H3 tuning remain open and are not decided by this tracker.

## Outcomes and starting point

**M1 is achieved:** the user tried one small playable branching film successfully.
Preserve its working Play view, selected media and attributed reviews.

**M2:** a user brings a synopsis or source story, reviews/refines proposals, and
finishes a coherent playable branching film without developer intervention.
Finished means complete intended routes with selected audiovisual assets and a
usable viewing experience, not flawless first-generation media or cinema quality.
Manual specialist handoff is acceptable initially; dependence on developer edits,
database intervention or hidden prompt surgery is not M2 completion.

Existing project storage, review, image specialist, video alternatives, H3 dispatch
and branching playback are foundations to reuse, not rebuild. Earlier proposal
and storyboard engineering checks remain evidence of those implementations.
Old 3B never achieved quality acceptance and is **superseded as a delivery path**.
Custom two-phase generation integration and further qualification-only work on
the old authoring pipeline are paused. No code is deleted by this plan.

Shuohao trials establish only bounded screenplay feasibility:
[corrected Terra trial](../verification/2026-09-17-shuohao-screenplay-reuse-trial.md)
and [Qwen API trial](../verification/2026-09-17-shuohao-qwen-api-adaptation-trial.md).
Only novel-script has been exercised on one short ending; the other four stages
and the complete workflow are unqualified. Qwen needed review-guided revisions;
profiles and formats differed. These are not controlled superiority comparisons.

## Agreed architecture

- One Terra-first repo specialist invokes five Shuohao-derived stage skills:
  outline, characters, art, script and storyboard. Tasks may be disposable; the
  versioned skill and files carry the workflow. No five-service architecture.
- Select and pin an upstream revision deliberately. The reference checkout at
  `/Users/wjmao/projects/HU/reference-repos/shuohao-skills` is research material,
  not a portable runtime dependency. F0 chooses a reproducible project-local
  dependency strategy with upstream license/NOTICE; no global skill installation.
- Plotloom owns projects, interactive routing, source/accepted revisions, review,
  assets, production and playback. Specialists propose creative content; they do
  not silently replace accepted material.
- Reuse upstream JSON as stage data where suitable. Markdown/HTML are derived
  reports, never parallel editable authorities. Reuse report presentation before
  rebuilding equivalent UI; isolate its scripts from the host and keep edits
  bound to authoritative data. Do not force all upstream data through obsolete
  Plotloom fields merely to keep the old implementation.
- Begin with a manual job-package handoff patterned on the image specialist.
  A skill requires an agent executor; it is not a server. Automation and other
  executors are deferred until the working path merits them.
- Qwen configuration is preserved but Qwen is not in the immediate authoring
  delivery path. No dual implementation or model benchmarking project.
- Job files live under the project's ignored `outputs/` storage, within their
  owning project/job home, with timestamped job folders where appropriate.
  No loose user-level generated files; no credentials in artifacts.

## Source and interactive structure

Support three source routes: synopsis → Terra-authored source story; externally
written story/treatment; existing work supplied for adaptation. Do not require a
full novel: a complete short treatment can suffice. Record source attribution,
usage rights/permission as supplied, adaptation intent and invented additions.
Never invent missing source text or claim legal clearance from a checkbox.

Use one shared story and character/art bibles, with a DAG of stable story-section
IDs. Choices connect sections; a viewer sees one route, not every optional section.
Display episode numbers where useful, but do not use sequence position as identity.
Write shared content once; do not duplicate every full route into an independent
episode. Each writing brief includes relevant prior events, incoming choice,
entity facts, intended consequence and ending/handoff.

The first integrated pilot is one small story, one decision and two distinct
endings, cinematic realism and pause-and-choose. Its scope/duration is frozen at
F1 before generation, not tuned after results. Reconvergence is deliberately later,
not abandoned. No new inventory/combat/state-dependent game engine is implied.
Episode-only hook/cliff requirements must be explicitly inapplicable for sections
that lack them, never fabricated or silently counted as passed.

## Checkpoints and live tracker

F0 through F5A now have bounded technical seams. The rows below distinguish
implemented lifecycle contracts from their still-required live specialist and
human creative evidence; no row is product acceptance merely because its
technical boundary exists.
Characters/art/script may iterate together; ordering describes acceptance
dependencies, not a rigid waterfall. Each delivery updates this table.

| ID | Deliverable and reuse | Acceptance evidence / next exit | Replacement obligation |
| --- | --- | --- | --- |
| F0 — Foundation and handoff **(candidate boundary delivered; [receipt](../verification/2026-09-17-f0-shuohao-handoff-receipt.md); not full F0 acceptance)** | Pinned Shuohao; checkout-operated repo specialist; minimal project-local request/candidate transport | Fresh recursive checkout can resolve the pinned skill and return a traceable, validated outline candidate/report. Candidate readiness verifies the complete frozen package and rejects malformed/stale delivery before a future owner can install it; no user-home runtime dependency. Pin/license and five-stage field/gap map recorded. F0 has no review or canonical-install owner proof. | F1 must select and prove the user-operable review/install owner; old authoring entrypoints are identified but not yet retired; no parallel general orchestration framework. |
| F1 — Source + novel-outline **(F1A lifecycle and F1B source-bound mapping/canonical-route admission delivered; creative/product acceptance pending)** | Three source routes; reviewed story direction, characters/assets inventory, sections, choices and endings | F1A persists declared synopsis/imported/existing-work source material and accepts/reopens a candidate-only upstream `outline.json` through the F0 exchange. Prepared external publication blocks project lifecycle/snapshot transitions until explicit cancellation; late cancelled delivery cannot alter canon. F1B adds an author-reviewed, source/outline revision-and-hash-bound map with exactly one entry/choice and two labelled consequence/ending links. It saves/reloads/reopens independently of Bible generation, then explicitly and atomically installs only its current three authored IDs into the existing graph routing owner. Source, accepted-outline, or map changes visibly stale only that admitted graph and actual consumers; unrelated graph ownership is not overwritten. This is technical proof, not invented human creative approval; F1 remains unaccepted until a fresh synopsis is genuinely human-reviewed as a one-choice/two-ending story. | Replace overlapping Brief/Bible/Graph proposal-writing logic only as the new path becomes usable; retain routing authority, not a second graph. |
| F2 — novel-characters **(F2A source-bound cast review and F2B attended two-study technical proof delivered; [F2A receipt](../verification/2026-09-18-f2a-cast-review-receipt.md), [F2B receipt](../verification/2026-09-18-f2b-cast-identity-proof.md); not human creative, F5 cross-shot, or F7 voice acceptance)** | Shared character bible, motivation, appearance/voice direction, identity references; existing ImageGen handoff | F2A prepares, refreshes, inspects and explicitly accepts one upstream `cast.json` bound to accepted source/outline/F1B sections, preserving a thin explicit consumer-ID seam. F2B freezes that accepted cast revision/hash and appearance direction through existing identity-reference/proposal currentness, with no duplicate media authority and no Story Bible/Shot/Approval prerequisite. In the disposable F2A project, a live original and a reference-byte-conditioned refinement were generated, inspected, explicitly selected, independently visually reviewed, and persisted through reload and close/reopen. Text direction and this two-study evidence are not proof of generated voice consistency. | F3 is the next creative-stage seam. F5/F7 production cross-shot and voice proof remain separate. |
| F3 — novel-art **(F3A text-first candidate/review path corrected for format admission, lifecycle recovery, upstream validation, reloadable frozen handoff, and committed production-browser regression at `bfc2b57`; [F3A receipt](../verification/2026-09-18-f3a-art-review-receipt.md). F3B attended two-study technical proof delivered; [original receipt](../verification/2026-09-18-f3b-art-reference-proof.md), with complete upstream-currentness, project-epoch, and unmount callback-ownership correction tracked separately in its [correction receipt](../verification/2026-09-18-f3b-currentness-correction.md); not human creative, F5 cross-shot, or production acceptance.)** | Shared locations/props, visual anchors and justified state/lighting variants | F3A freezes source/outline/map/graph/cast inputs, validates with the pinned upstream `novel-art` validator, and adds only a thin exact section-ID projection. Format-8 folders fail explicitly before open; fresh format-9 folders preserve stable scene/prop IDs and section usage through accept/reopen/save/restart. Prepared art blocks close/archive/delete/snapshot and recovery; cancellation remains user reachable and rejects late installation. Reload re-copies the same frozen assignment; current accepted JSON is inspectable without reopening, while reopening controls edits. F3B proves inspectable reusable environment/prop managed-reference candidates through the canonical art current-subject admission and current package/provenance owners, visibly labels missing/changed currentness, and does not infer physical meaning from ambiguous state labels. | Replace duplicated asset-authoring rules; retain managed asset storage/selection. |
| F4 — novel-script **(current-contract three-section technical proof delivered; first missing-binding candidate preserved/rejected; [receipt](../verification/2026-09-18-f4-novel-script-receipt.md); not human creative or product acceptance)** | Source-faithful action/dialogue for every pilot section using upstream writing/check/report workflow | One current Terra/high delivery bound exact `opening → 1`, `beacon → 2`, `dock → 3`, with source facts and two decision consequences intact. The headed production-browser proof re-copies/refreshes the frozen package, technically accepts it, reloads read-only JSON/original report, saves an opening-only edit while byte-preserving the two ending sections, and survives backend restart. Pinned validator/render and applicable section/route caps pass; hook/cliff and aggregate mutually-exclusive-ending duration stay explicitly product-inapplicable. | Replace overlapping scene/beat authoring, not wrap every old field in a new layer. No custom plan-expand subsystem by default. |
| F5 — novel-storyboard **(fresh F5A specialist delivery through production technical review delivered; [fresh receipt](../verification/2026-09-18-f5a-fresh-specialist-production-review-receipt.md), [lifecycle receipt](../verification/2026-09-18-f5a-source-bound-storyboard-review-receipt.md). The preserved content-split candidate remains historical evidence in its [production-seam receipt](../verification/2026-09-18-f5-storyboard-production-seam-receipt.md), not the fresh delivery, human creative approval, or product acceptance.)** | Script-derived review direction and reports; reuse upstream validation/render and the F0 handoff | F5A freezes the current accepted F4 script revision/hash, complete transitive binding, section/episode order, F4 section/route caps, and review-only 2–8s cut / 15s segment policy; it persists only raw upstream JSON/report as a review revision and visibly stales it with its source. A fresh package was re-copied, validated, refreshed, inspected, explicitly accepted, and preserved through backend restart and normal close/reopen. Independent content review passed. Attended native visual/creative review remains required because the Mac was locked; no creative approval is implied. Candidate `maxCutSeconds` is configurable upstream only within the frozen F5A review policy; production H3 remains fixed5 until separately qualified. No V2 SceneBeats projection, source-to-shot installation, media dispatch, or selected reference is a prerequisite or outcome of review-only evidence. | Replace overlapping scene/beat authoring only when a separately accepted product owner exists; retain this review/currentness seam and do not add a duplicate shot/prompt compiler. |
| F6 — Audiovisual qualification **([readiness receipt](../verification/2026-09-18-f6-h3-audiovisual-readiness.md), [offline 5/8-second contract receipt](../verification/2026-09-18-f6-h3-eight-second-offline-contract.md), [first live non-qualifying receipt](../verification/2026-09-18-f6-h3-first-clip-live-receipt.md), [offline corrective prompt proof](../verification/2026-09-18-f6-dialogue-prompt-offline-proof.md), and [corrected final-budget live receipt](../verification/2026-09-18-f6-h3-corrected-dialogue-clip-receipt.md); not audiovisual or production acceptance)** | Test native H3 dialogue, speaker attribution, cross-clip voice consistency and prompt effectiveness | Plotloom admits explicit 5- and 8-second H3 I2V contracts. Two and only two F6 live submissions are retained, both unselected. The first objectively ingested 8-second H.264/AAC clip is non-qualifying because its fixture froze a generic prompt. The final-budget corrected job froze and independently reviewed one C01/Lin Che `我在这里。` cue, quiet-room/no-narration/no-music direction, reviewed aspect, profile, and 8-second/192-frame/24-fps request; its output objectively ingested at 8.000 seconds, 192 frames, 24 fps, `576×1024`, H.264/AAC. Subsequent human review rejected the corrected clip: an unintelligible character-spoken utterance under one second around 4s precedes the recognizable intended line; unwanted burned-in subtitles show the intended line during both utterances. Audiovisual qualification failed; objective delivery remains valid. The cause is unproven. Voice consistency remains unqualified because the first clip has the wrong prompt. | No speculative TTS/lip-sync stack; no pad/trim/stitch workaround, duplicate queue, F5-to-media compiler, retry, or third submission. Keep F5/F7 production-reference and mapping choices explicit. |

| F7 — Reviewed production | Existing ImageGen/H3 jobs, alternatives, regenerate/select/discard across the pilot | Human can compare and choose clips, regenerate a defect and discard unselected candidates safely; selections, source revisions and provenance survive reopen. Missing media and failures actionable. | Reuse current media backend/accounting; avoid duplicate queue or candidate store. |
| F8 — Integrated playable pilot | All pilot sections produced, explicit choices, two endings, restart | Genuine native playback of both paths, held choices/endings, refresh/close/reopen; no wrong-branch footage or missing selected media. Creative/audio acceptance distinct from automated checks. | Reuse current player; stitching/export optional, not another playback engine. |
| F9 — Reconvergence | Minimal source-owned reconciliation for compatible incoming histories | One fresh branching/join example preserves differing consequences or explicitly reconciles them. Incompatible histories remain separate or visibly blocked; no unexplained state reset. | Reuse graph; add only evidenced context/authoring needs, not a general symbolic story engine. |
| F10 — M2 independent creation/delivery | Fresh contrasting stories through source → five stages → production → playback | Creator completes supported stories using documented UI/specialist handoff without developer repair; all intended paths complete, revisions/recovery usable, delivery opened by intended viewer. Settle local/portable/hosted delivery scope here before claiming completion. | Retire all replaced authoring entrypoints/tests for retired contracts; retain tests for supported safety and product behavior. |

### Deferred F6 prompt optimization — agreed separation

- **Evidence:** retain both F6 clips unselected. The user's review rejects the corrected clip for extra speech and unwanted repeated subtitles; do not reinterpret it as a transport failure or accepted native dialogue.
- **Prompt alignment:** before another bounded experiment, inspect and pin MiniMax's [H3 prompt skill](https://github.com/MiniMax-AI/MiniMax-H3/tree/main/.agents/skills/h3-prompt-writing), especially its [base guide](https://github.com/MiniMax-AI/MiniMax-H3/blob/main/.agents/skills/h3-prompt-writing/references/base-en.txt), against the deployed model/input mode and pinned Shuohao `skills/novel-storyboard/references/h3-prompt.md`. The source leads come from the user's “H3提示词官方指导” conversation; its summary is not verified primary-source guidance. Shuohao's local skill explicitly documents H3 alignment, dialogue blocks, soundscape and music fields. Prefer reuse over a second prompt framework; do not assume its multi-picture structure maps directly to current single-image dispatch.
- **Experiment:** design a small controlled comparison only after that source review. Candidate questions include a single speech instruction, exactly-once delivery, and suppression of additional speech/subtitles/on-screen text. Our action and dialogue fields both repeat the line; causal significance is a hypothesis, not a finding. No new generations are authorized by this roadmap edit; the original two-submit experiment is exhausted.
- **Product review:** keep regenerate/compare/select/discard in F7's existing candidate workflow; prompt improvement does not remove human acceptance.
- **Fallback decision:** if bounded evidence shows native speech remains unsuitable, separately assess controlled audio. Do not build a speculative TTS/lip-sync stack or redesign the text pipeline now. Cross-clip voice consistency remains an independent unmet gate.

## Execution and acceptance

The completed F5A integration closeout preserves baseline `bf4cc11` and tests
`ba271a6b3a9267dff4d103943339d8cbcddb82e9` in a fresh recursive local clone:
18 focused production FastAPI/file-SQLite browser cases, 627 locked Python tests,
162 frontend units, both typechecks, reproducible static build and fresh installed
wheel smoke pass. [Receipt](../verification/2026-09-18-f5a-source-bound-storyboard-review-receipt.md)
and [independent Terra/high delta review](../verification/2026-09-18-f5a-integration-delta-review.md)
retain actual checks, demonstrated fixes, failures and the main-worktree hygiene
discrepancy. Deliverable: current-package deterministic end-to-end review proof,
only demonstrated contract/UI/snapshot/gate defects repaired. Exclusions: fresh
specialist/creative approval, live generation, providers/H3, upstream changes,
legacy projection, retained databases, compatibility, CI/AGENTS and directory
cleanup. Stop condition: commit on main without push, stop owned services and
collect actual Relay source release. Technical proof does not accept F5 content
creatively or qualify production media.

The fresh live F5A specialist technical delivery is now complete. The next
bounded F5 action is an attended native visual/creative review of that accepted
review evidence; it is not implementation of the remaining rows or a provider
experiment. Director may dispatch successive settled slices without routine user
confirmation, using Terra and Relay serial source ownership. Each assignment
states exact deliverable, scope, reused components, checks, exclusions and stop
condition.

Before implementation of each slice, identify model-, author- and code-owned fields.
Use existing tools/contracts first. Changes to ownership need concise ADR updates.
Do not demand backwards compatibility for retired development formats; preserve
valued projects/assets and current integrity safeguards. Resets are scoped to
identified disposable data, not blanket cleanup authorization.

GitHub CI is a deliberate manual-trigger check, not an automatic acceptance
blocker for every push. Run it when its evidence is needed; retain the workflow's
jobs and `workflow_dispatch` entrypoint rather than adding a separate CI path.

Verify progressively: focused tests while editing; relevant production UI/runtime
journey and independent source-backed review on a stable candidate; broader
Python/frontend/build/wheel gates proportional to executable changes. Docs-only
work needs links/consistency/diff checks, not full runtime suites. Never count
unrun/inapplicable gates as passed. Capture latency/tokens if available without
inventing cost metrics. After two failures at one criterion, reassess rather than
repeat a broad task or add more machinery.

Every checkpoint records implementation, tests and creative/product acceptance
separately, plus replaced/deleted paths (or a concrete reason retirement is not
yet safe). Director reviews and pushes verified scoped work after checking remote
divergence. No force push, active-writer ref mutation or concealed failing gates.

Escalate only material changes: new paid services, changed rights assumptions,
destruction of valued work, source authority ambiguity, altered acceptance or
product scope. Native Codex ImageGen and owned H3 development calls are authorized;
that is not automatic audiovisual Approval. Model/provider choice changes and new
audio services must follow the settled scope, not be silently introduced.

## Named open decisions

- **F0:** exact upstream revision and smallest reproducible dependency/adaptation
  method; source/export schema mapping and safe report embedding.
- **F1/F9:** section-versus-episode rules and explicit join context. Do not force
  episode pacing rules onto endpoints or promise all DAGs before qualification.
- **F6:** measured deployed H3 voice/dialogue capability, whether separate audio is
  necessary, and resulting production tradeoffs.
- **F10:** supported story envelope and distribution/hosting boundary; manual
  specialist operation must be documented and user-operable if retained.

These are checkpoint-owned investigations, not reasons to delay F0, and not
authorization for generalized frameworks.
