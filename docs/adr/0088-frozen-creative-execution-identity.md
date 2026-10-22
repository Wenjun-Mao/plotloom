# ADR 0088: Persist creative task execution identity at preparation

Status: Accepted — 2026-09-26

## Problem and evidence

A completed character candidate could not refresh after the local specialist
skill received an authoring-guidance update. The package and delivery both
recorded the earlier skill hash; the candidate and report byte hashes matched
their manifest. `_verify_frozen_package` nevertheless reconstructed its expected
package using the current checkout through `_pinned_execution`. It confused a
later development change with tampering of the frozen task.

## Decision

Trusted project persistence owns a write-once execution identity bound to the
job and original request hash. New creative tasks capture it at preparation;
existing task reads use the stored identity, never recompute it from current
skills. This applies to outline, characters, art, script and storyboard tasks.
The original request hash and specialist-visible output contract remain intact.

Package verification still compares the complete expected request projection,
instructions, template and inputs. Delivery provenance must match the trusted
execution identity, and declared output hashes must match actual bytes. Neither
the package nor the specialist's completion manifest can authorize its own pin.
Current source/stage revision checks and explicit creative acceptance remain
separate and unchanged.

For a retained task lacking this record, ordinary refresh fails closed. An
explicit operator recovery may bind an independently selected preparation-era
repository revision only after verifying its skills and existing package against
the trusted stored request. A revision merely claimed by the candidate is not
independent evidence. Recovery records that provenance without rewriting the
package, original request or completed delivery, and does not accept content.
This is preservation of specifically authorized valued work, not automatic
historical replay or a fallback to whatever files happen to exist.

## Rejected alternatives

- Revert the skill to unblock one delivery: leaves every future skill update
  capable of breaking prepared tasks.
- Trust the package's own hash or weaken comparisons: permits coordinated
  package/provenance substitution.
- Rewrite the retained task to the new hash: falsifies its execution history.
- Automatically accept old packages when a record is absent: creates an
  unverified trust-on-first-read path.

## Consequences and guardrails

Execution provenance is now durable project state. Missing records require an
explicit decision; they cannot be silently synthesized during refresh. Tests
cover new preparation, restart/reopen after skill drift, coordinated tampering,
missing pins, recovery and immutability. No provider calls, candidate generation
or creative acceptance are part of this fix.
