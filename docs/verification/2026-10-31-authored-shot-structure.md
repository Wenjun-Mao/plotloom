# Authored shot structure and retained video authority

The original Last Projection project's final seven-target batch was rejected
before any H3 submission: the trusted prefix demanded a continuous shot while
E03's authored action allowed a fragment insert. The translated direction retained
the permission correctly. ADR 0224 now clarifies that source owns shot structure.
The active H3 prefix, ending-frame wording and bilingual production brief defer
to authored action and continuity. The field schema, reference treatment, exact
words, timing, settings, provider and budget contracts are unchanged.

Retained request admission validates the frozen brief's source, shape and hashes
and the original native check's complete pre-check manifest commitment. It does
not recompile old prompts or regenerate historical brief prose. Only generated
targets' trusted post-check projections are removed when checking that commitment;
inherited references remain exact. Adopted targets must match the owner's brief.
Current compilation remains mandatory for new admission and is rechecked inside
the atomic prepared-to-dispatching transaction. Compiler drift marks generation
stale while an already ingested selected clip can remain playable under the
existing passive-selection policy. Known prediction observation precedes new
submission validation; no retry, replay or reservation-clearing path was added.

## Evidence

Qualified runtime code: `e0f00881`; test-only closure checkpoint: `3e23eec5`.
See the [final receipt](2026-10-31-last-projection-functional-closeout.md) for
composite qualification, final production, activation and recovery.

- The old runtime's supported original-project snapshot contains three retained
  batches, fifteen selected keyframes and eight selected real H3 clips. Before
  the boundary fix, current admission reproduced `batch compiled prompt changed`.
  After the fix, all three retained batches pass read-only admission. A supported
  restore into an isolated disposable root, second snapshot, close and reopening
  preserve all eight playback SHA-256 values. Original data was not mutated and
  no provider call occurred. Evidence:
  `.local/last-projection-resume/frozen-original-restore-readback.json`.
- Focused authority, fidelity, retained preview and recovery: 35 passed in
  `frozen-video-owner-binding-closure.log`. Earlier failing attempts are retained.
- The broader final-request, whole-pack selection and replacement selection passed
  47 cases (`frozen-video-regressions.log`), including the mixed adopted/generated
  target contract.
- All eight new frozen-authority regressions pass, including batch-managed known
  prediction reconciliation after compiler drift (`frozen-video-authority-final.log`).
  New regression coverage exercises decoded six-clip selection, compiler/brief
  drift, stale generation versus exact retained playback, portable restore and
  reopening; native manifest/brief/source/prompt/capacity/candidate tampering;
  and known-prediction batch reconciliation without resubmission.
- Quick gate: 1,704 frontend cases, both type checks passed. Packaged validation
  resources match all 21 source files. Scoped Ruff F and whitespace checks pass.
- Independent read-only review found the authority/compilation boundary sound
  after two concrete binding repairs. Focused/full results remain separate.

The 435-line project-video facade gains one transactional call to the existing
new-dispatch authority owner; no new responsibility or extraction was warranted.
Frozen brief validation is a separate cohesive module. No frontend sources changed.

The full `e0f00881` invocation failed two retired QA fixture expectations after
5,077 Python passes. The test-only `3e23eec5` repair and seven focused cases close
those failures while retaining separate profile/budget scope-guard coverage.
Every declared downstream full step passed, including all 366 browser cases and
exact-wheel smoke. This is composite qualification, not a relabelled full pass.
The final seven targets passed genuine new exact-request fidelity checking and
were generated/selected; all 15 clips now export and play through all three routes.
Normal activation, exact export and refreshed recovery passed. The earlier
`765e4ea5` full pass remains historical. No hosted CI or quality judgment occurred.
