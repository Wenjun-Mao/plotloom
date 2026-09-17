# Retained terminal-video diagnostic boundary — 2026-09-16

## Scope and result

This is the bounded follow-up to the native Chrome terminal playback failure in
the branching creative-pilot receipt. It performed no media generation,
selection, review, source-code, configuration, or provider mutation.

**Result: the required same-byte controlled comparison could not start because
the retained production runtime is no longer serving the retained project or its
media endpoint.** This is an exact unresolved boundary, not evidence that the
terminal assets decode successfully or that the branch player caused the earlier
failure.

## Prior failure being diagnosed

The retained receipt records native Chrome playing the selected opening clip to
the decision hold, then reaching each terminal node and showing native **“Unable
to play media.”** once for return and once for departure. It records no numeric
`MediaError` code, `play()` rejection, completed decision clip, standalone
terminal-player attempt, or served-build identity. Hash and `206` observations
only established stored-byte/range-route integrity.

## Runtime and byte identification

At checkout `5639a875f395f1b6e451eca273715160956aa05f` (`docs: record
branching native playback blocker`), the known checkout build is:

| File | SHA-256 | Role |
| --- | --- | --- |
| `src/plotloom/static/index.html` | `f9bd0c147d0cbef3d4c97a5aafaee1ac0b0d14e2ef7758561ec3e0746395cebe` | `/v2/` shell, references `/v2/workbench.js` |
| `src/plotloom/static/workbench.js` | `6fb8962db46215ac8b5374c6df4f70f679e8fc336f381eb7072779610d52060d` | generated frontend bundle; contains the branching player markers |
| `src/plotloom/static/workbench.css` | `035c6d1e7689f75ffe464a65293688464409d78d24d1503b2262efe8facf66ff` | generated stylesheet |

The expected production runtime route is
`http://127.0.0.1:8775/v2/`; its video contract is
`/api/v2/projects/{project_id}/video-jobs/{video_job_id}/media`.

The production bytes could **not** be compared with these checkout bytes:

- The shell environment had no listener on port `8775` and `curl` could not
  connect to that route.
- More importantly, in native Chrome itself, navigating to the retained project
  `4d7d4856-e407-4467-9432-3d9187b9edf8` rendered the cached workbench shell but
  reported: `无法加载项目 …：Failed to fetch。项目未加载；没有回退到示例。`
  The UI marked `PLOTLOOM 服务：未连接`.
- A previously loaded Chrome page is not reliable evidence of the exact served
  `workbench.js` bytes. No production static response, project response, or
  terminal media response was available to hash or inspect.

The source contract review does identify an observability gap, but not a cause:
`BranchingVideoPreview` uses the selected job's media route for both standalone
and branching playback. Its `onError` records only the frozen shot title, and
its rejected `play()` handler records only the exception message. Neither stores
`HTMLMediaElement.error.code`, `error.message`, `currentSrc`, `readyState`,
`networkState`, or the corresponding request. This explains why the previous
receipt could not distinguish a native decode/serving/player failure; it does
not establish which of those layers failed.

## Controlled comparison disposition

The approved comparison was deliberately limited to one terminal clip served
from the same production endpoint, first in a plain native `<video controls>`
page and then after the exact branch transition. A diagnostic page would have
shown passive `error`, `currentSrc`, `readyState`, and `networkState` values
without media-method overrides or synthesized events.

It was **not run**. Running it against a restarted checkout runtime, a review
copy, or any alternative endpoint would violate the same-production-bytes
condition and could falsely assign the prior production failure to the player or
asset. No diagnostic server was started because the necessary retained project
and endpoint were unavailable.

## Reproducible continuation (one or two comparisons maximum)

1. Restore or start the owner-approved retained production runtime containing
   project `4d7d4856-e407-4467-9432-3d9187b9edf8`; first record the live `/v2/`
   and `/v2/workbench.js` bytes and compare them to the table above.
2. Fetch that project's selected video-job manifest, identify one terminal job,
   and record its exact media URL. Confirm the response comes from that live
   route; do not substitute a review copy.
3. Serve an ignored, local diagnostic HTML page containing only a native
   controlled video using that exact URL plus passive event/error/current-src/
   ready-state/network-state display. In native Chrome, make one explicit play
   attempt and record the native error code/message and accessible media request
   details.
4. Reload the retained project, reach the decision through genuine playback,
   take the matching branch once, and record the same fields. Also record whether
   the decision clip reaches `ended` before the choice appears.
