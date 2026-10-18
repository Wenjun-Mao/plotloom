# 0195 — Process command identity is independent of display width

Status: accepted; scoped module/Linux verification passed, 2026-10-18.
Full local and hosted qualification remain separate; see the
[correction record](../verification/2026-10-18-hosted-qualification-remediation.md).

## Problem

The Linux reconnect regression observed the same live helper's PID, group and
start text with two command strings: the detached helper recorded its complete
argv, while the RPC caller's `ps` output ended at 78 characters. Different hashes
caused a correct fail-closed ownership refusal and UNKNOWN hold before CLI
identity publication. Display geometry was accidentally part of process identity.

## Decision

Command capture explicitly requests unlimited width with `ps -ww` on both the
Mac host and provider-free Linux tests. The independent test-process ownership
journal uses the same width rule: its detached guard also announces full argv,
and a truncated parent observation otherwise refuses even a safe Git command.
Both installed Mac `ps(1)` and
[procps documentation](https://gitlab.com/procps-ng/procps/-/blob/master/man/ps.1)
define repeated wide output independently of terminal width. Start/group probes,
timeouts, token shape, ownership comparisons and missing/denied observations
retain their existing behavior. An owned long-argv regression compares narrow
and wide caller environments, alongside the existing cross-host lifecycle case.

## Alternatives and consequences

Comparing command prefixes, accepting unequal identities, or assigning a Linux
fixture exception would weaken ownership. They are rejected. This change makes
capture consistent; it does not make the separate legacy `ps` probes atomic,
certify historical timezone/session facts or prove incarnation retirement.
Retained tokens are not rewritten or given compatibility fallbacks. A truncated
old token can still refuse ownership. ADR 0190's quiescence guard remains intact,
and the A99 activation blocker remains unresolved. Deploy only after ordinary
qualification and live ownership checks; do not test this by signalling unrelated
processes.
