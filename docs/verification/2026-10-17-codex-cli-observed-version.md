# Observed Codex CLI version — October 17, 2026

## Decision and source

The manual walkthrough reached the configured Mac execution bridge but profile
construction refused the installed `0.163.0-alpha.10.2` CLI solely because it did
not equal `0.162.0-alpha.17.2`. The owner rejected a version allowlist as a
production availability policy. [ADR 0165](../adr/0165-serial-codex-exec-autopilot.md)
records the replacement: bounded optional observed metadata, not launch authority.

Implementation: `20dc09574f1e266bb4843ca1587c27c9cdaae78b`.
Reviewed purity clarification and regressions:
`3e9f8778b087bb881f395f9b83880b83705112b8`.

Executable/profile/source/toolchain identities, permissions, native event and
session evidence, trusted validators, receipt/output checks, and UNKNOWN/no-resend
rules remain enforced. Missing version metadata is not a wildcard for frozen
profile comparison. Retained historical profiles and outcomes are not rewritten
or recertified. No per-version registry or help-output compatibility parser was
introduced.

## Executed verification

Before the final gate, 122 distinct native focused cases and 71 service cases
passed, along with scoped Ruff and whitespace checks. Expected-red version-gate
failures and the corrected diagnostic-sentinel assertion remain retained.

The single full invocation on clean `20dc0957` ended naturally at exit 1:

```sh
uv run --locked --no-sync python scripts/verify.py full
```

Dependencies, media probes, API import checks, archived prompt reader, 1,381
frontend cases and frontend types passed. Python reported 3,095 passed and one
failure: the deliberate ADR 0184 semantic-AST review tripwire. Making immutable
version metadata nullable changed its reviewed model fingerprint. Root and
independent review confirmed that no factory, mutable state, ambient observation
or I/O entered the reused value-construction boundary. The reviewed pin was
updated only after recording that finding in ADR 0184 and adding explicit-null
and omitted-metadata exact-text reuse regressions.

The failed and affected six-file union then passed **94 cases**. Unchanged
production bytes and the other 3,095 Python results are reused under the repository
verification policy; this is not a claim that the original full invocation passed.
Final native ownership discovery covers **3,098 cases / 261 files**, fingerprint
`ee31e6ad5033bdcab3c71cedfe4e7d6efa8db18a60c411de4d7090802dd01585`.

All six downstream full steps passed on `3e9f8778`, using the existing runner's
exact step definitions, ambient-filter refusal and temporary wheel lifecycle:
deterministic build, checked bundle parity, unfiltered browser allocation,
**319 browser cases** including browser types, wheel build and installed-wheel
smoke. This continuation exited 0 in 485.023 seconds; no skip or reduced selector
was introduced. Its native handle `7706` closed `0b74fb` to `5d485e`, exit 0.
No application, service, dependency or frontend bytes changed between the
original full run and this continuation.

A provider-free check invoked the installed CLI through the retained
`native_sandbox_check.py` diagnostic and unchanged image-command permission
formatter. Reading its owned package control passed, while reading an owned
outside sentinel was denied. Native `417138` exited 0; its result binds executable
SHA-256 `1afb28c01d7d49e892bd75f11076b10f1451e34e0ee308a95e5ab7f69f9c84fe`.
It made zero model/provider calls. These two controls check command sandbox
behavior only, not built-in ImageGen/reference tools or end-to-end generation.

Original native handles: full `79037` closed `997a28` to `a8733d`, exit 1;
affected focused `48577` closed at `2815a6`, exit 0; initial focused `77866`
closed at `bbc0ef`, exit 0; service `62019` closed at `fc26a8`, exit 0. Focused
counts come from those native execution results, not collection-only ownership
discovery. Raw full/downstream logs and diagnostic code/controls remain private
under `.local/cli-version-observation-20261017/`.

Retained log SHA-256 values:

- `full.log`: `9c0f6d68c17bea6ee16af0db694921e35e4fa1c26600bdbbe9385c7f9c241600`.
- `downstream.log`: `b82687962f81819a3c17b21a1947cd9ffae92769f0c9d9395d4fbb29e53431bd`.
- `final-ownership.log`: `5d7bee5320dc79f1dd5e0d2a2cc54932a82aaa94377490b9768992348ad1766e`.

## Installation and acceptance boundary

The current walkthrough project and installation-local credentials/settings must
remain unchanged. The bridge and application will be restarted only after their
own queue, attempts, slots and validators are confirmed empty. Readiness and a
valid live profile must be checked after activation; an older bridge-readiness
failure has not been causally reconstructed and no authentication repair is
claimed. No story generation, hosted CI, creative acceptance or product acceptance
is established by this record. Python optimization and image batching stay parked.
