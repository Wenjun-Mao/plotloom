# Retained Flow reconciliation before P0

> **Archive status (2026-09-18):** Completed record retained for its evidence; it is not an active delivery plan. See [the roadmap entrypoint](../../README.md).


Revision 2 — **Bounded metadata retirement complete**, 2026-09-11.
After the initial no-deletion guard stopped execution, the user separately
approved a verified byte-preserving backup outside repository/Flow roots and
the plugin-managed retirement of exactly `.git/codex-flow/v0.9.12` and
`.git/codex-flow/refresh-v1`. This supersedes only the earlier metadata-deletion
restriction. No discard/replacement of work, task archive, source/ref/worktree
deletion, manual journal editing, or broad unplug is authorized.

Before apply, inspect the prepared handoff for empty decisions, replacements
and cleanup, preserve the prepared record separately, and verify the backup.
Retain returned transition evidence separately because the original backup
cannot contain later retirement records. Shared `assignments-v1` and reporting
authority remain live and preserved; authenticated retirement annotations are
permitted, their deletion is not. Backups are recovery evidence, not authority
to restore an old namespace into live Flow state. Stop on any unexpected scope.

### Execution preflight finding

Before prepare/apply, inspection of stable v0.9.13 `finishCleanStartConsumption`
in `lib/compat/refresh.mjs` found that clean-start consumption removes the retired
`commonDir/codex-flow/v0.9.12` namespace and the handoff directory using recursive
removal after state/identity checks. This includes retired runtime/journal files,
not just a state flag. It does not imply source/worktree deletion, but exceeds
the explicit no-deletion guard. No prepare/apply or other Flow mutation ran.

The initial execution stopped pending maintainer confirmation of the required retirement
and separate user authorization if no non-deleting path exists. A prospective
expansion would preserve an exact backup outside the repository/Flow roots and
permit only the plugin's validated retirement of these exact metadata targets;
it would not authorize task archive, worktree/ref deletion, product reset or
manual journal editing. That expansion is now approved above after the maintainer
confirmed there is no non-deleting clean-start option in stable v0.9.13.

## Outcome

Resolve the exact predecessor lifecycle obligation through a supported,
separately authorized route, preserving all committed Plotloom work and evidence.
Then establish whether the already-approved P0 assignment can activate normally.
Do not confuse Git preservation, product verification and Flow acceptance.

## Observed baseline

Inspection used stable v0.9.13's `refresh inspect` once in the new P0 worktree;
the result explicitly reported `mutation_performed: false`. Old run/local-work
status was read through its pinned v0.9.12 runtime. No lifecycle mutation ran.

| Target | Exact identity / observed state |
|---|---|
| Primary | `/Users/wjmao/projects/HU/plotloom`, clean before this note, `codex/m1b-alpha`, `afb5583da56311337717b6569e21b33befbba4ab` |
| Predecessor run | `m1c-provider-readiness-offline-01a08e07`, namespace `v0.9.12`, active |
| Predecessor coordinator | `01a08e07-89c1-7953-a054-4594bd4da892`; App snapshot `notLoaded`, latest turn completed; not an archive/no-active lifecycle proof |
| Predecessor checkout | `/Users/wjmao/.codex/worktrees/754b/plotloom`, clean detached `96de4e36c2f4b41c6e758c21db1b452d1fcfc275` |
| Workflow / task | `m1c-provider-readiness-offline-candidate` / `offline-provider-readiness-candidate`, execution kind coordinator |
| Claimed operation | `coordinator-work-v1-c9603def159326f2f0244bbdaff9870df14874042e7ed49e4d649ff77ae02153` |
| Local-work result | **completed**, mutation final revision `564862b78508354a019a46f24158224f76dca731`; completed 2026-09-11T01:53:25.333Z; scoped verification PASS at that revision |
| New P0 task | `01a090e6-4c50-7240-8eb2-a6b81c13f24c`; reported stopped before activation or source mutation |
| New P0 checkout | `/Users/wjmao/.codex/worktrees/357b/plotloom`, registered detached at `afb5583`; preserve it |
| New preparation | `assignment-preparation-v2-d1cd4fcaaf9447abffbb8cddb756ecdd5f4a90e55024b11af5e183cb881c5432` |

