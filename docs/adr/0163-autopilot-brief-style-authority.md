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
