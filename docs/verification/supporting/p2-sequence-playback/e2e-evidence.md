# Offline browser evidence index

The retained executable evidence is
`frontend/e2e/video-pilot.spec.ts`, test **P2 fake Wan selected pair plays in
order and survives file-SQLite restart**.

It starts an owned FastAPI server on a temporary file-SQLite database, injects
only `OfflineWanFake`, and starts the local Vite frontend. The test creates its
own project and artifacts, then deletes the temporary root on completion. It
does not read or modify retained P2 pilot storage, issue Atlas requests, or use
credentials.

The command and detailed limits are recorded in the paired receipt:
`docs/verification/2026-09-13-p2-sequence-playback-correction.md`.
