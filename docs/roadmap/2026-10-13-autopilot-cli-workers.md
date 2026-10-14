# Parallel CLI workers for pre-video autopilot

Status: owner-approved direction and conditional implementation, queued on
2026-10-13. Use Relay Brainstorm and Plan for this design, then Relay Direct
after the preceding Plotloom assignments finish. No pool implementation or
live executor change is part of this planning checkpoint.

The outcome is faster preparation through dependency-ready text and image
workers, including image work before all text is finished. Each worker uses
one isolated `codex exec` process for one immutable job. Plotloom remains the
owner of admission, scheduling, validation, adoption and final human handoff.

## Queue and start conditions

The manager starts this assignment after the current autopilot UX repair,
combined integration qualification and actual-path release checks have reached
their recorded technical closeout. Integrate the completed first-pass Python
speedup and its corrected receipt before taking the new source baseline.
Its still-open 85-percent stretch target is not an active predecessor.

### Current worker authority and checkpoint · 2026-10-14

The current allocation is the manager's **Approved isolated runtime repair**
subsection in the release checkout's same roadmap, recorded at `dab20f6f`.
It supersedes this branch's original queue timing. The owner approved the
follow-up and resumed `codex/autopilot-cli-workers` from source checkpoint
`7b30ad3d8afeacd9aade11385e8b6bd41b8542e3` as the sole source/check owner.
Manager-main files and the independently published Python changes remain
outside this worker's integration authority.

Retained `.local/exec-validator-sandbox-probes/20261014-07/` evidence proves
the copies-based environment and checked offline sync remained alias-free;
original-alias and synthetic sibling/runtime/auth reads were denied. Its
import control failed on the `src` parent and Branches did not execute.
Preserve that root, the paused canary and the unknown art attempt unchanged.

The approved repair is an explicitly provisioned checkout-owned environment,
strict dependency/runtime identity checks and a validated `src` parent read
for Python-backed plans only. Readiness and attempts cannot provision or repair
an environment. ADR 0169 records this owning contract and the host-owned
bytecode cache fence. Run narrow focused regressions and attend an independent
stable-candidate review, then one fresh provider-free native preflight of all
eleven trusted validator/render plans with preserved prelaunch pins and
negative controls. Import success alone is insufficient. Stop and diagnose any
unexplained native failure before changing or retrying the profile.

This allocation excludes generation, provider calls, pool work, full/hosted
gates, activation, merge, push and global settings. Return a reviewed committed
checkpoint and explicitly release the source/check window; the manager owns
subsequent Python work, integration and native-generation allocation.

The repair is committed at `e24cb80e`; the test-owned runtime fixture follow-up
is `7685a868` and changes no production qualification inputs. All eleven native
validate/render pairs and seven controls passed once (29 commands), with exact
prelaunch plans and unchanged output/input inventories. Independent source and
fixture reviews found no blockers; a fresh checkout without ignored runtime
setup passed 34 focused and 49 service checks. See the
[bounded verification receipt](../verification/2026-10-14-codex-exec-checked-python-runtime.md)
for qualified revisions, fingerprints and limits. This checkpoint returns the
source/check window to the manager; it does not release generation or activation.

Start only when the preceding source writer is idle, required reviews are
collected, and the manager has released the source and heavy-check windows.
Use a fresh isolated checkout of that released revision because the retained
installation can still serve valued stories. Do not treat elapsed time, an
old forwarded acknowledgment or a clean checkout as predecessor completion.
Pending owner creative review or explicitly separate hosted evidence does not
block isolated implementation once the manager records technical closeout.

The valued `失物招领的月亮` run keeps its frozen executor and original jobs.
Do not migrate it to CLI, restart it, resend anything, or change its checkout
while generation is active. Any activation is a later safe-idle operation for
future launches. The manager's existing heartbeat checks the queue without
dispatching the new assignment early or reporting unchanged state.

## Established feasibility and remaining proof

The local evaluation on `codex-cli 0.162.0-alpha.17.2` completed four distinct
sessions: structured text, built-in ImageGen, reference editing, and two image
workers with 13.762 seconds of actual tool-interval overlap. All processes
completed with verified outputs and no API fallback. The private
[evaluation receipt](/Users/wjmao/Documents/Codex/2026-10-13/plotloom-codex-exec-eval.yEOWsp/evaluation.json)
retains inputs, process receipts, native evidence and hashes.

