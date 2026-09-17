# Playable MVP milestones — Shuohao-first delivery

Revision 4 — **Approved direction and checkpoint roadmap**, 2026-09-17.
The user approved the architecture and requested this full roadmap. This is the
single current tracker; bounded implementation assignments remain director-owned.
[ADR 0057](../adr/0057-shuohao-first-creative-workflow.md) records the ownership
decision. [Revision 3 history](playable-mvp-milestones-r3-history.md) preserves
earlier scope and evidence, not the current assignment queue.

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

F0 is implemented as a candidate-only technical foundation; all remaining rows
below are **planned**, except bounded F4 feasibility noted above.
Characters/art/script may iterate together; ordering describes acceptance
dependencies, not a rigid waterfall. Each delivery updates this table.

| ID | Deliverable and reuse | Acceptance evidence / next exit | Replacement obligation |
| --- | --- | --- | --- |
| F0 — Foundation and handoff **(candidate boundary delivered; [receipt](../verification/2026-09-17-f0-shuohao-handoff-receipt.md); not full F0 acceptance)** | Pinned Shuohao; checkout-operated repo specialist; minimal project-local request/candidate transport | Fresh recursive checkout can resolve the pinned skill and return a traceable, validated outline candidate/report. Candidate readiness verifies the complete frozen package and rejects malformed/stale delivery before a future owner can install it; no user-home runtime dependency. Pin/license and five-stage field/gap map recorded. F0 has no review or canonical-install owner proof. | F1 must select and prove the user-operable review/install owner; old authoring entrypoints are identified but not yet retired; no parallel general orchestration framework. |
| F1 — Source + novel-outline **(F1A source/review handoff lifecycle correction in progress; F1B mapping and product acceptance pending)** | Three source routes; reviewed story direction, characters/assets inventory, sections, choices and endings | F1A persists declared synopsis/imported/existing-work source material and accepts/reopens a candidate-only upstream `outline.json` through the F0 exchange. Prepared external publication blocks project lifecycle/snapshot transitions until explicit cancellation; late cancelled delivery cannot alter canon. This correction follows the premature, incomplete `174b98b` push and is not F1 or F1B acceptance. F1 remains unaccepted: one fresh synopsis must still produce and be human-reviewed as a one-choice/two-ending outline, and F1B must map its sections/choices without creating a second graph. | Replace overlapping Brief/Bible/Graph proposal-writing logic only as the new path becomes usable; retain routing authority, not a second graph. |
| F2 — novel-characters | Shared character bible, motivation, appearance/voice direction, identity references; existing ImageGen handoff | Two distinct shots/poses retain approved identity reference; supplied reference can be retained; edits identify affected downstream work. Text direction is not proof of generated voice consistency. | Consolidate duplicated character prompts/forms with stage data and existing identity review. |
| F3 — novel-art | Shared locations/props, visual anchors and justified state/lighting variants | Referenced assets are inspectable and reused across sections; missing or changed reference is surfaced; setting/prop identity survives representative shots. No physical interpretation inferred solely from an ambiguous state label. | Replace duplicated asset-authoring rules; retain managed asset storage/selection. |
| F4 — novel-script | Source-faithful action/dialogue for every pilot section using upstream writing/check/report workflow | Whole pilot, not one ending: decision consequences, incoming context, timing, speakers and no repeated completed actions pass source-backed review. User edits/save/reopen and explicit revision work without silently replacing unrelated accepted sections. Applicable checks pass; inapplicable episode gates labeled. | Replace overlapping scene/beat authoring, not wrap every old field in a new layer. No custom plan-expand subsystem by default. |
| F5 — novel-storyboard | Script-derived shots, reference-image needs, timing, H3 production direction; reuse upstream reports/export | Every script section has ordered coverage; dialogue remains script-owned; reference images and prompts agree. Changes flag actual affected shots; rendered report supports review in Plotloom. Verify actual gateway capabilities, not assumptions from upstream prompt syntax. | Consolidate duplicate shot/prompt compilers; preserve review and candidate currentness. |
| F6 — Audiovisual qualification | Test native H3 dialogue, speaker attribution, cross-clip voice consistency and prompt effectiveness | Bounded representative dialogue/ambient clips through deployed gateway; actual visual/audio review with honest reviewer attribution. Decide native audio sufficiency versus separate TTS/post-production before substantial dialogue spend. | No speculative TTS/lip-sync stack; remove redundant prompt paths only after replacement proof. |
| F7 — Reviewed production | Existing ImageGen/H3 jobs, alternatives, regenerate/select/discard across the pilot | Human can compare and choose clips, regenerate a defect and discard unselected candidates safely; selections, source revisions and provenance survive reopen. Missing media and failures actionable. | Reuse current media backend/accounting; avoid duplicate queue or candidate store. |
| F8 — Integrated playable pilot | All pilot sections produced, explicit choices, two endings, restart | Genuine native playback of both paths, held choices/endings, refresh/close/reopen; no wrong-branch footage or missing selected media. Creative/audio acceptance distinct from automated checks. | Reuse current player; stitching/export optional, not another playback engine. |
| F9 — Reconvergence | Minimal source-owned reconciliation for compatible incoming histories | One fresh branching/join example preserves differing consequences or explicitly reconciles them. Incompatible histories remain separate or visibly blocked; no unexplained state reset. | Reuse graph; add only evidenced context/authoring needs, not a general symbolic story engine. |
| F10 — M2 independent creation/delivery | Fresh contrasting stories through source → five stages → production → playback | Creator completes supported stories using documented UI/specialist handoff without developer repair; all intended paths complete, revisions/recovery usable, delivery opened by intended viewer. Settle local/portable/hosted delivery scope here before claiming completion. | Retire all replaced authoring entrypoints/tests for retired contracts; retain tests for supported safety and product behavior. |

## Execution and acceptance

F0 is the next bounded implementation assignment, not an instruction to implement
all rows in one run. This roadmap-writing turn starts no implementation. Director
may dispatch successive settled slices without routine user confirmation, using
Terra and Relay serial source ownership. Each assignment states exact deliverable,
scope, reused components, checks, exclusions and stop condition.

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
