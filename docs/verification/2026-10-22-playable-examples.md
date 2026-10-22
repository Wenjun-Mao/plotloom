# Three genuinely branching examples · 2026-10-22

Status: three live playable examples delivered under delegated agent QA; all
six browser routes verified. Owner creative acceptance remains separate.

## Outcome, cause and boundary

The owner accepted the appearance of the three finished examples but requested
a few actually playable ones. Their zero-choice, one-ending authored graphs
were linear; the existing player already supports branching. Create three new
projects rather than change the originals or add player behavior.

The small real journey is opening → one route-only choice → either of two
distinct endings → restart → the other ending. Each project has four nodes,
three locked three-second shots and two six-second routes. The choice has no
scene, beat, shot or dialogue. Use the existing owner H3 quality-8 portrait
576×1024 profile, native audio and explicit `cover_center_crop`. Prospective
aggregate caps remain null; the finite deliverable is three completed projects.
The manager owns generation, actual media inspection, selection and all six
browser routes. This is delegated agent QA, not personal owner review or
creative acceptance.

| Project | Identity | Endings |
| --- | --- | --- |
| 小舟去哪儿（水彩） | `7304da14-c3aa-40aa-9b5b-236d6979ac25` | Warm open water / cool lotus shade |
| 这一杯的片刻（电影写实） | `7690e55d-3f08-4056-8f7b-8455814c4928` | Warm cup rim / cool rain window |
| 灯光照向哪儿（风格化3D） | `02a9c60d-9b37-46fd-9446-806cb0aa8a1f` | Sea beacon / illuminated shore steps |

Six owned ImageGen originals are reimported unchanged with truthful reused-art
provenance. Three new B-ending originals were generated with built-in ImageGen,
each using its style's original SH02 image as the sole reference. The actual
[prompt/file record](../../.local/playable-examples-20261022/image-generation.md)
distinguishes those calls from the author's two-reference prompt proposals.
All nine video clips must be fresh: the supported import accepts images, not
cross-project selected video/job/approval records. No media files or database
rows are copied to bypass provenance or currentness.

## Source and focused verification

`e74a3e86fb8ee3ccd3a775064a34b4c92b44afd0` adds only three exact source-owned
QA scopes, their regression tests and the narrow
[ADR 0198 addition](../adr/0198-delegated-disposable-qa-authority.md).
The five previous scope dataclasses match `d168ce60` exactly, including the
initial finite grant and native bundle/reference identities. The new grants
freeze actual project receipts, storyboard hashes and all nine imported
shot/asset/original-hash pairs. No public enrollment, matching, admission,
provider, API, UI, dependency or dispatch contract changes.

One worker owned focused verification; an independent reviewer inspected the
stable diff and all project/import receipts and found no actionable issue.
The manager also inspected the diff and receipt identities.

```sh
uv run --locked --no-sync python scripts/verify.py focused \
  --pytest tests/test_finished_example_qa_scopes.py \
  --pytest tests/test_delegated_qa.py \
  --pytest tests/test_native_material_qa.py \
  --pytest tests/test_provider_budgets.py
```

186 passed. After test import sorting, the changed-file focused selection passed
38 tests. Direct baseline dataclass comparison, changed-test Ruff and
`git diff --check` passed. Ruff over both Python files also reported an existing
import-order issue in an unchanged native-handoff block of `delegated_qa.py`;
that unrelated warning remains. This fixture-only addition uses scoped checks,
not a new full-release qualification. Historical failed full runs retain their
existing status. GitHub CI was neither requested nor run; no push is authorized
for this new assignment.

## Exact runtime activation

Installed P was clean at `b21505a0`, with no active native attempts, enabled
queue or validator. Product, frontend, dependencies and creator-service source
were unchanged from that installed revision through `d168ce60`; the executable
addition is the three immutable grant entries. Supported stop → detached
checkout `e74a3e86` → start recreated healthy container `cd2edcb105d8`;
the unchanged owned bridge remained PID 66847. No specialist gateway/Voice Lab
service was activated by the source checkout update.

