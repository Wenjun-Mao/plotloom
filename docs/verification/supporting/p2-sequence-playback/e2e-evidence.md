# Offline browser evidence index

> Historical fixture record. On 2026-09-14 the retained journey moved to the
> production `build_runtime_app` project-folder runtime with typed offline H3;
> it no longer selects Wan or uses this legacy fixture. See
> `docs/verification/2026-09-14-production-browser-parity.md` for the current
> parity mapping and verification result.

The former executable evidence was `frontend/e2e/video-pilot.spec.ts`, then
named **P2 fake Wan selected pair plays in order and survives file-SQLite
restart**.

It starts an owned FastAPI server on a temporary file-SQLite database, injects
only `OfflineWanFake`, and starts the local Vite frontend. The test creates its
own project and artifacts, then deletes the temporary root on completion. It
does not read or modify retained P2 pilot storage, issue Atlas requests, or use
credentials.

The command and detailed limits are recorded in the paired receipt:
`docs/verification/2026-09-13-p2-sequence-playback-correction.md`.