The old assignment is
`coordinator-assignment-v1-6364c056a564bb06514d0babc15076377e8aa726c3fa5b63dbe35f1e583de24c`.
Its reporting recipient is this director task
`01a04525-e907-7630-9640-78790d69e8ae`; preserve its assignment/reporting authority.

Git ancestry checks passed: `564862b` → `96de4e3` → `afb5583`. The later
`ed8cf76`, `7a38f87`, `96de4e3` source-only corrections and subsequent planning
commits are retained in the primary branch. They must not be discarded or
retroactively presented as having passed the earlier immutable Flow contract.

## Classification clarification: no discard inferred

The target inspection reports `refresh-ready` and exports the coordinator task
with `embodied=false` and `completed_no_change=false`. These were initially
misinterpreted as unfinished refresh-managed work. Pinned local-work status and
the workflow journal both record a completed coordinator operation at `564862b`.

A targeted read of the pinned source exporter found that `sourceTaskState` in
`files/lib/compat/refresh-source.mjs` derives embodiment from reconciled
integration records and no-change completion from dispositions. That function
does not consume a coordinator-work result. Maintainer clarification and a local
read of v0.9.13 `normalizeDecisionRequest`/`requiredReplacementTasks` establish
that this is not, by itself, a defect: coordinator claims with `state=completed`
are excluded from required discard/replacement decisions independently of those
two fields. The completed claim's revision digest matches the current workflow
digest `99c0620cb29313eda700f69597476850f07fd712e3d96bc5977db4b8d8335d56`.

**Preferred route:** an authenticated no-replacement semantic handoff, subject
to confirming the exact exported `task_states` claim remains completed and all
baseline/authority checks pass. Do not require duplicate implementation or
discard any claim because of the abbreviated inspection flags. No handoff has
been prepared or applied; this is a proposal for separate authorization.

## Scope and non-goals

Only the named predecessor's status interpretation and lawful remaining
obligations are in scope. No broad repository unplug, `.git` editing, force Git
operations, source reset, manual worktree removal, credential/config change,
plugin-cache patch, server restart, generation, or full product retest.

Preserve `754b`, new P0 `357b`, unrelated `cd58`, all branches, assets and raw
reports. No task archive or physical cleanup is preauthorized by this plan.
This is not a replacement P0 implementation plan or another product rewrite.

## Proposed checkpoints and authorization boundaries

### R1 — Resolve the classification read-only

Maintainer guidance has clarified that the two flags are not generic completion
flags. Confirm the exact refresh task-state claim/current revision binding at
the authorized handoff boundary, and check there is no other unfinished managed
work. If projection disagrees with the pinned completed journal, stop for that
specific mismatch; no package correction is presently established as needed. Do not
manufacture an integration record, reset a claim or run `workflow local complete`
again to make the summary agree.

Exit: documented explanation and a supported route. If unresolved, remain
blocked with preserved evidence; no sequence of speculative refresh attempts.

### R2 — Approve the exact mutation proposal

After R1, present only the route justified by current evidence:

The requested initial authority should be limited to preparing and, if its
validated output has no replacements/discards/host deletions and unchanged
preserved source, applying the authenticated no-replacement handoff for this
one run. Use the owning runtime's documented no-replacement request grammar;
do not infer that an active predecessor permits the settled-predecessor shortcut.
Any additional requirement is a stop and a new proposal, not authority to widen
this action set. Preserve reporting through the supported transition. No task
archiving or checkout deletion is included.

- If completed work is correctly recognized, settle only remaining legitimate
  assignment/run obligations through their owning authenticated runtime. Preserve
  source-only verification as separate evidence; no fabricated retroactive pass.
- If a genuinely unfinished semantic obligation remains, identify it precisely
  and propose supported refresh/disposition/reissue. Explain what “discard” means
  for the lifecycle record and prove it cannot erase committed source. Preserve
  completed implementation in the target baseline; no automatic redo of it.
- If the plugin cannot represent the state safely, request a maintainer-owned
  correction or separately approved source-only P0 execution. Neither fallback
  follows automatically from this plan.

The proposal must name affected run/assignment/claim identities, allowed metadata
changes, preservation evidence and stop conditions. Any task archive, ref/worktree
deletion or new semantic task needs its own exact target and user authorization;
do not bundle cleanup into the generic word “reconciliation.”

