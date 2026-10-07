# ADR 0125: Complete managed assets in candidate projections

Status: Accepted, 2026-10-07.

## Problem

Art, character-reference and shot-image candidates embedded only managed byte
metadata. The asset list separately joined persisted provenance. Consequently
the gallery reported unavailable origin/rights for an asset whose declaration
was present. Initial delivery, repeated delivery checks and reopened history
shared this omission.

## Decision

Use one session-aware public managed-asset projection for candidate reads and
asset listing. It joins the earliest persisted declaration with deterministic
identity ordering and uses the existing common declaration projection. A missing
declaration remains null; a missing asset remains null. Reads never rewrite
declaration history, grant rights or imply reference/creative approval.

The metadata-only projection remains internal for byte-storage lookup and writers
that already hold the exact newly admitted declaration.

## Alternatives and guardrails

Reject frontend defaults, another asset fetch per gallery item and invented
rights: those conceal the API mismatch. Regressions compare first and repeated
delivery, listing, reopen and asset-workbench DTOs; shared candidate readers
cover complete, absent and invalid declarations without mutating evidence.
