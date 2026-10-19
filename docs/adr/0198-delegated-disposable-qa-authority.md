# 0198: Explicit delegated disposable-QA decisions

Status: accepted implementation decision, 2026-10-19

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

## Alternatives and guardrails

Reject invented human names, fabricated human handoffs, implicit QA from labels,
generic role/enrollment frameworks, extra project tables, downstream review
bypasses and per-batch-only budgets. Focused tests exercise closed defaults,
attribution, scope/currentness, runtime incarnation, cumulative caps, UNKNOWN,
rejection, AV receipts and portable readback. Provider-fake tests are contract
evidence; the manager owns the bounded live journey and actual media inspection.
