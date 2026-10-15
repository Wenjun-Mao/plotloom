# 0177 — Invocation-local autopilot profile construction

Status: owner-authorized October 14, 2026; design reviewed. Implementation
candidate over local integrated `8ab58839df652e21ec5eef51a63c925d33a1af58`;
independent read-only stable code review found no actionable issue. Correctness
execution and matched measurement are separately scheduled, not passed evidence.
Tracked in the [Python speed track](../roadmap/2026-10-14-python-context-and-workers.md).

## Problem and evidence

The accepted mapped-consumer attribution on integrated `4525e3e0` recorded
26,832 successful `CodexExecProfile.model_validate` calls, including 26,361
same-input/output repeats in 471 ordinary validator invocations outside receipt
trust boundaries. Instrumentation was contended and added substantial overhead;
these counts identify repeated construction, not attainable savings or progress
toward the 151.73295-second complete-suite target.

Two native binding sites reconstruct profiles from freshly selected policy:
the attempt helper after parsing its snapshot, and the creative branch before
rebuilding its validation plan. This structural construction belongs to the
validation invocation. The surrounding SQL, provenance and receipt checks do not.
Read-only SQLite connections establish no complete-pass snapshot guarantee;
active cursors or caller-owned transactions can affect observed visibility.

## Decision

Each `assert_autopilot_contracts` invocation owns one private successful-profile
slot, discarded on return/error. Only its direct checkpoint and decision passes
receive it through a private common binding body. The public checkpoint signature
and fresh behavior stay unchanged. Frame, geometry/lineage, bridge-adoption,
command/admission and nested public paths remain fresh. This deliberately bounded
owner scope is not propagation through every nested consumer.

At each original constructor point, retain that site's own raw policy value
from its existing SELECT, decode it as before, and evaluate the existing
`policy.get("executorBinding", {})` before lookup. Only exact built-in TEXT
equality permits reuse of that private profile. The raw text guards equality;
it never replaces a database row or fresh decoding. Do not key by run, row/model
identity, normalized JSON, profile hash or the earlier parsed run-policy map.
Full policy text is deliberately stricter than executor-binding equivalence.

Clear the slot before extraction/replacement, retain only after success, and
take the original constructor path for all non-TEXT inputs. Thus A/A constructs
once, A/B/A constructs three times, and failure or bytes input cannot recover an
older success. Constructor class/options stay fixed; accept no caller-supplied
profile or forged `model_copy` result. The current profile contains only scalar
or immutable tuple fields, forbids extras, freezes assignment and validates
supplied data without ambient state. Future mutable fields or ambient validation
invalidate this assumption and require review. Frozen assignment alone is not
the justification for reuse.

Keep SQL/order, decoding, transaction/isolation/cursor behavior, comparisons,
error priority, `profile_hash` calculation, attempt and receipt parsing,
`assert_receipt_matches_attempt` snapshot revalidation, filesystem and admission
boundaries unchanged. No profile survives the invocation; no rows are retained.

## Alternatives and guardrails

Reject global/session/connection/ambient caches, historical result maps, eager
priming from `LaunchPolicy.executor_binding`, and plan/hash/receipt reuse. Outer
model priming adds unnecessary alias/default/nested-construction and error-phase
coupling. Retain fresh construction everywhere if a later matched comparison
does not justify this bounded change.

Focused guards cover exact text changes (including unrelated fields, aliases,
defaults and encoding), replacement/failure/non-TEXT fallback, retained serial
and v8 pool profiles, immutable fields, native SQL/error order, separate/reentrant
invocations, independent connections and every retained receipt boundary. WAL
commits use deterministic read-phase boundaries and compare original observations;
tests must not force visibility by changing cursors or transactions. Reuse the
preselected contract/open/claim/geometry/recovery consumer union and obtain an
independent stable review. Correctness, a new quiet uninstrumented matched pair,
combined release qualification, publication and product acceptance remain separate.