The [before](../../.local/playable-examples-20261022/before-grant-activation.json)
and [after](../../.local/playable-examples-20261022/after-grant-activation.json)
activation fingerprints are exactly equal for all seven projects, protected
settings, accounting and host tables, including historical UNKNOWN records.
The trusted operator then verified each exact newly created original home and
bound its scope inside the actual container's path/stat view; the
[grant receipt](../../.local/playable-examples-20261022/runtime-grants.jsonl)
records successful eligible QA context for precisely those three projects.

## Live media and playback

The cinematic project is approved under delegated agent QA. All 216 proposed
window frames and the three full-source overviews were inspected. The cup,
handle, cream rim and table remain recognizable; more pronounced warm steam
than the still image is an explicitly accepted demo variation. The cool rain
ending is visibly distinct, with stable cup framing and window droplets.
All three native AAC tracks and three-second derivatives decode, with 96,000
audio sample frames per window, zero NaN/Inf and no clipping. Audio review is
technical signal/spectrum inspection only: no listening or perceptual
speech/music certification is claimed.

The actual browser journey hid choices during the opening, naturally reached
the two-button decision, played each different ending to its natural end, and
reset time/history on restart. Both ending videos reported three seconds,
576×1024, unmuted, no media error and distinct source URLs. The
[route receipt](../../.local/playable-examples-20261022/cinematic-browser-routes.json),
[choice screenshot](../../.local/playable-examples-20261022/cinematic-browser-choice.jpg)
and two ending screenshots retain the observations. Creation, healthy startup
and visible controls alone are not playback acceptance.

The clay lighthouse project is also approved under delegated agent QA. All
216 window frames, three source overviews and audio spectra were inspected;
the lighthouse/rocks, fixed camera and clay palette remain stable. The shore
beam spreads broadly across the tower base and existing steps, an accepted
authored lighting variation rather than exact physical beam optics. The same
decode/sample/signal-only audio checks passed; no listening is claimed. Both
natural browser routes and restart passed with distinct current SH02/SH03
sources, three-second ends, no media error and no premature choice. Its
[route receipt](../../.local/playable-examples-20261022/stylized3d-browser-routes.json)
and [choice screenshot](../../.local/playable-examples-20261022/stylized3d-browser-choice.jpg)
retain those actual observations.

The initial watercolor SH03 was rejected after its full 72-frame window and raw
H3 source showed a substantial unwanted pigment/illumination wash-out. This is
visible before application cropping or playback, so no downstream pixel,
duration or player change is an appropriate repair. The internal model cause
is unknown. The [root-cause/evidence note](../../.local/playable-examples-20261022/watercolor-rejected-sh03.md)
and initial media are retained. Supported settled predecessor cancellation and
explicit rejected-take succession keep the two good SH01/SH02 jobs and segments
unchanged. The first replacement clarified the author's existing constant
lighting/pigment intent through reviewed English directions, with the same
original, scope, canonical story, profile, crop and native audio. It did not pass;
the rejected take is not relabeled as passing.

The replacement also failed the same visual criterion. A separate read-only
audit measured raw-source luma increasing from 142.6 to 223.2 over the selected
window, while the two good sources stayed near their opening values. The
[diagnostic note](../../.local/playable-examples-20261022/watercolor-fade-diagnosis.md)
records saturation changes, source hashes and layer exclusions. It does not
identify prompt conditioning versus model/sampler/VAE behavior. Repeated
negative concepts in the single conditioning channel are only a hypothesis;
each native replacement also gets a new random seed, and the current batch
contract offers no rejected-seed override. No seed feature or bypass was added.

After that reassessment, a final concise affirmative input-package trial
was dispatched with the same original, canonical intent and profile. It is not
an isolated wording comparison. Actual inspection of every current 72-frame
window and the new raw-source overview passed. The new SH03 retains the paper
boat, lotus canopy, cool pigment and small ripples without wash-out. Raw-source
luma at frames 0 and 71 is 142.405 → 139.193; saturation is 13.4046 → 13.9157.
The successful new-seed input package does not prove a wording-only cause or
repair the model. No downstream pixels, duration or player behavior were changed.
Both earlier failed takes and frozen rejection hashes remain intact; the two
good original jobs/segments remain exactly unchanged.

