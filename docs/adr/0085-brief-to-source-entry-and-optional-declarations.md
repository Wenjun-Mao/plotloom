# ADR 0085: Brief starts an editable source draft; declarations are optional

Status: Accepted for the bounded creator walkthrough fix, 2026-09-25.

## Context

The creator saved a Brief, then found an empty Source form. The Brief's primary
action started the older Bible/Graph proposal route, while the source-first
route required explanation outside the product. F1A also required attribution
and rights declarations before a source could be saved. The creator requested
their removal from this entry workflow.

## Decision

An unsaved project's Brief offers one primary action, “保存并继续到来源”; a
persisted project's Brief instead offers one “保存修改” action that remains on
Brief. This applies to the unsaved teaching sample too. Both the page
description and secondary-workflow guidance follow that state. The existing
Bible/Graph proposal remains an explicitly labeled secondary workflow. A new Source form
uses the saved Brief title and synopsis as an editable browser draft only when
that project has no accepted source. It does not save or accept a source, infer
adaptation intent, or overwrite an existing source or an unsaved source draft.
Navigation occurs only after the Brief save succeeds.
First-time project creation consumes its local Brief draft so continuing does
not ask the creator to save the same content again.
The creator UI admits targets of at least three seconds, matching Script
preparation. The stored Brief schema continues to read historical one- or
two-second targets; those require explicit correction before a new UI save.

F1A now requires source kind, title, text, and adaptation intent. Attribution
and rights declaration are optional source metadata, not product prerequisites.
The form no longer requests them. Existing recorded values remain in revisions
and are carried through a subsequent source edit; absent values remain absent.
Specialist handoffs use the frozen source as supplied and must not infer
ownership, permission, or legal clearance from missing metadata. This
supersedes ADR 0058's requirement that every source carry declarations, while
preserving its review, provenance, and explicit acceptance boundaries.

## Alternatives and consequences

The outline handoff exposes a single complete Chinese execution assignment
with a copy button. It includes exact frozen request/instruction and delivery
paths and a candidate-only/no-acceptance boundary; creators do not need to add
a separate chat instruction. A read-only assignment endpoint recovers the
current prepared job after reload by verifying its existing frozen package.
It never recreates missing files or rewrites package instructions. Non-prepared
and cross-project jobs are refused. Copying does not dispatch generation.
Clipboard denial retains selectable text and does not report success.

We rejected silently copying Brief into an accepted Source revision because it
would collapse two different author decisions. We also rejected filling the
removed fields with stock claims and retiring the older proposal action because
neither matches the requested scope. API clients may continue to supply the
optional fields; old project records remain readable without migration. A
creator changing the source still triggers the existing downstream currentness
rules.

Regression checks cover new and existing Brief actions, new and existing source
entry, dirty draft preservation, optional-field handoff payloads, the
save-to-Source route, and equal Brief
control heights across viewport widths. The latter uses explicit input/select
height because a minimum height alone left the number input free to expand
under the director's browser rendering.
