# Local QA storage review and routine cleanup

## Current status

Updated: 2026-11-06. Owner: main Plotloom coordinator, sole deletion owner.
The owner approved the reviewed `b72fd01d` plan with “Sounds good. Go.”
Execution is complete: **41.621 GiB of allocated artifacts removed**, W absent,
and D reduced to **652.496 MiB** of current inputs and bounded holds. All 4,329
retained entries and the live project/media/settings/guard/runtime/recovery
baseline are unchanged. Both current project contexts and all 15 playback
streams match before/after; historical schema errors remain unchanged. Routine
cleanup is adopted in ADR 0236 and the developer guide. Documentation checks and independent
closeout review passed; the assignment is complete. No provider operation, service
restart, scheduled automation, push or CI. The remaining holds are intentional
active dependencies with release events, not unfinished deletion work.

## Acceptance

| Claim | Required evidence | Fresh media | Status / evidence |
|---|---|---|---|
| Storage accounted for | Exact roots, no-follow inventory and allocated sizes | No | PASS: 42.26 GiB total at 2026-11-06 16:19 Toronto; see inventory |
| Necessary retention identified | Named current consumer and deletion consequence, with bounded release action | No | PASS: current consumers and narrow release conditions recorded below |
| Removal candidates reviewable | Explicit paths/exclusions and lifecycle prerequisites | No | PASS: complete W/D dispositions, measured first batch, independent review closed |
| Routine cleanup defined | Owner, trigger, default dispositions, exceptions and verification | No | Adopted: ADR 0236 and developer guide; no scheduler |
| Approved storage retired | Exact frozen leaves, absent targets, retained-byte and live-state comparison | No | PASS: 41.621 GiB removed; 4,329 retained entries unchanged; full baseline matches |

## Scope, authority and evidence

- `W`: `/Users/wjmao/projects/HU/plotloom/.local/retained-worktree-evidence`.
- `D`: `/Users/wjmao/plotloom-canaries/2026-11-01-last-projection-v2-media-diagnosis`.
- `G`: `/Users/wjmao/.codex/visualizations/2026/09/13/01a0983e-0e5f-7171-950e-011adaf53303/h3-reliability-goal`.

The user requested a cleanup review of W/D and a routine plan, then approved
its staged execution. Root owns this plan and the cleanup. Two GPT-6.1 Sol / Medium read-only reviewers
inspected W and D independently of the plan writer. Inspection used filesystem
metadata, existing receipts, tracked source, current mounted/runtime ownership,
read-only databases and current H3 task/package records. No fixture, model,
provider, service mutation, broad qualification, push or CI was run.

Apply the owner's [existing necessity rule](2026-10-25-top-five-cleanup.md#owners-preservation-rule):
keep only a named current function, owner-valued work or necessary recovery.
Uniqueness, sunk cost, old hashes, historical audit and possible future reuse are
not retention reasons. An obsolete runnable helper is not a current consumer.
Immutable evidence need not remain executable; disposal must not relabel a
failure, invent a remote outcome or clear a live reservation.

The smallest observed outcome is a concrete W disposal decision: its adopted
source is on main, current production/recovery lives elsewhere, and the old
qualification fixtures have no current exact-fixture consumer. No provider
proof or fresh media is needed for this decision.

## Reviewed inventory — historical baseline

| Root | Allocated KiB | Approx. GiB | Regular files / symlinks |
|---|---:|---:|---:|
| W | 5,371,040 | 5.122 | 122,217 / 686 |
| D | 38,939,920 | 37.136 | 53,063 / 144 |
| Total | 44,310,960 | 42.258 | 175,280 / 830 |

These are local allocated-file measurements, not a promise of reclaimed APFS
space. Symlinks were inventoried without traversal. D is dominated by NUT video
(about 12.18 GiB), tensor files (6.47 GiB), gzip bundles (5.29 GiB), raw RGB
(2.97 GiB) and PNGs (2.17 GiB). W contains copied tests/databases, environments,
images and closed execution state. File format alone does not decide deletion.

The earlier 208 KiB delivery directory and 201 MiB qualification area are outside
this batch. So are installed projects, Downloads V2/V3 games and media, G,
`.local/current-qualified-recovery`, `.local/worktree-consolidation-20261030`,
primary `.local/b37` and primary `.local/codex-exec`. W's nested directories with
similar names are distinct historical copies.

