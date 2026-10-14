# 0168 — Exact native case proof for Python workers

Status: accepted for the owner-approved bounded worker experiment on October
14, 2026; implemented with focused checks, complete two/four-worker experiments
and the full local gate at `4bc1d62a`. The release default stays
two under [ADR 0160](0160-two-process-python-full-gate.md).

## Problem

The coordinator checks an exact whole-file assignment, but previously accepted
worker exit codes without binding each worker's actual native collection to its
assigned case IDs. The timing plugin checked its own collected/observed set;
equal file membership or case counts alone cannot prove that coordinator and
worker ran the same parameterized cases.

## Decision

The existing timing plugin emits one versioned completion marker that includes
the exact sorted native case-ID fingerprint, case/file counts, completeness and
exit status. A successful worker must observe its unique complete collection.
The coordinator requires exactly one well-formed successful marker and compares
it to the exact assigned coordinator case IDs. Missing, duplicate, malformed or
mismatched proof fails the suite even if pytest exits zero. Do not accept old
markers without the current proof.

The producer owns the marker's line boundary: pytest's progress renderer may
leave a line open, so the plugin starts a new line before emitting the marker.
The real four-worker preflight exposed this condition. Keep the strict parser
and a regression with unterminated progress output; do not search arbitrary
log substrings for apparent completion.

Keep the same runner, native collection and whole-file scheduler for the
explicit two/four/eight-worker experimental entrypoint. `verify.py full` keeps
two workers; focused/module behavior is unchanged. Four is the first experiment;
eight requires measured memory/isolation headroom, not merely an accepted CLI
argument. Temporary roots, owned process-group cleanup, failure propagation and
ambient-filter refusal apply equally to every count.

## Consequences and guardrails

This closes a coordinator/worker evidence gap rather than weakening collection
or adding a second orchestration framework. Count-only proof, trusting exit
zero, silent environment overrides and automatic worker escalation are rejected.
Test equal-count/different-ID results, malformed/duplicate/missing markers,
four-worker isolation, partial startup and interruption cleanup. Use matched
candidate/inventory/schedule inputs for measured comparisons; added compute is
reported separately from the original same-resource speed target.
