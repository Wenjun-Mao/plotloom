# Provider-free validation and explicit acceptance boundaries

## Result and delivery state

Implemented and independently reviewed on `codex/validation-quality-boundaries`,
based on `4af2db95`, while the language coordinator retains functional closeout
ownership. Integration is held until that closeout; reconcile the plan's current
status with the coordinator's final evidence when integrating. This is a workflow,
documentation and regression-test change, with no production runtime/schema edit.
The separately queued media-quality refactor remains after functional closeout.

The four approved changes are durable in:

- `AGENTS.md`, ADR 0023 and the developer guide: internal changes default to
  contracts, complete final-request comparisons and retained-media functional E2E.
  Fresh media answers a specific uncovered integration question.
- Existing adapter/host boundaries: complete H3 multipart fixture and intended
  seed-only difference; dialogue/reference/audio omission controls; ImageGen
  observed-argument and ordered-reference refusals; a sticky live-dispatch guard.
- Existing functional-only receipt tests: unreadable-lettering limits remain
  explicit, original rejection events survive, corrupt bytes and changed request
  provenance still block, and replay cannot drop the quality limitations.
- The compact plan template, roadmap entrypoint and language plan: one current
  status and acceptance table, with superseded instructions nested as history.

## Verification

32 distinct cases passed across focused selections. The initial 25-case run
finished in 19.422 seconds. Retained-project reopening added six cases in 9.750
seconds. After review, the ImageGen selection passed 12 cases in 3.600 seconds:
three argument mutations now reach receipt comparison rather than an earlier
session mismatch, and two reference mutations exercise their supervisor owner.
These overlap the initial selection; the total is not a sum of all run counts.
The six H3 final-request cases also passed after moving image hashes before
direction compilation (2.236 seconds).

Focused Ruff and `git diff --check` passed. Module ownership manifest schema,
paths and unique ownership passed; this was not full native suite discovery.
Python was 3.12.13. The existing FastAPI/Starlette test-client deprecation warning
remains. All checks used local fixtures: zero live H3 or ImageGen submissions.
The expected multipart fixture was inspected against exact dialogue, visible
text, room-tone/no-music constraints, opening/ending identities and scalar settings.

Independent Sol/Medium review found one weak ImageGen negative control, repaired
as described above; the follow-up review found no further actionable issues.
Run the representative selection documented in
[the developer guide](../development.md#validation-without-new-media).

## Evidence limits

ImageGen has no deterministic pre-submit inspection seam for the final prompt
composed by the agent. Retained observed tool arguments are separate from its
frozen brief; these tests do not claim a new live integration or creative-quality
pass. The HTTP/native-host guard covers the existing tested dispatch paths and
is not a process-wide network sandbox.

Branching/browser, report export, full qualification, package activation and
cleanup remain owned by the existing language closeout. Its prior failures stay
failed; this receipt does not convert them to passes. No full-suite rerun, live
mutation, publication, CI, new evaluator service or quality-generation campaign
was performed for this isolated follow-up.
