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