Exit: user approves that concrete action set. Approval of planning alone is not
approval of an as-yet-unknown repair or broader retained-resource cleanup.

### R3 — One bounded execution after authorization

Recheck source/primary HEADs, cleanliness, ancestry and task activity at the
mutation boundary. Newly discovered work is a stop, not something to stash or
discard. Commit this approved plan first so its own draft file is not mistaken
for unrelated dirty source. Use only documented commands and typed host evidence;
preserve returned operation identity for any resume after an ambiguous result.

If a supported refresh is selected, inspect its exact prepared decisions before
apply. A coordinator-local claim has no child-worktree/branch cleanup authority.
No manual replacement for a refused host/lifecycle action. Stop on the first
unanticipated refusal and report the operation/evidence needed, not a retry loop.

Exit: authenticated result establishing the predecessor's actual disposition and
remaining obligations, plus unchanged source commit/tree preservation. “Command
returned” is not equivalent to settled lifecycle.

### R4 — Return to the primary product outcome

Recheck the new P0 task once and obtain an authenticated admission route. Resume
its existing approved preparation if supported; do not create duplicate
coordinators or silently treat a recovered old assignment as P0. If a new identity
is required, report why and perform the exact supported handoff only.

P0 revision 1 remains unchanged, including no live providers, bounded still
preview, verification paths and no release/push authority. A successful
reconciliation enables that outcome; it is not product progress by itself.
After this support checkpoint, start P0 rather than another infrastructure audit.

## Acceptance evidence

- The completed-versus-unembodied distinction is explained, not ignored.
- Exact `564862b`, `96de4e3` and `afb5583` source is preserved in durable refs;
  any later approved documentation commit is identified separately.
- No source-only result is relabelled as an old Flow-verified result.
- Only explicitly approved lifecycle identities change; retained checkouts,
  unrelated tasks and data remain untouched unless separately authorized.
- Old reporting/acceptance status and remaining obligations are explicit.
- P0 admission is confirmed by the owning runtime/task, or reported still blocked
  without duplicate dispatch. No false claim of implementation having started.

## Current handoff

Recovery completed through stable v0.9.13 at 2026-09-11T15:14:21.606Z.

- A private external backup of the complete pre-transition Flow tree was verified
  by file size/SHA-256 manifest and a second source comparison (264 entries,
  including directories). Location:
  `/Users/wjmao/plotloom-flow-backups/2026-09-11-handoff.xuiFqt`.
- The first prepare request incorrectly named the separate P0 coordinator as
  the refresh target. It failed before mutation: refresh must stay in the source
  coordinator task. Byte comparison confirmed no Flow change. The corrected
  request retained the source coordinator identity; P0 remains separate.
- Prepared handoff
  `refresh-v1-9d39010be81057526986069c9f708b56a2fc3ed6ed8e38f4d344f8e364d68c73`
  had empty decisions, replacements and cleanup. The prepared result is retained
  outside Flow along with both requests and process results.
- Apply returned `consumed-clean-start`, handoff state `consumed`, source terminal
  status `abandoned` by `snapshot-abandon`. This is lifecycle retirement, not a
  claim that source-only corrections passed the old immutable contract.
- The plugin removed only `v0.9.12` and `refresh-v1`. The pre-transition metadata
  is recoverable from the verified backup, but must not be restored as live Flow
  authority. `apply-result.json` preserves the later transition receipt separately.
- Before/after verification passed for all refs, worktree registrations, and
  HEAD/status of primary, `754b`, `357b` and `cd58`. No source, branch, checkout or
  task was deleted or archived. Primary was clean at `c46b8d6` during the operation.
- No shared records disappeared. The sole changed shared file was the old
  assignment record, with authenticated execution retirement retained. Reporting
  and P0 preparation remain present. A verified post-transition copy is retained.
- Fresh inspection from P0 checkout `357b` returned `route: fresh`, non-mutating.
  The existing P0 coordinator can now activate ordinary fresh work without a
  refresh ID; the approved P0 revision 1 preparation remains unchanged.

Next: resume the existing P0 coordinator for the imported still preview journey.
No product tests, live providers, merge or push ran in this support checkpoint.
Old assignment acceptance is not claimed by retirement. Usage/cost deltas are
unavailable.
