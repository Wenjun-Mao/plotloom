# 0198: Explicit delegated disposable-QA decisions

Status: accepted implementation decision, 2026-10-19

## Native material handoff and browser context amendment · 2026-10-22

Native automatic preparation previously always attributed atomic material
handoff to an unnamed creator. A granted agent UI click therefore could not
truthfully authorize native references/frames. A distinct `NativeMaterialQaScope`
now freezes the exact original run, full pre-handoff bundle and closure hashes,
ordered endorsed reference decisions and every displayed original asset/hash,
in addition to the board, frame/shot/profile and budget facts. Manual-image
grants retain their existing meaning; no optional wildcard fields or enrollment
API are introduced. Add a production fixture only after its native output exists.

The trusted original-runtime binder validates the complete bundle before binding
the immutable grant. Atomic whole-pack material handoff accepts typed QA and
retains a `pre-video.handoff.v4` receipt carrying the actor through approval,
source-endorsed/authored intent, reviewed keyframe and identity observations.
Every owner still checks current revisions and original-runtime command scope.
Source text ownership stays with the saved storyboard; QA attribution is separate
metadata, never a claimed authored change to that text. Historical/portable
readers validate the exact source grant, receipt, actor and reference/frame facts;
portable truth does not confer runtime write authority.

`GET /projects/{id}/qa-context` only discovers a verified original-runtime scope.
Its grant lookup is read-only. Each material/batch surface requires explicit
visible browser opt-in for that project; navigation resets opt-in. Server writes
independently recheck typed scope and grant. Missing/failed context cannot enable
a QA write, and native QA material handoff refuses an omitted actor instead of
falling back to unnamed creator confirmation. Browser text, URLs and project
titles grant nothing. Final AV QA records actual observations and evidence,
including an explicit listening limitation when only technical audio inspection
was possible. Scope creation is not media inspection or creative acceptance.

Focused native tests cover exact-bundle refusal, actor fallback, atomic identity
review, retained attribution and portable copies without runtime grants.

## Finished-example scope addition · 2026-10-22

The owner requested a few finished example projects in different styles, with
prospective unlimited ImageGen/H3 budgets and delegated QA. The new examples
cannot use the initial fixture's authority: project identity, board and imported
originals differ. Append three exact immutable source grants:
`finished-example-watercolor-20261022` (paper boat),
`finished-example-cinematic-20261022` (teacup), and
`finished-example-stylized3d-20261022` (lighthouse).

Each grant freezes its created project ID, revision-one storyboard hash and two
imported SH01/SH02 asset IDs with original SHA-256 hashes in `delegated_qa.SCOPES`.
The manager supplied these identities from actual project-creation and ImageGen
import receipts retained under `.local/finished-examples-20261022/`; bootstrap
files and image descriptions alone are not grant evidence. Each board contains
two three-second shots (six seconds total). All use the existing H3 quality-8
portrait 576×1024 profile,
native audio and `cover_center_crop`. Both aggregate caps are null under the
prospective policy; the finite outcome remains three completed example projects.
The initial `disposable-qa-20261019` grant stays byte-for-byte equivalent in fields,
including its two-submission/ten-second limits, despite its fixture's deletion.

Reuse the existing exact admission and runtime-incarnation grant owners; reject
a generic enrollment endpoint, public schema change or relaxed matching. Source
registration does not bind a runtime grant, dispatch work or establish inspection.
The manager owns activation, serial live execution, actual visual/native-audio
inspection and settlement. Decisions remain agent-operated QA, never the owner's
personal review. Copy/restore, UNKNOWN, currentness and provider guards remain
unchanged. Focused regressions pin the old grant and exercise new exact admission
and refusal of changed board, shot, asset, original hash and project identity.

## Prospective provider-budget policy amendment · 2026-10-19

The owner requests unlimited provider budgets by default unless he specifies a
finite cap. This applies prospectively within already-authorized development/test
work using Codex ImageGen and the owner's H3 gateway. It does not authorize new
providers, real-story changes or endless experimentation/retries. Use the
smallest useful test and retain a finite task outcome.

