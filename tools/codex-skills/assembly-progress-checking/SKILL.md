---
name: assembly-progress-checking
description: Report ordered assembly progress and validate source-bound selection and export evidence without choosing takes or generating media.
metadata:
  version: "0.1.0"
---

# Assembly progress checking

Invoke manually for a supplied project and explicit selection/evidence. Report ordered
segment coverage and gaps per episode, separately for technical evidence, explicit
selection, and export. Never choose a best/latest attempt or turn technical PASS into
review, selection, perceptual audio or creative acceptance. A missing or stale binding
is a gap, not a reason to mutate a source or make a new export.

Use `scripts/progress.py` on the normalized contract in [contract.md](references/contract.md).
Counts and order come from the current source; do not hand count. Source, selection,
media and export receipts must be content-bound and rechecked. Show historical
receipts as historical when current inputs no longer match. Do not mistake the mere
presence of a receipt for a verified export. Reuse a frozen proof only when its
receipt, source, selection, media and proof bindings are actually verified; otherwise
mark it unqualified. For exact new verification, use the project's existing assembly
proof tools on actual media, read-only and without overwriting originals. Distinguish
ordered pre-encode native PCM plus bounded explicit EOF zero padding from lossy AAC
output. Never claim encoded AAC samples are identical to pre-encode PCM.

For this Plotloom production the read-only `scripts/plotloom_adapter.py` uses the
existing manager `current_authority` and `selected_clip` functions; run with the
project's locked `uv` environment. It reports every qualifying technical attempt
without implicitly selecting one. It accepts a supplied partial selection; the final
assembler's full preflight remains authoritative before an actual export. The adapter
and historical preview verifier are project-specific; the normalized reporter is not.

Default to GPT-6.1 Terra/medium for routine delegated checking; use high for uncertain
material discrepancies, subject to available native settings and explicit user choice.
Deterministic checks require no model counting. Do not add diagnostic review as a
production gate, submit generation, or assemble without separate authorization.