The third watercolor pack is approved under delegated QA, with the same
technical-only native-audio limits. Both actual natural browser routes and
restart passed, including the selected new SH03, no media errors and no early
choices. Its [route receipt](../../.local/playable-examples-20261022/watercolor-browser-routes.json)
and [choice screenshot](../../.local/playable-examples-20261022/watercolor-browser-choice.jpg)
retain the final observations. An initial confirmation request was refused
before selection because its 18 evidence references exceeded the existing
16-reference limit. The corrected request references the retained manifest
instead of separately repeating two source-audio references; the operator now
validates the complete native request model locally. All evidence files and the
existing contract limit remain intact. The
[422 note](../../.local/playable-examples-20261022/watercolor-confirmation-request-422.md)
records this operator-input error, not a product failure or provider retry.

## Final playback and preservation

| Playable example | Actual ending routes | Current approved batch |
| --- | --- | --- |
| [Watercolor boat](https://plotloom.tail6040ad.ts.net/v2/?project=7304da14-c3aa-40aa-9b5b-236d6979ac25&view=play) | Warm water / cool lotus shade | `03d8d6b2-a884-4419-9988-422e0957d998` |
| [Cinematic cup](https://plotloom.tail6040ad.ts.net/v2/?project=7690e55d-3f08-4056-8f7b-8455814c4928&view=play) | Warm cup rim / cool rain window | `94acd17e-e1a4-4372-819f-05cca8ffa26b` |
| [Clay lighthouse](https://plotloom.tail6040ad.ts.net/v2/?project=02a9c60d-9b37-46fd-9446-806cb0aa8a1f&view=play) | Sea beacon / illuminated shore steps | `9e123463-4af1-4b69-8b99-76078e41b826` |

Read-only [closeout assertions](../../.local/playable-examples-20261022/closeout.py)
passed against actual native readback, the three browser receipts, the
[before](../../.local/playable-examples-20261022/before-task-state.json) and
[final](../../.local/playable-examples-20261022/final-task-state.json) snapshots.
They bind each browser ending to the current selected SH02/SH03 job and N03/N04
node, verify every retained job's exact H3 adapter/profile/request, all nine
selected three-second segments and 96,000 audio sample frames, and preserve both
watercolor rejection histories and unchanged good clips. The independent
Luna/Max reviewer found and re-reviewed the corrected route/profile assertions;
final execution then passed. No pending output is inferred from the review.

All four pre-existing project records, table digests, retained-file hashes,
modes and owners match their before-state exactly. Protected settings/files,
host tables, both historical UNKNOWN attempt IDs and all pre-existing
application rows also match exactly. Only create/grant records belonging to the
three exact new projects and the eleven exact task dispatch identities are
excluded when comparing old application rows. The catalog contains exactly the original four
plus these three projects. No enabled queue, validator or active host attempt
remains. The installed checkout is clean at `e74a3e86`; its container is running
and healthy. This checkout assertion and historical activation evidence are
separate from a new byte-for-byte runtime certification.

The [closeout result](../../.local/playable-examples-20261022/playable-examples-closeout.json)
records three fresh built-in ImageGen originals, six reused originals, eleven
H3 jobs / 55 requested seconds including both rejected takes, and nine selected
clips / 27 unique playback seconds. Each of the six routes lasts six seconds
because its opening is shared with the alternate route. Monetary cost and a
precise work/wait/coordination timing breakdown are unavailable. The live journey
started at 22:07 UTC and reached closeout at 23:37 UTC, with substantial serial
provider-generation waits. There was no new
full-release run, CI, push, specialist service activation or owner creative
acceptance. The scoped source and documentation are retained locally on main;
the final documentation-only checkpoint needs no runtime restart.