The source contract implements this preference with nullable aggregate limits
(see [ADR 0200](0200-optional-aggregate-provider-budgets.md)). New launch policies
and batch manifests freeze null for unlimited by default, or explicit finite
integer caps. Prospective source-owned QA scopes can independently leave either
aggregate cap null. A finite QA scope refuses a null or larger batch cap; an
uncapped scope still requires its exact project/material/profile/runtime grant.
No new live QA scope is added by this implementation. Existing finite grants and
their evidence must not be rewritten or silently widened; the completed initial two-submission/ten-second grant remains
historical and enforced as authored.

An unlimited aggregate budget does not remove exact project/material/provider
scope, runtime-incarnation grants, usage accounting, per-request duration/shape
contracts, concurrency limits, idempotency, pause/cancel controls or UNKNOWN and
unsettled-dispatch protection. Provider/account quotas remain external limits.
This source change does not bind a live grant, alter a ledger/provider setting,
dispatch work or change retained runtime data; activation is separate.

## Problem

The owner explicitly delegated disposable-QA material inspection, test acceptance
or rejection, native audiovisual review and clip selection. Existing storyboard,
material and batch confirmation paths attribute decisions to human creators.
Using those paths unchanged would misstate who inspected and approved the media.

## Decision

Agent decisions use typed `agent_operated_qa` attribution with a scope ID. A frozen
source-owned scope identifies the exact disposable project, storyboard hash,
shot/asset/original-hash pairs, existing H3 profile and cumulative submission and
requested-second limits. Labels, notes, reviewer strings and public APIs cannot
enroll projects. The initial scope is `disposable-qa-20261019`, project
`326a5137-1851-4b5c-8ab2-b600ec7bda23`, SH01/SH02, existing H3 quality-8 portrait
profile, `cover_center_crop`, at most two submissions and ten requested seconds.
Originals remain intact. Real stories, other providers, larger budgets, uncertain
dispatch clearing and GitHub CI are excluded.

The trusted operator binds this scope once inside the actual application runtime
to the verified original home, database device/inode and immutable scope hash.
Reuse the existing application-owned nonportable grant store under a reserved
`qa-scope:` key; there is no public enrollment API or project-schema migration.
Do not compare macOS host stat values with a Linux container's view. QA command
contexts and persistence owners require that runtime identity. Dispatch requires
both the scope grant and existing batch grant and rechecks cumulative project
claims before reservation and in the existing lifecycle transaction. Failed and
UNKNOWN claims still count; UNKNOWN and unsettled work block another submission.

Storyboard approval and video review rows encode QA attribution with a reserved
marker that cannot be supplied as a human reviewer. Intents, reviewed bindings,
English endorsement, AV receipts, selected segments and UI readback expose typed
QA attribution. Material and English/final actors must agree. Ordinary named and
unnamed human review remain distinct. Existing gates, dirty drafts, revision/hash
CAS, rejection, currentness, byte proof and atomic whole-pack selection remain.

Authorization never proves inspection. Authored material intent and compatibility
observations remain explicit; final QA confirmation additionally requires actual
visual/audio observations, evidence references and explicit clip, native-audio,
intent and window confirmations tied to the current review hash. Neither source
code nor a grant asserts that future outputs have been seen or heard.

Copies, snapshots and exports retain truthful QA facts. Portable evidence
admission validates logical scope and lineage without requiring a runtime grant;
copies/restores cannot silently acquire write or fresh-dispatch authority.

The optional attribution observer does not own ordinary retained-video shape or
currentness. Non-object ordinary snapshots and malformed ordinary metadata remain
available to the video reader as invalid diagnostic evidence; observing no QA
marker grants no authority. An explicit attribution key is validated even when
its value is null. Retained QA approval, batch-job and review links also identify
QA evidence, so deleting or corrupting its snapshot markers cannot turn it into
ordinary evidence. Genuine QA evidence still requires exact matching actors and
frozen scope; production dispatch and selection admission remain strict.

## Alternatives and guardrails

Reject invented human names, fabricated human handoffs, implicit QA from labels,
generic role/enrollment frameworks, extra project tables, downstream review
bypasses and per-batch-only budgets. Focused tests exercise closed defaults,
attribution, scope/currentness, runtime incarnation, cumulative caps, UNKNOWN,
rejection, AV receipts and portable readback. Provider-fake tests are contract
evidence; the manager owns the bounded live journey and actual media inspection.