This establishes transport feasibility, not full-story speed, strict reference
identity, production delivery, crash recovery or cancellation. Console JSON
omitted image-extension events in this tested CLI version. Successful exit or
a model's tool claim is therefore insufficient ImageGen evidence.
[Official non-interactive command guidance](https://learn.chatgpt.com/docs/developer-commands#codex-exec)
supports the scripted transport; observed local capability remains version-bound.

Persistent specialist chats are simpler to retain but constrain independent
work to their chat reservations. A CLI worker per job is the selected approach:
explicit process ownership and parallel capacity, with more durable supervisor
responsibility. App-server integration is deferred unless a concrete CLI
capability or evidence blocker makes it necessary.

## Scheduling dependencies

Keep the existing owner prerequisites rather than making every text stage
simultaneous. Cast follows accepted source, outline, section map and installed
source graph; Art follows current Cast; Script follows current Art and route
budgets; storyboard follows current Script. Intention, presentation and
installation retain their current binding and approval rules.

Cast-owned exploratory reference generation already requires no Story Bible,
Shot or Approval. Start those jobs after current Cast adoption while Art or
later text runs. Art references can start after current Art adoption while
Script or storyboard runs. Freeze the exact subject revision, content hash,
Brief style and inputs at admission.

Retain early character-reference candidates, then select their exact bytes
under the existing canonical authority after installation. Cast-owned and
Story-Bible-owned reference contexts have different hashes; do not weaken
identity admission or pretend an early selection already authorizes a shot.
First frames wait for current installation and their own visible characters'
current canonical references. Unrelated Art gallery requests need not block a
ready frame; Art images remain gallery material, not implied shot conditioning.

Multiple text workers run only genuinely independent frozen jobs, initially
including different projects. Do not split a whole-stage delivery or run
dependent stages concurrently merely to fill slots. Any proposed same-project
text overlap must first prove independent owner bindings and serialized adoption.

Early references change the old guarantee that complete inventory ceilings
are checked before any image exists. Preserve hard image/job ceilings through
atomic reservations and a small frozen early-reference allowance, initially
at most four image jobs per project. Reject known impossibility before early
dispatch. If the later complete inventory exceeds the frozen ceilings, stop
further dispatch and offer manual takeover with retained early results. An
incomplete pack cannot receive the final material handoff or video eligibility.
Reconcile already-reserved subject identities into the final inventory without
counting or dispatching them twice. Never skip required material, raise a
ceiling or silently regenerate. Disclose this bounded early-work consequence
at launch and in the decision record.

## Executor and ownership contract

Introduce a typed future-launch executor contract, not a fake specialist chat
ID. Distinguish the existing specialist-chat backend from `codex_exec`; freeze
the executable identity/version, supported capabilities, model/effort,
instructions/validator pins and finite execution limits. Existing manual
specialist workflows remain available. Do not alter their pinned skill bytes
or rewrite retained jobs, policies, receipts or artifact bindings.

Immutable jobs own project/run/operation identity and frozen package hashes.
Durable attempts own spawn intent, native session identity, process ownership,
terminal result and evidence. Record reservation and attempt before spawn;
run processes outside database transactions. Validate complete packages and
output bytes before currentness/CAS adoption in the existing owner transaction.

The native CLI runs on the Mac host, not inside the Linux workbench container.
Use the established host-bridge/composition boundary; do not add an unowned
web-request subprocess or expose arbitrary executable paths and command text.
Keep credentials in the existing CLI auth boundary, out of project state and
logs. Restrict each worker to its frozen inputs, pinned read-only validation
tools and assigned writable delivery area. Use a vetted tool/config profile;
disable API fallbacks, unrelated connector writes and nested job dispatch.

Persist a private, attempt-owned evidence stream. Parse supported typed events
and actual tool arguments; bind ImageGen completion, session/tool identity and
native output hash to the declared package output. Do not scan unrelated
sessions, use substring/regex detections as production proof, or infer missing
telemetry means success. An unsupported CLI/evidence version fails preflight
or remains unknown until a capability adapter is qualified.

Restart reconciles the original attempt. Missing acknowledgment, session,
transcript or PID does not permit another generation attempt. Unknown provider
outcomes keep their reservation until exact terminal settlement. Fence PID
reuse and owned descendants; permission denial is not proof of absence.
Pause prevents new scheduling while retaining legitimate late delivery.
Cancel/takeover revoke automatic adoption, preserve results and require
truthful process/remote-operation settlement. Killing the CLI cannot prove
that an already-started remote ImageGen operation never happened.

## Ordered delivery

1. Record the executor, job/attempt, budget and early-reference decisions in a
   concise ADR. Reconcile primary instructions, schemas, binders, validators,
   ordinary-open/recovery validation and installed package contracts before
   adding correction machinery. Inventory the precise stage dependencies.
2. Implement one durable CLI executor with the existing serial ordering.
   Prove immutable inputs, exact output inventory, typed provenance,
   duplicate refusal, publication/adoption crash boundaries and restart
   reconciliation with disposable data before adding concurrency.
3. Add a bounded fair pool with per-domain and installation-wide caps.
   Qualify one text plus one image worker first, then two image workers;
   enable two text slots after independent-text proof. Start with a maximum
   of four total processes, never an unbounded backlog. Reserve capacity and
   job/image budgets atomically; unrelated safe jobs may continue while an
   uncertain attempt retains its own reservation. Do not expire reservations
   through a timeout alone.
4. Admit early references and ready individual frames through the dependency
   scheduler. Separate provisional work discovery from the final complete
   inventory; complete bundle publication still covers every required subject
   and unique filmed shot across all routes exactly once.
5. Show concurrent domain activity, queued/running/validating/unknown states,
   real counts and executor provenance in the existing progress/review UI.
   Keep the visible indicator, saved-Brief authority, source-bound limitations,
   manual takeover and genuine human review. No fake percentage or ETA.
6. Review the stable candidate, perform the full local gate, disposable native
   actual-path proof and preservation checks, then integrate/publish under
   repository policy. Hosted CI remains a separately deliberate release gate,
   not an automatic queue-monitor action. Activate only future launches at a
   verified safe-idle checkpoint; do not rewrite the prior run to adopt CLI.

One source owner implements each bounded checkpoint. Independent read-only
reviews remain attended and their concrete findings are fixed before release.
Use Relay Direct and Relay Deliver with this manager's existing identity at
dispatch. Refresh the actual project/checkout IDs before creating the new
assignment; do not reuse the completed UX worker for this separate deliverable.

## Verification and acceptance

Use focused and reviewed module checks while developing; reserve full for
the stable combined candidate. Preserve every existing release gate and the
full-scale all-route material tests. Include duplicate starts/attempts, PID
reuse and orphan descendants; missing/foreign/partial evidence; omitted
ImageGen stdout events; wrong session/tool/output hashes; pin drift; racing
CAS adoption; out-of-order deliveries; budget exhaustion after early images;
Cast-to-Bible selection; required identity attachments; pause/cancel/takeover
and late results; closed folders; portable recovery; derivative lineage;
single final human handoff; and unchanged video denial.

Native proof must use real frozen Plotloom packages through the production
adapter, not replace provider calls with fixtures. Bound the proof to two small
disposable all-route packs, at most sixteen native images across the paired
serial/parallel comparison. Extend that allowance only after preserving a
concrete failure and explaining the necessary additional proof. Do not use
valued projects or another provider as test fixtures.

Measure queue, process setup, tool execution, validation/adoption and end-to-end
wall time with matched inputs/settings. Demonstrate both same-domain and
cross-domain overlap, including reference work before final text completion.
Report throughput, limits and costs only when retained records establish them.
Do not promise a multiplier from toy overlap or confuse this generation work
with the separate 85-percent Python verification target. Human visual/style
acceptance remains distinct from software and executor qualification.

Exclusions: voice casting, audio/video generation, optional tails, new providers,
automatic aesthetic regeneration, global Codex settings changes, removal of
manual specialist workflows, live run conversion and destructive valued-data
changes. Keep this roadmap as the single plan for the queued worker scope;
append its implementation evidence to the existing autopilot receipt.
