# 0163 — Autopilot inherits the saved Brief visual direction

Status: accepted for implementation, 2026-10-12. Extends the
[pre-video autopilot](0162-pre-video-autopilot-authority.md) launch contract.

## Problem

Autopilot currently asks for one of three image presets and freezes it into
Cast and Art requests. Those independent presets can contradict the saved
Brief's arbitrary visual selections and free text. The existing manual
adapters are content-hash inputs to frozen contracts and candidate currentness;
changing them would invalidate retained evidence and frozen execution pins.

## Decision

New autopilot launches use an explicit server-owned `brief` style authority.
The saved Brief's complete `visual_direction` is the authoritative direction
for Cast, Art, references and shot frames. Empty direction is frozen as an
explicit instruction to use specialist discretion informed by the story, with
no injected photographic or preset style. The frozen policy binds the Brief
revision/content and style authority. Structural/source/language validators
remain authoritative; style identity and direction can be mechanically
checked, while semantic or visual fidelity remains a human judgment.

Keep the existing three manual presets and their adapter hashes unchanged.
Brief-mode contracts and validators must have distinct identities and must
not reinterpret or rewrite old policies, candidates, receipts or artifacts.
When decoding retained v1/v2 policy rows, an omitted style-authority member
stays omitted on serialization so their canonical hashes remain stable; the
runtime interprets that omission as the historical preset authority.

The v3 launch changes style authority while retaining the v2 geometry recipe
and runtime contract. Image-lineage assertions therefore accept geometry
evidence bound to either v2 or v3, while still checking the full policy hash,
recipe and runtime identity. Retained v2 policy bytes and hashes are not
rewritten.

## Consequences

Launch no longer exposes an unrelated preset selector. Policy and downstream
requests must carry an unambiguous mode and exact saved direction. Cast and Art
must share the same Brief authority, and image proposals must receive that
frozen direction exactly once without contradictory preset text. Tests cover
arbitrary selections/free text, empty direction, old-policy preservation,
manual presets, v2/v3 geometry lineage and inherited references/frames. This
decision authorizes no live run mutation or activation.

## Saved-Brief specialist instructions

The installed novel-characters and novel-art skills contain mandatory preset
selection and preset-specific validator/render entrypoints. Those instructions
conflict with `saved_brief`, even when the request's authority opener says the
Brief owns visual direction. New saved-Brief Cast and Art requests therefore
carry the named `plotloom.autopilot.saved-brief-receiving-contract.v2` override
from the Brief style contract owner. It explicitly supersedes only preset
selection/defaults, preset bundles and matching, style-specific negative-word
rules, and preset-specific commands. Upstream stage guidance and unrelated
structure, source/evidence, language, reporting, and quality requirements
remain in force. The instructions resolve task package and delivery roots and
give the exact repository-root validate/render commands for the Brief
adapters. Manual preset requests keep their existing instructions and
adapters. New saved-Brief contracts name the receiving-contract version and
hash this instruction owner; existing requests, policy hashes and specialist
pins are never rewritten. Installed skill bytes and hashes remain unchanged.

Before release, a review of the first instruction draft found that its Cast
Markdown command created an unsupported extra delivery file and its shared
ownership sentence prohibited editing the assigned Cast candidate. The v2
contract removes the extra output command and states input/output ownership
per stage: Cast authors `cast.json`; Art authors `art.json` and treats the
accepted Cast as read-only. Delivery inventory remains exact.

## F5A receiving and admission authority

The downstream trace found an unclosed seam: F5A still used the pinned
storyboard preset gate, which defaults omitted style to `cinematic film still`
and rejects `saved-brief`. Its frame text is later copied into canonical shot
composition and the image request. Appending Brief direction downstream cannot
repair an already contradictory source frame.

For new F5A requests inheriting saved-Brief Art, code freezes a distinct
storyboard render contract in the binding and request. It contains the exact
inherited Art contract/direction and identities of the local instruction owner,
neutral adapter and pinned upstream validator. The author owns direction; the
model owns faithful English frame/H3 interpretation and the required
`saved-brief`/`Saved Brief direction` markers; code owns authority, identity,
currentness and admission. The model cannot supply or change the frozen contract.
Generated validate/render commands and server admission use the same adapter.
Every unrelated upstream structure, coverage, timing, source/name, language,
recipe and H3 gate remains active; style markers prove authority membership,
not semantic fidelity. The report is still upstream-derived HTML, and exact
candidate/report/completion inventory forbids extra outputs or media.

The new F5A identity does not modify the hashed Cast/Art owner, pinned skills,
manual preset path or stored historical bindings. Historical absence of the
F5A contract stays absent on serialization and follows its frozen request;
only newly prepared saved-Brief work receives the new contract. Reopening F4
retains inherited Art authority, while superseded inputs or changed adapter
identity make the new F5A binding stale. Regression evidence must include real
upstream command execution, admission/acceptance and ordinary reopen/currentness,
preserved non-style gates, and source frame propagation into image requests.

## Frontend review presentation

The API readback found that the Art and Cast pages still treated every frozen
render contract as a manual preset. Manual Art contracts include `preset` and
`adapterHash`; manual Cast contracts include `preset` and `implementationHash`.
Saved-Brief contracts instead identify `authority: saved_brief` and carry
`direction` plus `emptyDirectionRule`, with no preset. Dereferencing
`preset.label` therefore blanked Art and could fail on Characters for valid
saved-Brief bindings.

Frontend bindings model the owner-specific preset contracts and the shared
saved-Brief contract as an explicit union. The pages display the contract for
the current candidate, or the accepted binding when no candidate exists.
Saved direction is shown directly; a null or empty direction uses the frozen
`emptyDirectionRule`, while a missing direction field is reported as missing.
No preset is inferred for Brief authority. Manual preset labels and Cast's
author-direction display remain unchanged. This is a presentation-only
clarification: API payloads, frozen policies, validators and generation
behavior do not change. Regression coverage exercises accepted and candidate
bindings and navigation between Art and Characters without generation.
Accepted style captions use the existing revision/hash-bound adoption label;
an AI-adopted style remains labelled AI-adopted after cancellation and is not
presented as a new human confirmation.