## W: entire root retired

| Relative path | Allocated KiB | Reason it can go |
|---|---:|---|
| `b30f/.local/b37` | 3,064,932 | Closed B3–B7 fixtures, copied project homes, validator environments and diagnostics; the named valued-copy directory is an isolated verification copy |
| `b30f/.local/project-language-20261028` | 1,653,628 | Closed bilingual QA installation, private supervisor, ASR model/environment and failed traces; no current exact-fixture consumer |
| `b30f/.local/codex-exec` | 132,116 | Old worktree Python environment |
| Remaining `b30f` | 46,868 | Superseded QA, caption, preflight and browser captures |
| `f4b3` | 472,740 | Parent-source copies, old native environment and fixture/log copies |
| `8f80` | 716 | Review manifests and obsolete helpers; 72 final file hashes and five deletions match adopted ancestor `708a56b8` |
| `validation-quality-boundaries` | 40 | Closed logs/checkpoint |

The [consolidation receipt](../verification/2026-10-31-worktree-consolidation.md)
explains the original move: preserve bytes while retiring worktrees. It did not
establish a permanent storage requirement. Separate consolidation source
snapshots and refs remain outside scope. Current source preserves the adopted
retry contract in [ADR 0225](../adr/0225-bounded-generation-retries-and-local-capacity.md).

The two bilingual QA homes hold six exact selected derivative hashes. Disposal
loses replay of that closed fixture and the raw proof, but not current user
projects, the supported bilingual feature or its tracked result/limitations.
Four old `inspection.evidenceRefs` in a current project already point to
October-25-retired files, not extant W files; they are bounded descriptive strings,
not file-read dependencies. Do not rewrite project persistence to clean them up.

The archived bilingual supervisor has two remote-unknown/reserved outcomes,
no slots/queue/validators, and no attempt/project/job identity overlap with the
installed ledger. Retire that isolated QA namespace and its obsolete helpers
as a unit after the lifecycle preflight; remote outcomes remain unknown. Do not
initialize it, resume jobs, import its rows, or manufacture settlement. The
installed ledger's two separate UNKNOWN reservations and five revocation guards
remain protected outside W. Counts are observations, not expected constants for
a later cleanup while other work may legitimately advance.

## D: current consumers prevent whole-root deletion

The H3 work is active. The owner now prefers native H3 while pursuing separate
speech in parallel. Old experimental failures do not retire either route.
Current v4 preparation still imports files and uses an environment under D;
thus a broad age-based or whole-root deletion would break active work.

A source/package check found no W/D reference in current tracked application,
script, frontend or test code. The installed bridge LaunchAgent has no W/D
reference. This does **not** cover external H3 development: v4's README explicitly
selects D's interpreter; `offline_rehearsal.py` reads its plate and START; the
calibration manifest reads its selected media/source. The active sparse-guide
review explicitly consumes D's pinned native layout files.

The initial inventory recorded 248 observed top-level entries, exact keep/hold
paths and the first batch. It is now retired after execution; the same
[path list](2026-11-06-local-qa-storage-paths.json) contains only remaining
current dependencies/holds and the concise result. The initial review below is
historical baseline evidence, not a new removal instruction. Its top-level
name list does not identify new nested children or authorize recursive erasure.
New or changed paths are outside the reviewed removal scope. Hashes are
observations, including for mutable active plans; refresh them at execution.
The parent corrected the first proposed keep set to also retain the review pages' linked START images, astronaut prompt, original media
paths and three corpus-summary links. Otherwise the seven playable examples
would have retained their videos while losing useful source links.

### What actually stays

