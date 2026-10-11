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

Final cross-runtime local full, hosted exact-SHA evidence, runtime activation
and actual owner video/playback acceptance remain separate pending checkpoints.
