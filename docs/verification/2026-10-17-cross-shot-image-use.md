# Cross-shot image use — October 17, 2026

## Contract and scope

Implementation: `901e62705ed63b6b3359371a33b91af39e295688`.
Browser-fixture correction: `cf689db9d689b13e2cda1d1d27fd5ce4fb0bbd30`.
[ADR 0189](../adr/0189-cross-shot-image-use.md) separates immutable image origin
from a reviewed target-shot use. It adds unchanged-frame reuse and one independent
scene-continuity input to original-image preparation, without weakening default
source, machine, refinement or geometry admission.

Trusted code owns frozen source/target evidence. Each target has independent
intent, compatibility and applicable identity review. Source reselection alone
does not invalidate its frozen use; changed required authority still does.
No SQL-layout migration, provider change, automatic adoption or new service was
introduced. Existing project/media evidence and installation settings are retained.

Independent provenance and UI reviews found and closed duplicate-content receipt,
shared ordinary-intent ownership, retained target editing and source-disclosure
issues. Focused regressions cover source isolation, stale/forged/CAS inputs,
repeated unselected target saves, references and telemetry, handoff, snapshot,
preview, video, refinement and adaptation consumers. Reviews are technical,
not human creative acceptance.

## Original full outcome and root-cause correction

One clean implementation invocation ran:

```sh
uv run --locked --no-sync python scripts/verify.py full
```

Native session `54127` closed naturally, `ccef0a` → `a9338a`, **exit 1**.
It passed 3,155 Python cases across 266 files (workers 1,646 / 1,509), all 1,388
frontend cases, frontend types, dependencies/media probes/API imports/archive
reader, deterministic build/parity and browser shard coverage. The browser step
reported **317 passed / 4 failed**; wheel/smoke were not reached.

All four failures occurred when three older fixture owners reused the first
imported frame for another shot and attempted selection without saving that
target's new independent intent. The UI correctly withheld authority. The P0
failure was its second-shot selection, not its initial same-shot operation.
The two video-pilot cases shared this setup; branching playback stopped at the
same second-shot boundary.

The correction changed only three existing browser specs and one shared fixture.
It saves each explicit target intent, records required current target identity
review, and asserts the source binding/intent remain unchanged. All original
playback, exact-frame/range, restart, byte and deletion assertions remain; no
timeouts, assertions or product guards were weakened. No duplicate import avoids
the intended reuse path. The affected four cases plus both new cross-shot journeys
passed together (**6/6**, session `51079`, completion `ae7be1`).

## Recorded local results

The executable application, frontend/unit sources, checked assets, locks,
dependencies and verification tooling are identical between `901e6270` and
`cf689db9`. Following AGENTS' failure/evidence-reuse policy, the unchanged
Python/frontend/build results were reused and the changed browser and unreached
downstream checks were requalified:

- Unfiltered `npm --prefix frontend run test:e2e`: **321/321 passed**, including
  browser TypeScript, session `78312`, `dbd516` → `2d0d74`, exit 0.
- Current shard check: 94 specs / 321 cases, zero overlap or missing cases.
- The final wheel build and installed-wheel smoke check passed, session `95105`,
  completion `844928`, exit 0.
- Native module ownership, relevant type/lint checks and whitespace checks passed.

This completes local gate coverage through explicit unchanged-input reuse;
**the original full invocation remains failed, and no second full was run**.
Existing dependency/tool deprecation warnings were retained, not suppressed.

## Evidence retirement

The ignored `.local/cross-shot-image-use-20261017/` directory was permanently
removed without an archive (23 files, 73,332,701 bytes; 71,660 KiB allocated).
This retired all raw logs, the final wheel, Playwright traces and four copied
failure-artifact directories. Their file hashes are omitted because the artifacts
no longer exist. The outcomes above are historical results from the original
qualification; no raw evidence remains for independent replay.

## Activation and acceptance boundary

Activate only the same installation at an idle checkpoint, preserving project,
outputs, settings and credentials; verify the current served assets/API and
readiness after normal bridge/app reload. Do not rewrite frozen jobs or rebase
their evidence. Qualification itself dispatched no real generation and selected
no owner media. Actual scene continuity remains a generation/review outcome.

Hosted CI is not established by this evidence and remains a separate gate. This
is not a performance improvement, full story walkthrough or creative acceptance.
The owner deferred audio from the current visual walkthrough scope; that is not
a claim of listening or sound approval. Python optimization, batching and the
broader Goal remain paused.