| Exact group, relative to D | Current consumer / loss if removed | Release condition; owner |
|---|---|---|
| `h3-reliable-recipe-plan.md`, `standing-authority.md`, explicitly incorporated prior pilot plan | Active H3 scope, qualification and authority; removal loses the owning plan | H3 director explicitly supersedes/ends the scope, then retires unused text |
| `conditioning-audit/installed/comfy/ldm/minimax/model.py`, `comfy_extras/nodes_minimax_h3.py`, `comfy/text_encoders/minimax.py` under the same `installed` root | Pinned actual layout/guide/token semantics used in current sparse-guide/native preparation | Versioned worker freeze identifies and validates a maintained source location before retiring old copies |
| `latentsync-pilot-preparation/.venv`, `inputs/{START.png,plate.mp4,source.json}`, `inspection/sync-review.mp4`, root `latentsync-director-review.md` | Current v4 interpreter, offline rehearsal and source-bound calibration; deletion breaks execution or readback | H3 source owner rebinds to a supported environment/fixture and passes the affected provider-free rehearsal; no generation is needed |
| `tbdub-reusable-two-speaker-preparation/{README.md,adapter.py,contract.py,media_io.py,native_cpu.py,clock_contract.py}` | Active recipe's starting implementation/import closure | Source owner incorporates or stops using this implementation; old adjacent test runs are not included |
| Seven `native-positive-controls-review/media` clips, current pages/manifest/owner review and the exact source/START/original paths listed in the inventory | Owner-reviewed native controls used to formulate the preferred native route; current pages and frozen source bindings still name these paths | Retain while used as selected calibration/owner-valued examples. H3 director may retire duplicate originals only after actual consumers no longer need those paths; do not silently rewrite frozen evidence |
| `native-corpus-assessment/{REPORT.md,primary-takes.json}` and `native-corpus-director-review.md` | The working positive-control index links these source summaries | Retire with that consumer or update its current view deliberately; no need to keep the full old corpus |

At review these current dependencies occupied **0.303 GiB**. Execution also
retained the 3.684 MiB self-contained
`latentsync-pilot-preparation/director-review/index.html`: the current n10
calibration report links it. This preserves that working view without editing
its source report. It releases with that calibration consumer. Most is the one
working Python environment. Retention is functional, not a promise to keep
these historical directory layouts forever. No whole diagnosis root is needed.

### Temporary holds with specific end conditions

At review these selections added **0.330 GiB**. The fresh execution check added
seven files (40 KiB) under
`latentsync-pilot-preparation/gateway_candidate/src/plotloom_h3_gateway/`:
`__init__.py`, `contracts.py`, `profile_catalog.py`, `workflow.py`, `naming.py`,
`vae_policy.py` and `profiles/minimax_h3_template_v2.json`. Current v4
`native-proof/build_packet.py` imports/loads them. They release only after an
accepted proof and verified source rebind, or explicit retirement of that
workflow. No surrounding candidate/cache/deployment subtree is retained. The H3 director owns their disposition at the
next same-scene/source-method freeze, before approving another large diagnostic
archive. The main coordinator checks any unresolved exception at the next weekly
maintenance review. Do not renew a hold merely because its old script is runnable.

| Exact selection (inventory lists files) | Why hold now / what resolves it |
|---|---|
| Native START comparison: two MP4s, their actual graph/request/START files, comparison JSON and director/experiment reports | Current formulation uses the matched START counterexample. Same-scene authoring freeze selects any continuing calibration; release unselected case files then |
| `tbdub-crossed-face-audio-preparation/live-execution/review/media/{F1-A2,F2-A1}-comparison.mp4` and reports/index, plus `tbdub-crossed-director/RESULT-ASSESSMENT.md` | Fresh `lsof` found both exact clips open in QuickTime. Wait for natural close and the separate-speech brief's selection. Do not close the app, signal it or remove its current media. The old full HTML view is not retained if its other media are retired |
| Fruit-stall `REPORT.md`, `media/joint-candidate.mp4`, `media/source-picture-same-master.mp4` | Existing retained-example gate consumes the first two; matching source enables comparison. Release if the selected maintained route no longer uses this example; no current need for its ~930 MiB lossless traces/exports or ~56 MiB frame cache |
| N10 `tbdub-n10-independent-cpu-transfer/inputs/canonical-original-rgb.nut`; LatentSync geometry pair and exact `runs/dfa041239f74457ca19f682940ea36e4/source-faithful.nut` | Old N10 transfer reads these exact files. Keep only until the source-method freeze confirms whether that route is actually selected; runnable old code alone is not long-term necessity |
| Nine Student identity/source files listed in the inventory | Existing candidate manifests and boundary checks refer to them. Release if current method no longer selects Student; CPU captures and learned-woman comparison are not implicitly retained |
| `portrait-speech-first-development/plate.mp4` and `native` | Possible F3 transfer/lineage input. One old lineage input is already missing, so no claim of a viable complete old workflow. At method freeze, either identify the exact still-used subset or release it |
| Three quiet-tail envelope/index JSONs, roundtrip `installed-envelope.json`/`sources/main.py`, and `latentsync-reuse-preparation/{sync_adapter,REPORT.md}` | Exact source/envelope inputs of old weather/quiet-pose tooling. The next maintained-method selection either adopts them or releases them; it does not retain raw RGB, tensor dumps or the old postmortem |

