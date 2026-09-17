# Complete branching creative pilot

Status: **Approved, revision 1 — scope and new generation caps approved 2026-09-16**.
Baseline: accepted structural preview at `3d86c54`. This extends, rather than
reopens, the five-step reliable-creative-workflow plan.

## Outcome and choices

Deliver one small cinematic-realism story that can be played from its beginning
through either explicit choice to a distinct ending using real reviewed media.
Use a separate project, one character, one location, four nodes and four shots:
opening → decision → ending A or ending B. No join or stateful conditions.
Each path has three approximately five-second clips. Default to ambience without
dialogue; this does not qualify dialogue or lip-sync. Endings must visibly express
different consequences, not merely reuse the same clip under different labels.

The retained eight-unit story and its reviewed media remain untouched. Reuse its
reviewed character reference only through an existing supported import workflow;
do not copy database bindings, broaden import APIs, or weaken currentness checks.
Otherwise use one newly reviewed identity reference.

## Checkpoints

1. **Creative package, before media:** establish a valid four-node project through
   current authoring workflows. Review causality, distinct endings, shot continuity
   and frozen image/video inputs. Use the configured text backend if needed; stop
   rather than launch repeated full pipelines. Confirm supported H3 profile and
   image adaptation policy before making any media request.
2. **One complete shot first:** create/reuse the reviewed identity, generate one
   keyframe, and obtain one H3 clip through current job workflows. Review identity,
   framing and motion before committing the remaining allowance. Keep provenance
   and outputs project-local; use the image-specialist skill and staging cleanup.
3. **Finish the bounded story:** generate the remaining three keyframes/clips.
   Review each for continuity and its intended narrative consequence. Use normal
   selection workflows; do not fabricate audiovisual or human review decisions.
4. **Play both paths:** observe real start, decision hold, explicit A/B choice,
   both endings and restart in the production browser. Repeat after project reopen.
   Capture concise evidence and report creative acceptance separately from tests.

### Checkpoint 4 verification update — 2026-09-16

Native Chrome is available and the earlier browser-provider inference was wrong.
The retained project was reopened in a fresh native tab; its opening clip played to
the decision hold and exposed both canonical choices. Each choice reached its
distinct terminal node but the native player then reported **“Unable to play
media.”** The terminal clips are still selected and hash-valid, and their range
routes are readable, but that does not satisfy complete-path playback, final-hold,
restart, or durable recovery acceptance. Verification stopped after one attempt
per ending; no media, source, configuration, or selection was changed. See the
receipt for exact native observations and the bounded player/serving follow-up.

### Checkpoint 4 diagnostic boundary — 2026-09-16

The bounded follow-up first found that the retained production runtime was no
longer serving the retained project in native Chrome: it showed `Failed to fetch`
and `PLOTLOOM 服务：未连接`. The checkout build was identified, but no live static
or media response was available to establish its production-byte identity. The
prescribed single-terminal plain-player-versus-branch comparison was therefore
not run: a checkout restart, review copy, or alternate endpoint would not test
the prior same-byte production failure. Checkpoint 4 remains blocked at the
serving/runtime observability boundary. See
`docs/verification/2026-09-16-terminal-video-runtime-boundary.md` for the
recorded evidence and bounded continuation.

### Checkpoint 4 controlled continuation — 2026-09-17

The prior diagnostic's prohibition on restarting the retained checkout was
incorrect. The approved continuation started the normal localhost checkout
runtime with the retained project outputs, then proved the live shell,
workbench bundle, stylesheet, and selected return-terminal response were the
same recorded bytes. One native plain-player attempt reached `playing` with no
`MediaError`. One genuine opening → decision → return transition reached the
same terminal job and ultimately `ended=true`, `readyState=4`, and no
`MediaError`; an immediate native-control “Unable to play media.” display was
transient and did not correspond to the element's passive final error state.

This clears only the former inability to perform the same-byte comparison. It
does not establish a root cause, a product fix, complete-path/restart behavior,
the other ending, audio review, or creative acceptance. The exact bounded
receipt is `docs/verification/2026-09-16-terminal-video-runtime-boundary.md`.

## Approved execution allowance

- At most **5 ImageGen calls** total: one identity plus four keyframes. Reusing an
  identity leaves an unused call; it does not authorize another kind of work.
- At most **4 H3 submissions**, five seconds each (20 requested seconds total).
  No Atlas calls, paid fallback or backend/configuration changes.
- Failed calls consume the cap. No automatic resubmission of unknown outcomes.
- These are new caps, separate from the exhausted Step 4 allowance.

## Delivery and acceptance boundaries

After approval, use one Relay Terra-high coordinator and serial source ownership.
Director handles routine review; request user input only for a consequential
choice, an exhausted cap, or genuinely unobservable audiovisual judgment.
Permit a small demonstrated integration fix only after a minimal reproduction;
stop after two failures at the same criterion and propose a method change.

No new player architecture, stitching/export, editing suite, compatibility layer,
generic cleanup framework, broad refactor, new snapshot proof or new backend.
The earlier intermittent native pause remains unexplained; capture native events
if it recurs, and do not equate readiness or synthetic events with real playback.

Accept only with all four clips current and selected, both paths genuinely played,
distinct coherent endings, and an honest audiovisual-review record. If audio cannot
be heard by the reviewer, request the user's review once with accessible clips.
Run focused checks for any code change and broader gates only on a stable change.
Record exact revision, output location, calls consumed and remaining gaps in one
receipt. Push verified source/docs after director acceptance; never commit media,
keys or endpoint configuration. No Alpha or general creative-quality claim.
