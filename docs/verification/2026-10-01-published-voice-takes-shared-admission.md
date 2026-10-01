# Published voice takes and shared admission: specialist completion

**Result:** All four checkpoints in the [approved plan](../roadmap/2026-09-30-voice-takes-h3-plan.md)
are technically complete. This is not acting approval or Plotloom integration.
Retained branch: `codex/h3-ref2va-gateway`; planning baseline `e288623`;
qualified runtime/source `43ff815d61093b25f1c3cf957ddd76272387317f`.
Final documentation/screenshots are a separate local commit. No merge, push,
Relay execution or director message was performed. Usage/cost deltas unavailable.

## Delivered contract and requirement evidence

| Checkpoint / requirement | Authoritative evidence |
| --- | --- |
| 1 · Published identity only; frozen reference, dialogue, engine, seed and delivery | `takes.py`, `contracts.py`, `dispatch.py`; `test_takes.py` rejects corrupt references/controls and preserves admitted snapshots across catalogue changes |
| Immutable results independent of source project | Independent `takes/<takeId>/` storage; completed records refuse append; unit and browser project-deletion proofs; second live take leaves first hashes unchanged |
| Native source and eligible H3 derivative; safe deletion/failure | `media.py`, terminal/confirmation/unreleased-grant guards; ineligible native remains available; failed-publication regression removes partial output without changing identity; browser confirmed deletion |
| Preservation migration | Lab schema v4 and gateway lane migration proved on separate copies of the deployed databases; all original columns/rows remain equal; original backups retained |
| 2 · All managed producers, one durable FIFO | Atomic local media registration and Lab outbox triggers for candidate, clone and take; real SQLite `test_shared_lane.py` orders candidate/H3/clone/Qwen-image/take and skips cancelled media |
| Bound private execution, no replay or fallback | Independent control key; one-use job/hash/grant; `test_take_dispatch.py`/`test_shared_lane.py` cover disconnection, lost acknowledgement, duplicates, wrong binding, both restart orders, unreleased terminal results and deleted late registration |
| Reap before release; unknown work blocks | `engines/process.py`, worker finalization and unique active/grant indexes; process-engine timeout/stop tests; both real grants released before the next managed job |
| 3 · Authenticated facade and working Lab | Gateway create/list/status/audio/delete API with verified byte hash and separate private auth; real FastAPI/file-SQLite browser journey plus actual Spark refresh/playback/download/copy verification |
| Chinese/manual controls and immutable regeneration | Fixture journey submits Index Chinese description, copies observed strengths to a manual draft, creates a second distinct take, preserves the first and exercises guarded deletion |
| Restored voice/take/draft selection; no generation on page open | `takes_browser_journey.js` and actual deployed URL restoration with highlighted card; all final UI checks are reads, playback and copying, not generation |
| 4 · Preserved idle cutover and bounded live qualification | Exact two-Index/one-H3 accepted IDs below; frozen audio binding, FIFO and release evidence; actual idle service restart preserves databases, three voices and 60 WAVs |
| Documentation and withheld handoff | ADR 0097, Chinese client guide, pipeline/reproduction/operations documents, and updated [held integration note](2026-09-26-voice-candidate-handoff-draft.md) |

Implementation checkpoints: `18bf774`, `692c81a`, `7d3972d`; focused follow-ups
`51fdb9e`, `f426105`, `1ac588f`, `950a27e`, `43ff815`.
All work remains confined to specialist service modules, their tests and docs;
root Plotloom author/runtime/frontend implementation was not changed.

## Executed offline/package gates

| Command / scope | Result |
| --- | --- |
| Root `uv run --locked pytest -q` | **803 passed**, 129.01 s |
| Voice Lab `uv run --locked pytest -q` | **80 passed**, 10.46 s |
| `node --check` for Lab `app.js` and `takes.js` | Passed |
| Lab `uv build --wheel --out-dir dist` | Built `plotloom_voice_lab-0.2.0-py3-none-any.whl` |
| Lab `tools/smoke_installed_wheel.py` with exported locked control requirements | Isolated installation/routes/web assets/runner contracts; no Torch import; passed |
| Root `uv build --wheel --out-dir dist` + `scripts/smoke_installed_wheel.py dist` | Passed outside checkout |
| Deployed gateway image in `docker run --rm --network none` | Packaged routes/templates and CPU-only import passed, no backend calls |
| Real local FastAPI/file-SQLite browser journey | Create/publish, description/manual takes, progress, playback/download, immutable results, selection/draft reload, confirmed deletion, source-project deletion passed |
| Actual Spark UI after final service restart | Selected Take restored/highlighted; playback progressed; both WAV downloads succeeded; manual-copy fallback on insecure HTTP; zero captured page errors |