### Reviewed D disposition — executed

The five largest study families total about **17.73 GiB**: Teacher selector,
closed-reference pair, F2 reframe, Teacher CPU preparation and crossed face/audio.
All are closed or superseded experiments. Retire them except the exact crossed
view files above, after normal preflight. Their names and allocation are frozen
in the path inventory. The two ~198 MiB closed-reference lossless pair files have
no selected current consumer; a completed negative study is not a preservation
case by itself.

| Other large family | Disposition |
|---|---|
| Full VAE roundtrip (~1.95 GiB), quiet-tail masked edit (~1.55 GiB) | Retire raw RGB, tensors, lossless decode copies, archives/postmortem; hold only named small envelope/source inputs |
| Teacher learned (~1.67 GiB), N10 learned review (~1.53 GiB), Fun2 GPU (~1.27 GiB), ROI bridge (~0.63 GiB), N10 startup repair (~0.56 GiB), LivePortrait C/L (~0.51 GiB), LivePortrait isolated (~0.45 GiB), N10 two-actor (~0.44 GiB), trained inpainting (~0.43 GiB) | Whole-family disposal candidates: no selected current consumer; prior technical/content failures remain failures in the useful decision summaries |
| Student runtime (~1.56 GiB), reusable two-speaker (~1.16 GiB), fruit joint review (~1.05 GiB), N10 CPU (~0.92 GiB), LatentSync pilot (~0.85 GiB) | Partial: retain only keep/hold entries; retire captured fixtures, repeated frames, copies, inactive environments and historical outputs |
| Remaining observed entries | Disposal candidates except the explicitly listed keep/hold files. Their exact observed names are in the inventory; this is not a wildcard authorization for new work or new files |

The historical diagnosis proposal left **0.634 GiB** of identified current/temporarily
held files and makes approximately **36.502 GiB** a disposal candidate. With W,
that is **41.625 GiB** of reviewed potential removal, inclusive of the first
batch below. This is a planning estimate. Active work, identity changes or newly
established current consumers must be checked before execution. The full
proposal should be staged; it is not a command to delete everything else now.

## First D batch — executed

The following nonoverlapping paths total **9,414,280 KiB / 8.978 GiB**. They are
closed synthetic proofs, reconstructible caches and unneeded transport bundles.
Their experiment reports record terminal/reap/release outcomes; the current
plan does not select those closed experiments for replay. No current caller was
found for these exact payloads. Current exceptions below and any newly created
consumer take precedence at execution preflight.

| Paths relative to D | Allocated KiB |
|---|---:|
| `closed-reference-paired-study/numerical-fake-proof`, `numerical-fake-proof-attempt1` through `numerical-fake-proof-attempt7`, and `role-proof` | 3,042,900 |
| `tbdub-teacher-asset-cpu-preparation/retained`, `retained-evidence.tar.gz`, `proof-candidate.tar.gz`, `first-stage.tar.gz` | 3,546,924 |
| `tbdub-f2-reframe-preparation/evidence/cpu-proof-r2-c243ca37125b`, `cpu-replacement-evidence.tar.gz`, `delivery-stage.tar.gz`, `preparation-packet.tar.gz` | 1,592,216 |
| `tbdub-teacher-selector-retained-review/.cache`, `.venv`, `teacher-original-F2-A2-portable-review.zip` | 739,556 |
| `tbdub-crossed-face-audio-preparation/preparation-packet.tar.gz`, `delivery-stage.tar.gz` | 492,684 |

Each basename after a directory prefix in a row belongs to that same prefix.
Combined with W, this initial disposal recommendation covers **14.100 GiB**.
It is a subset of the broader D disposition, not additional space to sum twice.
The tensor captures are synthetic validation outputs, not installed model
weights. A transport archive being old is insufficient alone: check that it is
not the sole required source of any retained member before unlinking it.

## Approved staged execution procedure

1. Before a later removal, bind the exact files or unchanged subtrees and
   exclusions to a fresh no-follow manifest at the authorized cleanup boundary,
   including leaf membership, identity and change indicators. The 248 top-level
   names and complement of the keep list are insufficient deletion authority.
   Recheck that manifest immediately before removal; defer any added/changed
   child or affected subtree instead of absorbing it into a recursive delete.
   Recheck current H3 work against the keep set; do not interrupt another task or the
   user's media player. New dependencies defer only their exact paths.
