# Direct project deletion

Status: Owner-approved implementation, 2026-10-04.

## Outcome and sequence

Make permanent deletion visible in the project directory without Archive or
reopen prerequisites, including projects with media. Preserve explicit consent,
revision checks, project confinement and unknown-job safety. The root cause is
recorded in [ADR 0114](../adr/0114-direct-project-deletion.md).

1. Amend the owning folder deletion contract and exact request revision checks.
2. Add typed DOM confirmation, project-scoped local cleanup and direct row action.
3. Verify disposable media-bearing, closed, busy and cross-project cases; obtain
   independent read-only review and run the established stable-candidate gates.
4. Publish qualified source, activate normal 8841 after quiescence checks and
   inspect consent without deleting either existing project. Compare preserved
   normal project data and settings before and after activation.

Stop when the qualified, deployed direct deletion flow is verified and published.
Creator usability acceptance remains the owner's subsequent walkthrough.

## Exclusions

No real project deletion, generation, cancellation, V1 edits, H3 activation,
credential changes, Chinese manual synchronization, snapshot erasure or broader
contract rewrites. A proposed current-runtime contract audit remains separate.
