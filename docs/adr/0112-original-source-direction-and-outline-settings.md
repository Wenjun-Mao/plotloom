# ADR 0112 Original source direction and frozen outline settings

Status: Accepted, 2026-10-04.

## Context

The creator's new-project walkthrough exposed repeated work: Brief already
seeds the Source story, but Source requires another adaptation intention even
for an original synopsis. The outline handoff receives only Source, omitting
the author's saved duration, language, style and production scope. Asking the
creator to retype these settings compensates for a missing handoff contract.

## Decision

For `synopsis`, the seeded story can be confirmed unchanged. `adaptationIntent`
is an optional, trimmed string, presented as “补充创作要求（可选）”; an empty
string remains empty, not a stock or inferred creative instruction. For
`imported_text` and `existing_work`, “改编目标” remains required. Changing the
source type preserves entered text and direction while revalidating the form.

Trusted code supplies `inputs/outline-settings.json` from the saved Brief,
excluding its title and synopsis. Confirmed Source owns story facts and title;
Brief owns format, style, route-duration target and scope. The specialist must
read both, preserve explicit direction, treat a blank direction as no additional
request, and report conflicts rather than silently choosing a new author goal.
These settings do not imply generation, acceptance or provider capability.

Preparation, delivery admission and explicit acceptance compare this frozen
settings projection with current project settings inside the owning write
transaction. A relevant Brief edit blocks an unfinished candidate's delivery
or acceptance; it does not retroactively reopen an already accepted outline.
After explicit acceptance, the existing field-specific production owners handle
later settings edits: shot policy invalidates the production bridge, and route
duration invalidates timing-dependent stages, not the confirmed Source chain.
Title/synopsis-only Brief edits do not overwrite confirmed Source or change
the settings projection.
Historical requests, candidate evidence and accepted creative content are not
rewritten. New preparations must carry the named settings artifact; missing or
changed settings cannot be admitted by the new contract. Cancellation retains
its explicit existing lifecycle meaning.

The overlarge source/outline persistence owner separates source and outline
mutation transactions from map compilation and state reading before adding
the new admission checks. It retains one repository and transaction owner.

## Alternatives and guardrails

We reject deleting adaptation goals for imported works, inserting boilerplate
to satisfy validation, automatically accepting the carried-over synopsis,
requiring repeated Brief settings, relaxing stale-delivery checks, or making
every production setting edit require a new Source/outline review. The latter
failed existing shot-policy and Script replacement regressions because it
discarded the accepted story boundary rather than invalidating its actual
downstream consumers.

Regression coverage must include unchanged synopsis confirmation with no
direction, required imported goals, preserved entered direction on type changes,
exact settings publication, stale preparation/delivery/acceptance, Brief edits
through both save paths, preserved accepted source facts/outline, field-specific
downstream invalidation and explicit candidate review.
V1 is a separately running visual reference; production cannot read V1 runtime
or project data. The Chinese manual is intentionally left unchanged until the
creator's broader same-day changes settle.
