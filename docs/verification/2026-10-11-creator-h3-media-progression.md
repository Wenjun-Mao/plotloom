# Creator H3 deployment and installed-shot progression

## Root causes and contract

The live owner walkthrough installed nine shots but could not prepare H3:
the persistent server's composition supplied no video provider/adapter. Fix
the deployment composition with explicit protected-file opt-in, default off,
sanitized local validation and Compose secret delivery. Do not export credentials
into subprocess environments or project/public settings. ADR 0095 records the
runtime boundary; neither opt-in nor health checks dispatch generation.

The guide also inferred playback readiness from formal storyboard installation.
Observe existing media/video owners, invalidate on project/revision/entity
changes, and gate both playback text and action on all current formal stages
and duration-matched selected clips for every derived route. ADR 0155 records
this advisory contract. No provider payload, admission or media acceptance is
changed by the guide.

## Executed development verification

- Direct native tests: 67 passed for creator runtime, manager, declared service
  boundaries and H3 transport.
- Focused runner: 31 Python, 61 Vitest and both video-pilot browser journeys
  passed in 34.000s before the review-driven revision-refresh delta.
- Quick: 1,224 frontend unit cases and both type checks passed in 13.082s.
- Review-driven focused delta: 83 unit cases passed, plus frontend type check.
- Native ownership: 1,542 Python / 158 files; 1,225 Vitest / 149 files;
  294 Playwright / 89 specs, complete owner union.
- Real Docker one-off secret probe: regular file, runtime UID matches owner,
  owner-only permissions and readable. No secret contents or network request.
- Independent H3 configuration review found no blocking issue; it required the
  Docker UID probe above. Independent media-guidance review identified stale
  formal stages, an empty-shot selector and retained approval IDs; these were
  corrected at their shared readiness boundaries. Final review found no blocker.
- Final focused advisory delta: 12 unit cases and both video-pilot browser
  journeys passed in 29.940s; current-approval and revision refresh regressions
  are included. The prior five affected browser journeys also passed (29.433s).

## Final software qualification and activation

Exact source `d59bcdab17af8f4850b082cf832ad12537946583` was committed and
pushed before owner media dispatch. The local command
`uv run --locked --no-sync python scripts/verify.py full` passed with
`VERIFY_SUMMARY tier=full elapsed_seconds=721.842 exit_code=0`:

- 1,542 Python cases / 158 files, two disjoint workers of 771 cases each.
- 1,226 Vitest cases / 149 files and both type checks.
- 294 unfiltered Playwright cases / 89 specs.
- Lock, API lint, archived reader, deterministic build/parity, native ownership,
  four-shard allocation and installed-wheel smoke all passed.

Unfiltered [hosted run 38146928907](https://github.com/Wenjun-Mao/plotloom/actions/runs/38146928907)
passed on that exact SHA. The manager independently read back success for
`verify` and all four browser jobs. The run interval was
14:22:43Z–14:40:57Z on October 11 (18m14s); browser shards passed 83/70/70/71
cases without gaps or overlap. This is exact-revision qualification, not a
controlled claim that every machine or subsequent revision is faster.

Activated the reviewed opt-in through
`uv run --locked --no-sync python services/creator_workbench/manage.py start --h3-config /Users/wjmao/projects/HU/plotloom/.env`.
Only the creator workbench was recreated; normal8841 was healthy, the configured
Codex bridge remained available, and the private H3 v7 catalog was admitted.
Credential contents were not printed, exported or changed. Activation did not
dispatch a video; subsequent requests used the normal explicit preview/submit
and review workflow.

## Real owner-media evidence

The walkthrough subsequently completed nine selected 60-frame playback clips
from 13 H3 originals. Four wrong-action originals were explicitly rejected and
preserved, not accepted merely because output validation passed. Three matching
endpoint-image refinements enabled successful subsequent pickup, hand-withdrawal
and turn-away candidates. This observation is not proof of prompt causality or
a general H3 quality guarantee.

All admitted originals were quality 8, 832×480, requested for five seconds and
measured at 124 frames / 24fps (5.167s), with native AAC audio. All selected
clips were explicitly prepared at frames 0–60 and played through at 2.5s.
The actual interactive player then exercised both mutually exclusive endings,
waiting at the route-only choice and stopping at each terminal ending. Film
durations are 17.5s and 15s, excluding viewer decision time; neither padding to
30s nor adding both endings is implied.

See the [owner walkthrough receipt](2026-10-11-lamp-owner-walkthrough.md) for
media identities, rejection evidence, player screenshots and quality limits.
These final receipt edits are documentation-only; the CI evidence remains
pinned to `d59bcda`, not to a later documentation commit.
