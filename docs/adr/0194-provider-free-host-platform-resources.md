# 0194 — Explicit platform resources in provider-free host tests

Status: accepted; scoped module/Linux verification passed, 2026-10-18.
Full local and hosted qualification remain separate; see the
[correction record](../verification/2026-10-18-hosted-qualification-remediation.md).

## Problem

The required Linux hosted suite runs provider-free Codex host tests, while the
production host is a Mac. Its pinned Node OpenSSL file is deliberately required.
The shared fixture owns source and a synthetic checked Python receipt but did not
own this platform resource. Exact profile and qualification cases reproduced the
missing-file failure on Ubuntu before reaching their intended assertions.

## Decision

Cases opting into `codex_exec_test_source` receive a function-scoped, private
test-owned OpenSSL config through `tests/codex_exec_platform_fixtures.py`.
The parent substitutes only the configuration constant. A test-owned Python
startup module on that test's `sys.path` supplies the identical substitution to
real worker children through the existing worker environment. Teardown restores
the parent's module and path. Child lifecycle ownership remains the test's job.
The separate paid-source fixture explicitly creates the same resource under its
existing case owner. Its test entrypoint binds that config after selecting the
copied source, then adds startup for actual worker children; it does not install
a session-wide parent patch or an ambient interpreter override at the guarded
launcher. Startup loads production modules from the fixture's copied source
before substituting only the config constant. The existing synthetic uv exec seam
also owns executable lookup and temporary storage, mapped to case-owned paths
instead of manufactured Mac system paths. Launch/phase/source validators remain
real and continue refusing ambient interpreter overrides.
The paid sandbox wrapper and pair-schema entrypoint bind that same case resource
explicitly after selecting source; neither relies on inherited Python overrides.
The sandbox wrapper still compares the entire frozen production command before
running its real Node tail.

Production defaults, copied production source, profile/source/receipt validators,
permission construction and missing/symlink file refusal remain unchanged.
The bootstrap contains a literal owned path; production gains no environment
selector, Linux fallback, alternate profile or provider authority.

## Alternatives and consequences

Creating a fake `/System/Library` file would conceal an accidental host dependency.
Relaxing production validation or mocking the whole profile would weaken the
contract. A parent-only monkeypatch fails again in the actual helper interpreter.
These approaches are rejected. Tests must cover propagation into a new worker
interpreter, real helper completion/UNKNOWN reaping and missing/symlink refusal.
Linux arm64 reproduction remains separate from hosted x64 qualification and
native Mac provider execution. No external provider or creative acceptance is
established by these fixtures.
