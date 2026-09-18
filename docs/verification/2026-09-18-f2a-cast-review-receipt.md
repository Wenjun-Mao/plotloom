# F2A source-bound cast review receipt

Date: 2026-09-18. Scope: candidate-only character proposal review and explicit
accepted cast persistence. This is technical workflow evidence, not human
creative acceptance, media production, or voice-consistency proof.

## Delivered

- The F0 frozen handoff exchange now carries a `characters` package with the
  accepted source, upstream outline, and F1B section map as explicit inputs.
- A project-owned cast owner freezes source/outline/section-map and installed graph
  hashes, revisions, and stable section IDs from one transaction snapshot; it admits only current, pinned-specialist
  deliveries, supports cancellation, rejects late/stale delivery, and makes
  prepared external publication visible to project lifecycle controls.
- Explicit acceptance saves one immutable upstream-shaped `cast.json` revision
  and a reviewable mapping from cast IDs to the existing character-reference/
  media consumer namespace. It does not require old Bible generation and does
  not create image, reference, selection, or generated-voice claims.
- The production surface adds ordinary proposal review for per-character
  motivation, appearance, and voice direction, raw JSON inspection, sandboxed
  report viewing, copy/refresh/cancel/accept/reopen actions, and stale-context
  messaging.

## F2B seam

F2B must bind the explicit consumer-ID mapping to the existing selected
character-reference and media paths, then qualify two distinct image poses with
an attended identity review. It must not treat this text-only proposal as image
or voice evidence.

## 2026-09-17 Toronto live specialist/browser proof

This addendum records one isolated, disposable production-app exercise. It is
technical workflow evidence only: nobody made a human creative decision about
the material, no image or audio was generated, and no character identity or
voice consistency was qualified.

### Isolated live project and retained F1A boundary

- Project: `4cdbe9c5-dc47-4365-98a3-7ba022433556` (`潮汐灯：一盏旧航标的选择`).
- Runtime: the source-checkout production entrypoint with both application data
  and outputs under
  `.local/relay/fa9d3aa6-9039-4c02-ab16-e30e0a380943/live-proof/`.
  The app was stopped, started again with the same isolated directories, and
  the browser then loaded the project successfully.
- The requested retained F1A directory rejected both supported restore and
  current-project opening because its database schema predates the current
  video-candidate selection schema. The source directory was preserved. Its
  source material was read only, then re-entered through the live source UI;
  no project database was copied, edited, or used as an import workaround.
  This is an evidence limitation, not a claim that the historical project was
  restored by the current app.
- Current source: r1,
  `fb79cb40b0c89f71da206d44bad3421c9d44d5c7ad3d7206dc6568f1e985fe27`.
  Accepted outline: r1,
  `f0eb0d58ba7c8e3bdca07eef1a0d7f1444c104f0e61c1ee1b72f0c1f5b1f22db`.

### F1B graph exercised through the UI

The live authoring surface saved a three-section map and installed its current
route graph: `opening` branches by `turn` to `ending-a` (`path-a`) and
`ending-b` (`path-b`). The API after the restart reported section-map r1,
`49381b1ea9f88766f91a1b21e9732b82da9b09a346300db72530d52099d30bea`, and
current graph admission r1,
`975a70a0f171db7f3a92620a4b0c9b63dc625d1ed298de0fd43cbe233baab8cb`.

### Attended package and F2A lifecycle

- The outline delivery was reissued from the retained, read-only F1A evidence
  into the current UI-prepared job `ch_f8e25b53d21046d59533a5b39fb8e11c`.
  Its `outline.json` and `report.html` hashes are respectively
  `7c9879965b0352decd208d3e84acb3f3ae67aa8f910253d8ba0752c6dd7319de` and
  `1d721ceeea2e2b828f35f1d41d49168e98b756d9a96a44774c638b7c418f66cd`.
  The pinned `novel-outline` validator passed.
- The cast package was prepared from the accepted source, outline, and section
  map. Its completion metadata declares `gpt-5.6-terra` at high reasoning;
  it is a package provenance assertion, not independent provider telemetry.
  The first UI admission (`ch_f99ca1ed7fc6405e9414e5a0a7e44cc2`) correctly
  rejected the otherwise upstream-valid cast because the receiving contract
  requires stable character IDs. It was cancelled through the UI, retained as
  evidence, and never accepted.
- A replacement handoff, `ch_f506620de33a49b7a9ec38a4c6bed23c`, supplied the
  same two source-bound characters with stable IDs `C01` and `C02`. Its
  `cast.json`, `report.html`, and `completion.json` hashes are respectively
  `d76435e71a26cf62509a7ef2e244020d83f1e07b9df2693154cc6f43a59e0533`,
  `e374acb0fc97a7946f434dab4c2659d6578a46180d95961576bfc43683cd891a`, and
  `4563652668ed34b59c6212143b28f38ef1c4e84df76b9e7743733e596e2a3fc1`.
  The pinned `novel-characters` validator passed before the UI refresh.
- In the browser, C01's motivation, appearance direction, and voice direction
  were separately inspected and edited; the proposal was explicitly
  technically accepted as r1, reopened, its voice direction edited again, and
  saved as accepted r2. After browser reload and a clean runtime restart, the
  app/API still reported accepted r2,
  `f1a43e3ce3d47bc0f76d8258df2aab1320a3fc461fd453fb25022dd21e7716d5`,
  from the replacement job, with `C01 -> C01` and `C02 -> C02` consumer
  mappings. The persisted C01 voice direction includes the reopen marker;
  motivation and appearance live in the character persona where they were
  edited.

### Evidence and checks

- Full-page post-restart screenshot:
  `.local/relay/fa9d3aa6-9039-4c02-ab16-e30e0a380943/live-proof/f2a-after-restart.png`
  (`sha256:4c5948c302b86f3595e5e6820bfa8c3bedca0506e66118862f52ae5855138042`).
  It visibly contains the current F1B graph and `已接受 r2` F2A status.
- During the browser exercise, sandboxed report scripts were blocked and the
  cancelled first cast refresh returned its contractual 422. Those observations
  explain the browser console messages, but the console transcript is not a
  retained standalone execution artifact.
- Focused verification: pinned upstream outline validation passed; pinned
  upstream character validation passed for the replacement; production UI/API
  state was checked after reload and after restart. No source code changed, so
  no test suite or frontend rebuild was warranted for this evidence-only run.

### Remaining boundary

This proof does not establish a fresh externally witnessed Terra invocation,
human creative acceptance, identity reference, voice consistency, media output,
or F2B. The completion file's provider/reasoning declaration is retained for
audit but must not be upgraded into any of those claims without independent
provider evidence and the required attended reviews.

## Independent read-only review

An independent Terra high-reasoning read-only review checked the live output,
project persistence, receipt hashes, screenshot, and tracker update before
this record was committed. It found no blocking contradiction: the cancelled
job has no admitted cast, the replacement is the sole source of accepted r1/r2,
the r1-to-r2 delta is the stated C01 voice reopen marker, and the replacement
remains bound to the accepted source/outline/map/graph hashes. It also confirmed
that the restart log records only server startup and `GET /v2/`; the post-restart
state claim is supported by the screenshot and persisted database rather than a
separate captured API response. Validator and provider fields remain provenance
assertions, not external telemetry.
