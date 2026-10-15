# 0177 — Invocation-local autopilot profile construction

Status: owner-authorized October 14, 2026; implementation committed at
`db0216999210616fa6020ef156b811abb735d55f`, parent
`8ab58839df652e21ec5eef51a63c925d33a1af58`. Independent stable code review,
142 focused checks and one quiet unchanged-case pair are complete. The pair is
scoped observational evidence; current whole-Python measurement, combined full
qualification, publication and product acceptance remain open.
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

## Executed checkpoint — October 15

The exact committed candidate bytes passed 51 new-contract and 91 selected
consumer cases before commit; committing changed no content. Independent stable
code and observer reviews found no remaining actionable issues after bounded
observer corrections. An explicit eight-file Ruff F-family check passed; the
earlier default Ruff check remains failed with ten non-F findings. These are
focused/static records, not quick, module or full release qualification.

Root accepted one quiet native mapped-consumer pair on clean before `8ab58839`
and after `db021699`, using a detached control and the same checked physical
Python 3.12.13 environment. Separate accepted natural collection/source-binding
proof established each arm's package, test, fixture and tool ownership despite
the shared editable environment. The measured command used only the original
timing plugin, fresh external roots and the unchanged fixture generation.

Whole focused-command time, including immediate owned cleanup, was
50.113741375s before and 45.048235292s after; case setup/call/teardown totals
were 47.094782542s and 42.662325292s. Both actual one-case executions passed
with the same native fingerprint. This single pair observed 5.065506083s less
command time; it establishes no statistical or whole-suite gain and cannot be
added to earlier observations or subtracted from a historical complete run.
The fixed-resource 151.73295-second / 85-percent target remains unmet.

The [roadmap receipt](../roadmap/2026-10-14-python-context-and-workers.md#ordinary-open-profile-correctness-and-matched-result--october-15)
records the exact case, fingerprint, commands, phase rows and artifact hashes.
Retained result:
`.local/remaining-cost/ordinary-open-profile-isolated-jf3tfr7m/result.json`,
SHA-256 `7d20525429c5e829e52b04fc0bc1bebadecd624333d76f44b2adf7dcfda9b2fd`.
This documentation receipt was written after the pair; it changes neither the
measured revision nor the executable contract. No tests were rerun solely for it.