2. Capture the relevant live project/settings/media, supervisor guard and current
   recovery baseline. Observe state passively; do not bootstrap an old runtime
   merely to inspect it. Revalidate exact directory identity, no-follow boundaries,
   mounts, open files, worker ownership and unresolved native work. Use the
   existing ordinary deletion/abandonment contracts where a current project
   lifecycle owns a target; a filesystem erase is not a guard workaround.
3. Begin with one unreferenced closed fixture/bulk group and verify the live
   baseline remains intact. Then remove the remaining authorized candidates,
   excluding current dependencies. No relocation archive, backup collection or
   new replay tooling is needed. Do not follow symlinks into external runtimes.
4. Retire stale availability claims and obsolete commands in the owning docs
   while preserving pass/fail/UNKNOWN outcomes and useful contracts. Record
   removed roots/allocated size in this existing plan; keep historical immutable
   receipts unchanged where still retained. A dead narrative link is not a
   reason to retain gigabytes or edit canonical project data.
5. Verify target absence, retained-file identity, current playback/reopening,
   actual guard preservation and usable recovery. Report any legitimate
   concurrent state changes separately. Do not restart services or rerun full
   qualification for storage-only work. Report actual removed allocation and
   remaining narrowly justified exceptions; no guaranteed free-space claim.

## Routine cleanup — adopted 2026-11-06

| Trigger | Responsible owner | Required action |
|---|---|---|
| Before a run creates durable output | Producing task | Name working directory, current deliverable, disposable scratch and cleanup owner in its existing plan. Check existing inputs before copying them. |
| At every known-terminal task closeout | Producing task, coordinator verifies | Remove authorized task-owned scratch after result/readback and exact process closure. Classify each remaining artifact as current product/input, open-defect evidence, necessary recovery or disposal. Include failures in this closeout. |
| When a candidate is superseded or adopted | Source/execution owner | Release earlier synthetic captures, full-frame dumps, extracted archives, duplicate environments and derivative media with no remaining consumer. Keep the selected working/delivered copy and only required source bindings. |
| At the next weekly maintenance session | Repository coordinator | Review root sizes and every exception's named consumer/release event; resolve expired holds or propose a bounded cleanup batch. This is a manual procedure, not an installed schedule. |
| Before the next large experiment after interruption | Resuming task | Reconcile exact owned work, close obsolete scratch, then continue the authorized assignment. Do not turn an interrupted/UNKNOWN attempt into a retry or deletion permission. |

A retained item must state **path, current consumer, loss if removed, owner, and
release event** in the existing plan. A small file or old test pass is not an
exception by itself. Temporary holds expire for review at the named event; age
triggers review, never unconditional deletion. If a consumer still needs an
artifact, retain its dependency closure, not the entire neighboring experiment.

Prefer reading existing canonical media over making another local copy. When
an actual transfer needs an archive, remove the transport copy after the owned
extraction/readback and closeout if no consumer uses the archive. Capture full
raw frames/tensors only when the specific acceptance question needs them;
after the defect is resolved, retain its useful finding/regression contract and
release redundant payloads. Do not weaken an active diagnostic's evidence or
rewrite a frozen run to avoid its retention obligation mid-execution.

Keep disposable work in the task's existing scratch area and clean it at
closeout; do not create a new permanent evidence library. Keep one actual
current recovery package. User-valued media, installed projects and current
native safety state follow their own lifecycles. Project-owned creative handoff
packages may still be read for validation/import/reopening: do not apply a
standalone TTL to `delivery` subdirectories. Retire completed disposable QA
projects through their supported lifecycle and then their isolated envelope.

Within future assignments, ordinary authorized scratch cleanup belongs to the
same closeout, not repeated milestone approvals. This approved batch does not grant
blanket deletion outside its exact reviewed scope or of user assets. No new daemon, cron,
Codex automation, quota or generation ceiling is proposed for this first step.


## Planning review — historical

