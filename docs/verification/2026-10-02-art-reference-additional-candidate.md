# Additional art-reference candidate verification

Date: 2026-10-02. Baseline: `7b06fec`. Contract: ADR 0097.

## Diagnosis and scope

The UI used `current && state !== cancelled` both to protect a frozen request
and to decide whether any preparation was allowed. Delivered images therefore
blocked another candidate. Persistence already owns multiple independent
proposals; no image/job schema or generation contract needed changing.

Current delivered scene/prop tasks now expose **修改要求，再生成一张**. It seeds
a separate local draft, preserving immutable old requests, images and selections.
**准备新图片任务** creates a new proposal; Send remains explicit. This is new
generation from complete requirements, not image editing against the old image.

## Executed checks

- Focused component tests: **25 passed**. Covers initial requirements, frozen
  requests, new preparation/send identity, local edit cancellation, blank/error
  handling, subject isolation, accepted-session reset and pending/readonly gates.
- Full frontend suite: **286 passed**. TypeScript and E2E type checks passed.
- Art-storage/API tests: **25 passed**, including a new isolated regression that
  chooses the first candidate, prepares/delivers a second, reopens storage and
  compares the first request/package/delivery bytes, entire accepted-art state and
  reference choices exactly. Both candidates remain current and distinct.
- Existing art browser suite: **9 passed**, including comparison, reference
  decisions, lifecycle persistence and held-response project ownership.
- Deterministic assets rebuilt; scoped Ruff and `git diff --check` passed.
- Independent read-only review found no actionable findings and separately ran
  the 25 focused component tests and TypeScript check successfully. This review
  completed under inherited settings before the user's subsequent Relay model
  policy instruction; it is not represented as a Luna/Max run.

Existing warnings: Starlette/httpx TestClient deprecation and Vite chunk size.

## Browser and runtime check

Used a separate Playwright CLI browser against the existing local project. Opened
P01's revision form, edited a clearly marked test-only local draft, captured and
visually inspected the form, then cancelled the edit and closed that browser.
The previous frozen requirements and original image remained visible. Screenshot:
`output/playwright/art-reference-revision-draft.png` (ignored local evidence).

No POST/PUT/PATCH/DELETE requests occurred during that check. Exact before/after
API snapshots of accepted art, all proposals, reference decisions and specialist
state were equal. No real task was prepared/sent, image generated/selected,
reservation cleared or accepted art reopened. The report iframe emitted its
existing expected sandbox script-blocking message; its permissions were unchanged.

The Docker service serves the rebuilt frontend through its existing read-only
checkout mount; no server/bridge restart was required. HTTP-served and on-disk
bundle SHA-256 match:
`be173bab02993f983cd780a6b83dbe5e5504d8f1c049564e9769432d342e0f10`.

## Acceptance boundary

The technical UI/storage checks pass; a new real image and the creator's judgment
of it are not claimed. Next creator action: reload Plotloom, open P01, choose
**修改要求，再生成一张**, revise the full requirements, prepare, then explicitly
send if ready. Old/new candidates remain available for comparison and choice.