Both Python suites emit one existing Starlette/httpx deprecation warning.
Root frontend/build/E2E reruns are not applicable: those sources/static assets
are unchanged, as explicitly bounded in the approved plan. Lab browser evidence
is not a substitute for root frontend acceptance.

An attended independent review found selected-Take visual restoration and,
on narrow reopening, the real HTTP clipboard issue. Both were fixed and
regression-tested; the final review reports no material remaining issue.
The native reviewer used Luna High because Terra was unavailable in that
selector; no unattended coordinator/executor was created.

## Deployment and preservation

Only gateway/Lab control services were stopped at proven idle boundaries.
ComfyUI 0.38, Qwen-Image, embedding/comment services and all model assets remain
unchanged. Qwen-Image health/models and Lab health were rechecked; ComfyUI queue
was empty. Private control configuration is mode 0600, separate from client auth.

Final Lab release on Spark:
`/home/wjmao/services/plotloom-voice-lab/releases/2026-10-01-shared-takes-ui-43ff815/`.
Wheel SHA-256: `4e068055806fb16e1b81d4f83064b020377f317a00d1b901a41af98482ca0e60`.
The same wheel is installed `--no-deps` into the CPU API and all three qualified
engine environments. **81 pinned installed Python files** stayed identical over
the web-only replacement; the runtime manifest/dependencies/models were not
changed to accommodate the UI fix.

Gateway image SHA-256:
`39ed1ad84851572b3f36287ae37ea28a700db50edae1e86a285c64927b4ccc78`.
Previous image `4b5b5911cdd06eaa5522ff40effadf3ee8d3dcbd865dc2329c9acb6ac1ae22f9`
and exact configuration/data/source backups are retained at
`/home/wjmao/services/plotloom-voice-lab/backup-shared-takes-2026-10-01-scoped-copy/`.

The retained `migration-proofs/` copies were reopened and compared again against
the original backup: Lab projects **4**, slots **7**, generations **9**,
selections **13**, clone trials **18**, voices **3**; gateway assets **80**,
jobs **66**, frame bindings **80**, voice bindings **5**. Every original column
and row matches; new Lab tables are takes/outbox/grants, new gateway table is
the lane. No guessed content migration or reset occurred.

The initial unprivileged backup attempt could not read root-owned gateway WAVs.
Its partial directory remains retained. A scoped no-network Docker-root copy
resolved backup access without chmodding live assets or mounting models.
An initial read-only-filesystem SQLite verifier also lacked WAL/SHM bookkeeping
access; scoped writable mounts with read-only queries established preservation.
Neither diagnostic failure was treated as corruption or permission to reset.

## Exact bounded live results — no replay

Published technical MOSS identity:
`voice_5689e99835494d2f8024485523c4dbf6`. It is **not original MOSS D** and was
not substituted for it or installed into Plotloom.

| Registration order | Accepted ID | Outcome |
| --- | --- | --- |
| 1 · Index, seed 20260929 | `take_2e0e83cfb70d464dac1d63c3e683f8ff` | Completed; 4.551 s native 22,050 Hz; H3 eligible; process grant released |
| 2 · H3 Base-20, seed 20260923 | `h3_60685a23438d434fbb8399d677a1aa24` | Succeeded; 576×1024, 192 frames / 8 s, H.264 + AAC 32 kHz; 736,889 ms backend elapsed |
| 3 · Index, seed 20260930 | `take_4df0a923c00b43f4beb309022f9acafc` | Queued behind H3, then completed; 4.551 s; H3 eligible; process grant released |

First source SHA-256: `3ddb5dc2eef8a987fb1914c0546464cc13ca69a0f4e023561f34fe422b26d0ae`.
First H3 WAV SHA-256: `a780e9db30d4e57982b718d638c5eacbe4932ef867dd7465ae94ebafd20da8b2`.
Second source SHA-256: `daa020b986180abd34629206ae8fe02ff04d1b1f79ed29083708f41bcf6010f9`.
Second H3 WAV SHA-256: `2bb5851fa4593f3d18a6ebe1a2f7d776923d372d6803cb44c5eb42f412f065ad`.
Video SHA-256: `f27430e2cc862e0d059b4c1dae63060a06fb080bf3a25b42cbe69bf23f369308`.

