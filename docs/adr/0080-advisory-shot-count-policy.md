# ADR 0080: Optional shot-count guidance and dependency-aware Brief edits

Status: Accepted for bounded implementation, 2026-09-22. Creative and production acceptance remain separate.

## Context

The retained U4 lighthouse has one F4 scene occurrence and nine authored F5 cuts in each of three sections. The existing Brief says 2–4 shots per scene. The range currently acts as a strict canonical and generation gate; any Brief edit also stales the source-map graph and, transitively, accepted F2–F5 even when the edit changes only shot policy. F1 source, outline, and section map do not consume that policy. The director has approved treating shot count as optional creative guidance by default for new projects, with explicit strict enforcement when desired.

## Decision

`ProjectBrief` owns one `shotCountPolicy` value: `advisory` or `strict`. The stored absence of this field means **strict** for existing projects; read/open must not rewrite old Brief bytes, project revisions, hashes, or accepted bindings. New project creation must explicitly persist `advisory` when the caller omits the field, including idempotent creation. An explicit `strict` remains available in the Brief editor and API. The numeric min/max range remains a preference in advisory mode and a required bound in strict mode. It is not a provider capability, duration limit, or universal shot ceiling.

Canonical V1/V2 storyboard validation and the bridge use the same Brief policy. Strict out-of-range counts block; advisory counts do not. The current V2 gate and bridge proposal are the review surfaces that display nonblocking advisory evidence. V1 is a retained validation-only contract with no warning result or review UI; this decision does not add a new legacy review channel. All other coverage, timing, entity, resource, and provider-duration checks remain mandatory. The bridge retains one F4 scene occurrence per canonical scene and one F5 cut per canonical shot with exact source coordinates and milliseconds. It never splits or omits cuts to satisfy guidance. The existing gate-set version remains valid for legacy strict projects, with their pre-policy input hashes preserved; advisory evaluation records a warning-shaped, nonblocking result under a distinct Brief input hash. Storyboard generation continues to show the preferred range in its prompt, but its response schema and semantic count check use only the strict range when strict is chosen; advisory mode uses hard timing/resource feasibility rather than quietly imposing the preferred maximum. Frozen jobs preserve their own contract.

Brief invalidation follows evidenced dependencies, for both direct and draft-consuming saves. A shot-policy-only edit does not stale a source-map graph or accepted F2–F5 whose hashes and F4 timing binding are unchanged. A graph topology edit invalidates the graph and its dependants; a playthrough-target edit invalidates timing-dependent F4/F5 even if the graph stays valid. Other Brief fields retain conservative existing invalidation until their ownership is separately established. Already-installed canonical Storyboards must be revalidated or marked stale when their effective strict policy changes; no policy edit may silently leave invalid content ready. Source-map graph admission display must reflect a stale graph head, not revision equality alone.

The bridge still freezes the full raw Brief revision/hash. Every Brief edit makes an old proposal stale; a new proposal and exact whole-package review/save are required before explicit installation. Historical model suggestions and reviewed text may be carried forward only as identified previous evidence after exact source-coordinate/hash matching, never as a fabricated new inference or automatic creative acceptance.

## Rejected alternatives and consequences

- A bridge-only exemption would leave canonical validation and storyboard generation with conflicting shot authorities.
- Silently changing an existing missing policy to advisory would reinterpret accepted legacy projects and hashes.
- A fixed nine-shot ceiling, source splitting, or cut omission would be arbitrary or would rewrite the retained source shape.
- Re-running F1–F5 after every shot-policy edit is safe but falsely treats a production preference as a source/timing dependency.

This changes a public Brief field, gate semantics, generation prompt/schema semantics, bridge review shape, and Brief currentness rules. Regression coverage must include old/new defaults, strict/advisory and counts above nine, both save paths, topology/timing changes, existing canonical heads, stale proposal CAS, exact cut preservation, and restart. No media or provider dispatch follows from an advisory pass or bridge confirmation.
