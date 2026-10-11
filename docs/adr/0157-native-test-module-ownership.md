# ADR 0157 — Native test module ownership

Status: accepted, 2026-10-11.

## Context

The existing verification runner supports explicit file and case selectors,
but no product-module ownership map. Splitting a test file or running a subset
by directory alone cannot show that every native parameter row still has one
owner or that test setup is shared across module boundaries. Each runner has a
different discovery format; Vitest's JSON list repeats identical file/name
pairs for parameterized rows whose titles do not interpolate the input.

## Decision

Maintain exact repository-relative test-file selectors in
scripts/testing/module-ownership.json. Each collected test file has one
primary product or verification owner. Keep shared runner configuration,
setup, fixtures and helpers in a separate dependency register with the modules
that consume them; a support dependency does not duplicate test ownership.

The native guard runs collection only for pytest, Vitest and Playwright. It
refuses ambient selectors, stale or unknown files, empty modules, duplicate
ownership, source test files with no collected cases, unowned native cases and
any module union that does not cover the complete collected case set exactly
once. It does not execute test bodies or alter quick, focused or full.
Named module execution and dependency expansion remain a separate M2 change.

Preserve runner-native case identity and every parameter row. Pytest IDs and
Playwright's path, source location and full title are retained. When Vitest
emits repeated JSON rows with the same file and title, preserve their native
list order and suffix each row with its occurrence number and multiplicity.
Vitest's list interface does not expose a parameter value or source location
for those repeated rows; the ordinal distinguishes the discovered rows without
pretending to recover hidden parameter data.

## Alternatives and consequences

Directory ownership was rejected because the suites do not share product
boundaries and several use explicit shared fixture modules. Runtime tags and
automatic file-name inference were rejected because they can silently leave
new tests unowned. Duplicating shared fixture cases across modules was rejected
because it would execute them more than once.

The manifest is intentionally reviewed data: when a test file moves, a new
test file appears, or a shared helper gains consumers, update its primary owner
or dependency consumers. The native guard detects stale, duplicate, empty and
uncovered entries before module execution can be introduced.
