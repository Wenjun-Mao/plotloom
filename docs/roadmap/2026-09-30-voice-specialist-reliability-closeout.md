# Voice specialist reliability and handoff closeout

Owner authority: “Go ahead and tackle 1–4”, 2026-09-30, after ComfyUI 0.38
maintenance adoption (`ef7716f`). Director contact, Plotloom changes, merge and
push remain withheld. One source/runtime owner; existing assets stay preserved.

## Ordered deliverables

1. Repeat the old failed Qwen-reference → Index neutral path without pausing
   another service. Pin reference, words, seed and semantic settings. Capture
   resident/cold state and memory; never claim a restarted Comfy process holds
   the same cached models as the old failed run.
2. Settle the shared resource policy from that evidence and a post-H3 test.
   One Lab child does not exclude gateway dispatch; host MemAvailable does not
   guarantee CUDA context allocation. Do not add hidden OOM replay, cache flush,
   broad service stopping or model fallback. A policy change must have a named
   contract and focused lifecycle/concurrency tests before deployment.
3. Verify the full working workflow: paired Qwen/MOSS creation, independent
   regeneration, all four neutral creator/reuse paths, Index Chinese/manual
   controls, explicit publication, refresh/project isolation/restart, and one
   gateway Ref2VA submission consuming the exact published reference bytes.
   Existing creative findings are retained; valid audio/video is not new human
   naturalness, acting or lip-sync approval.
4. Finish the held specialist handoff package: exact APIs, identities, byte/hash
   ownership, runtime/deployment/recovery, limitations and Plotloom-side tasks.
   No director message or product integration is performed.

## Bounded real calls

Initial allowance: two exact neutral Index probes (cold-engine and post-H3),
plus the existing nine-call workflow (three creation/six reuse), and one H3
image-and-voice job. No other generation, seed sweep or automatic replay. Each
operator invocation uses a new immutable receipt, persists sole-POST intent and
stops on ambiguity. The previous receipts and failure remain unchanged.

Reassess after two failures of the same criterion; do not exhaust a batch while
its prerequisite is failing. A demonstrated resource-policy repair can justify
a separately documented bounded verification under this closeout, not an
unbounded search. Unrelated queued work must finish without preemption.

## Evidence and completion

Use locked service tests, JavaScript checks, actual FastAPI/file-SQLite browser
journeys, wheel/install smoke and affected gateway tests if changed. Capture a
secret-free receipt and privately retained runtime evidence, released child
processes, old Voice ID/file preservation and final service readiness. Keep cold,
warm-resident and controlled-release observations distinct. Finish only when all
four deliverables are demonstrated; leave unresolved limits explicit in handoff.

## Closeout disposition

All four deliverables are technically complete; see the
[executed receipt](../verification/2026-09-30-voice-specialist-reliability-closeout.md).
Cold and post-H3 Index probes passed with Qwen-Image running; the fresh nine-call
matrix and sole published-byte H3 job passed; browser/idle restart checks
preserved state and 54 WAVs. Resource policy remains on-demand processes and
operator-serial windows, with no hidden retry/stop/cache change. Atomic receipt
claims close the independent review's tooling race.

This does not diagnose away the old allocation incident, guarantee multi-client
concurrency, or grant creative acceptance. The held handoff package is updated;
Plotloom integration, director contact, merge and push are still withheld.