Independent GPT-6.1 Sol / Medium review reconciled all totals, all 50 keep paths,
43 holds and 22 first-batch paths; recorded hashes/sizes matched and selections
were disjoint. All eight positive-control HTML pages' local dependencies and
v4's current D dependencies are covered; v4's 14 additional dependency paths are
under G, outside cleanup. Parent verified local document links, JSON arithmetic,
path existence/confinement, disjoint selection and whitespace. Documentation-only
qualification: no product/full/browser suite was run or required.

The review's nested-child boundary finding is incorporated in execution step 1.
Two existing documentation issues are scoped for the owning closeout: v4
`SOURCE.md` points to a nonexistent `v3-media-diagnosis` authority path (the
actual v2-root plan is kept), and the retained LatentSync report links an older
review page proposed for retirement. The H3 owner should correct the former;
cleanup should mark the latter historical unless a current consumer is named.
Neither is a reason to keep a whole historical directory, and no concurrent
H3 source or report was edited by this review.

The planning review changed no W/D file, service or user media player. Execution
below supersedes that no-deletion status. The completed removal inventory has
been retired; only the concise result and current exception list remain.
The README entry is a narrow navigation edit to an existing long roadmap; no
unrelated document restructuring is warranted.


## Execution result and preservation

| Stage | Removed allocation | Result |
|---|---:|---|
| Small closed fixture (`W/validation-quality-boundaries`) | 40,960 bytes | Seven entries removed; all live preservation sections matched before scaling |
| W remainder plus 22 D bulk paths | 15,140,126,720 bytes | W absent; live state still exact |
| Remaining eligible D paths | 29,550,063,616 bytes | Every unprotected candidate absent; current dependencies and holds remain |
| Total | **44,690,231,296 bytes / 41.621 GiB** | 199,526 file/directory/symlink entries retired |

D now holds 684,191,744 allocated bytes / 652.496 MiB, 3,923 regular files and
three symlinks. This and the removed allocation reconcile exactly to the frozen
root inventory. Allocated bytes are not a measured APFS free-space gain.
No archive or relocation copy was made. The task's temporary inventories and
one-off operator are retired after independent closeout; they are not a product
cleanup tool or another standing evidence store.

Before deletion, exact no-follow membership/identity/change snapshots and an
open-handle check were taken. Only the kept active plan had changed since review.
No candidate had new mtime/ctime or new nested membership. The private operator
was independently checked: actual root descriptor identity, fresh parent-chain
checks, immediate leaf checks, no symlink traversal, refusal of optimized Python,
and empty-only directory removal. The same-UID cooperative/quiescent boundary
was used; no protection against a hostile simultaneous same-UID rename is
claimed. QuickTime and both open comparison clips remain untouched.

All 4,329 kept entry identities/content hashes match, including the added gateway
source and linked view. The seven native controls' working source/START/media
links remain available. Current application data, project data (20 logical
SQLite databases), installed host state, settings/credential hashes, runtime
source/container/bridge identities and all three current recovery members match
the pre-delete baseline. The installed two UNKNOWN reservations and five
revocation guards are unchanged. The retired isolated QA envelope's two remote
outcomes remain unknown; no replay, migration, settlement or reservation release
was performed. Consolidation source snapshots/refs, qualification campaigns,
primary working data and user deliveries were excluded.

The read-only HTTP status/digest records match before/after: health/catalog,
both current project contexts and all 15 selected playback streams return 200;
recorded successful content hashes are unchanged. Fourteen historical context
requests and two historical playback statuses remained 422. The unsupported-schema
message was inspected during preflight; failed response bodies were not compared
by the final harness. This pre-existing compatibility finding was not repaired
or reclassified by storage work.

Operational checks initially refused a system-Python `hashlib.file_digest`
lookup before manifest publication; the operator then used the existing locked
Python 3.12.13 envelope. A subsequent compile caught an indentation error before
deletion. The first-batch readback encountered a transient disappearing SQLite
SHM file; filtering already-excluded transient filenames before `lstat` corrected
the observer race, and the unchanged logical/file baseline then passed. These
were operator/observer issues, not bypassed product failures or weakened checks.

Historical worktree availability notices were updated without rewriting
canonical receipts, results or failed outcomes. ADR 0236 records the prospective
closeout procedure; it does not install a timer or broaden deletion authority.

Independent final review confirmed the exact live baseline comparison, HTTP
status/digest records, stage/journal accounting and all 101 retained path
selections. No retention or outcome blocker remained. Documentation-only
validation covered added links, JSON consistency and whitespace; no product
full/browser suite was required for this storage-only change.