H3 admission's audio hash and its frozen `job_voice_bindings.source_sha256`
equal the first prepared WAV hash. Both audio kinds for both takes verify;
first-take and published-identity bytes stay unchanged. Video ffprobe and full
decode passed. All three lane entries are done and both voice grants have
`release_confirmed=1`. No managed inference overlap or unknown result remains.

Two source WAVs expose `audio.possible_source_clipping`; source bytes were not
silently attenuated. Prepared derivatives use the existing documented policy.
This is visible technical evidence, not a new quality judgment or tuning task.

### Retained receipt lineage

Private receipt directory:
`/home/wjmao/services/plotloom-voice-lab/qualifications/`.

| File | Meaning / SHA-256 |
| --- | --- |
| `2026-10-01-published-takes.json` | Exactly 2 Index + 1 H3 calls; original observer wrongly rejected nonterminal `submitting`. `a7c95211e17d50b0a0f623a1ae170cc4a51ac4e0db59b657dedd63074c2b94df` |
| `2026-10-01-published-takes-observation.json` | GET-only observer interrupted during harness correction; retained as nonterminal observation, not acceptance. `4510e20f1f436164114d38bfd3272ad2c25939724c79295b630f5b5118f01688` |
| `2026-10-01-published-takes-completion.json` | Passed GET-only completion of the same accepted IDs, **0 new calls**. `50da98c00b95586325b26c8fd863ec378ca9101679c1571eed387d84274a463f` |
| `2026-10-01-published-takes-restart.json` | Passed original idle control-service restart. `4c4c6ef969d74609b87460470c65dfc3689b5863a7ef437fa9614ab95cacb19e` |
| `2026-10-01-published-takes-restart-final-ui.json` | Passed idle restart after final UI wheel replacement, **0 new calls**. `521077d0bcb30f8001a082967f89ce343f64a5358626e8397cfc3aba53d5727b` |

The observer was repaired to recognize all nonterminal video states and to
check the audio hash from admission plus frozen binding—not ordinary video
status, which intentionally does not expose it. Original failures were not
rewritten, and no generation request was repeated. The final browser harness
also corrected an unconfigured relative API URL to the actual absolute origin;
this required no product change or inference call.

The final restart compared complete SQLite rows, all **60** managed WAV hashes,
all **3** published voices, both takes/downloads and the video across restart.
Lab database state hash: `d0aa3db258d1938b35e5463187f1bae6e83d6b5e2554346d09a64154f907bf1c`;
gateway state hash: `6556348dd43918e081155ecb4552dcf041f5e6bf36d320e671feebbf51e4cc4a`.
These are canonical row-state hashes, not SQLite file-byte hashes.

Existing CPU memory traces have 148, 607 and 26 samples in separate observation
segments. Lowest sampled MemAvailable is 21,132,928 KiB; maximum within-segment
gap is about 1.016 s. Coverage is **segmented**, not an uninterrupted full-run
peak-memory record; process RSS is not GPU allocation. No CUDA retuning,
cache flushing or conclusion about the historical allocator cause follows.

## Browser evidence and stopping boundary

- [Fixture controls](supporting/voice-takes-controls-fixture-1440x900.png): fake runtime audio, not real synthesis.
- [Fixture after real service restart](supporting/voice-takes-fixture-after-restart-1440x900.png): selected card restored over the same file SQLite.
- [Real Spark queued take](supporting/voice-takes-spark-queued-1440x900.png): waiting behind the active H3 job.
- [Real Spark after final restart](supporting/voice-takes-spark-after-restart-1440x900.png): immutable completed take, visible controls/warning and restored selection.

All four retained screenshots are 1440×900 and were visually inspected.
Owned local fixture service is stopped; private browser artifacts remain outside
tracked source. Scoped secret and patch checks passed before the local receipt
commit. Models, experimental originals and published audio were not deleted.

Stop here. A caller can generate/audition a durable take and feed its verified
prepared WAV into H3. Later Plotloom character/cue binding, production copies,
currentness and approval remain director-owned, and the handoff remains withheld.
No further inference, quality comparison, director contact, merge or push is
authorized by this receipt.