5. Stop after the first supported responsible layer, or after these two
   comparisons with the uncertainty stated exactly. Any correction must update
   the responsible serving/player/observability contract with regression
   coverage; do not add a retry workaround.

## Acceptance impact

Checkpoint 4 remains blocked. The selected clips, review lineage, exhausted
generation budget, and existing failure evidence are untouched. There is no
product acceptance, media-decode acceptance, full-path acceptance, or proposed
implementation in this diagnostic.

## Controlled continuation — 2026-09-17

This addendum corrects one premise of the initial boundary without changing its
historical observations. The statement that restarting the retained checkout
would violate the same-production-bytes condition was wrong for the approved
follow-up. The retained checkout, its `outputs/` project folder, and the
production static bundle are the authorized comparison target. Starting and
stopping its normal localhost server does not substitute the media bytes.

### Live identity

There was no listener on `127.0.0.1:8775`. The assigned operator started the
checkout normally with `uv run --locked plotloom`, bound to localhost, and did
not alter configuration, credentials, project state, selections, media, or
providers. The project endpoint then loaded
`4d7d4856-e407-4467-9432-3d9187b9edf8`.

The live responses and `src/plotloom/static/` matched exactly:

| Role | SHA-256 |
| --- | --- |
| `/v2/` / `src/plotloom/static/index.html` | `f9bd0c147d0cbef3d4c97a5aafaee1ac0b0d14e2ef7758561ec3e0746395cebe` |
| `/v2/workbench.js` / `src/plotloom/static/workbench.js` | `6fb8962db46215ac8b5374c6df4f70f679e8fc336f381eb7072779610d52060d` |
| `/v2/workbench.css` / `src/plotloom/static/workbench.css` | `035c6d1e7689f75ffe464a65293688464409d78d24d1503b2262efe8facf66ff` |

The selected return terminal was the one controlled subject:
`vj_d3de4bbe38af4993acad08cbba2517f5`. Its live production URL returned
`200`, `Accept-Ranges: bytes`, `video/mp4`, and `689729` bytes. The served body
and retained project asset both hash to
`2fc8c0ca52a7822859e18c06c01db2fc7bc20cfdd334142a89be89b4798107fd`.

### One terminal, two native contexts

An ignored localhost diagnostic page used only a native `<video controls>`
element with that exact production URL and passive event/property display. One
explicit native play produced `loadstart`, `loadedmetadata`, `canplay`, and
`playing`; before play it had duration `5.167`, `readyState=4`,
`networkState=1`, and no `MediaError`.

The real production workbench was then reopened in native Chrome. Its opening
clip completed, the decision clip reached the completed decision hold, and the
two canonical choices appeared. Taking **归还吊坠** moved through the genuine
branch transition to the same return job. Chrome briefly painted the native
control text “Unable to play media.” at time zero. That display alone did not
identify an error layer, so the live terminal element was read passively in
DevTools; no prototype, event, source, or media mutation was used. It reported:

```text
currentSrc: .../video-jobs/vj_d3de4bbe38af4993acad08cbba2517f5/media
currentTime: 5.167
duration: 5.167
paused: true
ended: true
readyState: 4
networkState: 1
errorCode: null
errorMessage: null
```

The matching Performance resource entry was initiated by `video`, with
`decodedBodySize=689729`, `transferSize=690029`, and `duration=28.5ms`.

### Disposition

This is one same-byte terminal comparison in two contexts, not a broad replay.
The plain player and the real return transition both reached native playback;
the branch terminal ultimately ended with no `MediaError`. The transient native
control text is preserved as an observation, but it is not evidence of a
decode, serving, or player failure. No root cause is established and no product
fix is proposed. This narrow success does not accept full-path playback,
restart, the other ending, audible review, or creative acceptance.

### Subsequent native completion — 2026-09-17

The remaining departure, restart, and project close/reopen checks were completed
later against the same retained checkout and live byte identity. The departure
terminal reached `ended=true`, `readyState=4`, and no `MediaError` despite the
same transient native control label; restart reset the player to its opening
state; normal project close/reopen preserved the four current selected video jobs
and their review-derived selections. This preserves the bounded return evidence
above rather than rewriting it as a broader replay. The full receipt is
`docs/verification/2026-09-16-branching-creative-pilot-receipt.md`; director
creative acceptance remains separate.
