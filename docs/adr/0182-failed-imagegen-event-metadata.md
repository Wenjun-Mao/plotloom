# ADR 0182: Failed ImageGen terminal metadata

Status: Root-approved bounded decision; implementation candidate, 2026-10-16.

Related: [0165](0165-serial-codex-exec-autopilot.md) owns exact CLI telemetry
and failure settlement; [0178](0178-capsule-plan-handoff-authority.md) owns
finite qualification and current-process settlement.

## Context

A bound native ImageGen Extension reported `status=failed`,
`transparentBackground=null` and no savedPath. The exact call had explicitly
requested false. The adapter required a boolean for every terminal event, so
it rejected a legitimate failure shape before the supervisor could settle that
failure. Existing test helpers always supplied false and missed this case.
The mismatch is demonstrated; a later parse does not reconstruct which
UNKNOWN branch the historical worker took.

## Decision

Completed events require a boolean transparentBackground matching the exact
call and a nonempty savedPath. Failed events may omit output-only transparency
or declare null; the observed value remains None. A supplied non-null value
must still be a strict boolean matching the call. No value is coerced or copied
from the call to fabricate event metadata. This is a current telemetry contract,
not a provider fallback or a per-run exception.

Session, call, event identity, ordering and reference-view checks stay strict.
The supervisor reaches normal failed settlement only after its existing strict
process-group exit and evidence gates. Missing/ambiguous telemetry or unresolved
process ownership remains UNKNOWN. Historical attempts, reservations, files and
qualification outcomes are not rewritten or automatically reconciled.

## Alternatives and guardrails

Requiring success-only metadata on failed events loses usable terminal failure
proof. Defaulting missing metadata to false invents an observation. Trusting
stderr/model prose or relaxing completed events weakens execution evidence.
All are rejected.

Faithful sanitized failed/null and failed/absent fixtures must preserve None.
Wrong-type or mismatched supplied values, incomplete successful output metadata,
unbound/duplicate events and invalid ordering must refuse. The real supervisor
execution path must settle a bound failure after strict synthetic group-exit
proof, while missing session/event evidence, ambiguous terminal evidence and a
group that has not exited retain UNKNOWN and capacity. Provider-free checks
qualify software only; native execution and creative acceptance stay separate.
