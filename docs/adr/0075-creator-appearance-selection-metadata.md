# ADR 0075: Creator appearance selection has no required attribution fields

**Status:** Accepted

## Context

The Characters appearance workspace makes a creator choose a project-owned
identity reference under accepted-cast currentness and revision protection. Its
older request required a reviewer and written rationale, so the interface split
image viewing from selection and forced people to enter ceremonial values before
an otherwise safe choice.

## Decision

Character-reference selection no longer requires creator-supplied reviewer or
notes. New decisions persist those fields as absent; historic decision values
remain readable unchanged. The decision's selected assets, frozen cast context,
asset hashes, revision CAS, and current state remain the authoritative evidence
of the choice. Revocation keeps its existing explicit attribution/reason
contract because it is a distinct, consequential reversal.

The project-folder schema transition makes the two selection metadata fields
nullable without rewriting existing decision rows. The UI may show historic
metadata only in folded technical/history details; it must not synthesize a
replacement author or reason.

## Consequences

- Appearance selection can live beside the currently viewed image.
- Existing decision history remains intact and selection/currentness safety is
  unchanged.
- Story-Bible callers may continue to provide optional metadata, but are no
  longer required to do so by the shared decision API.
- This changes neither proposal dispatch nor image-generation authority.
