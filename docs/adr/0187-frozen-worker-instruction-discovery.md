# ADR 0187: Frozen-worker instruction discovery

Status: Accepted, 2026-10-17

## Problem and evidence

The manual walkthrough's first Outline attempt launched the native CLI, but its
private stderr reported `failed to load AGENTS.md instructions` with an operation
not permitted error. Its JSONL stream was empty. Without an exact session and
terminal evidence, the host correctly retained UNKNOWN and its capacity hold.

Frozen delivery directories can be nested below a checkout containing unrelated
development instructions. Ignoring user configuration does not disable Codex's
ambient instruction discovery. That discovery conflicts with the explicit
deny-root/package-only filesystem boundary before the frozen assignment runs.

A credential-free, no-turn initialization probe using the installed binary and
the unchanged permission formatter reproduced the same error in an owned fixture.
Changing only the project-document budget to zero allowed initialization. The
probe used a closed loopback provider endpoint, no existing authentication/session
home, and no `turn/start` request. It did not retry the user's job.

## Decision

All frozen text and image workers pass `project_doc_max_bytes=0`. Their instruction
authority remains the source-owned stdin assignment, complete frozen package and
explicitly pinned source resources. Ambient global/ancestor/local AGENTS documents
are not part of that authority and must not be discovered implicitly.

Keep command construction with the existing child-environment/permission owner,
so both domains receive the same initialization policy. Preserve every existing
permission, feature, authentication, model and evidence constraint. Do not grant
ancestor/source-root/auth-home reads or alter the user's instruction files.

## Consequences and guardrails

The exact invocation remains covered by the executor's source hash. Regressions
must cover text and image commands, package instructions and unchanged allow/deny
boundaries. Fake CLI tests alone cannot establish native initialization behavior.

UNKNOWN is not a synonym for an inferred startup failure. Do not derive terminal
authority from stderr text, a missing PID or a later successful probe. Absent
separate explicit operator disposal authority, the original attempt, frozen
profile, reservation and raw evidence remain unchanged. An authorized discard is
not terminal settlement and must not silently start replacement generation.
This fix itself does not authorize a duplicate attempt or resume a held run.
