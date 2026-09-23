# Production-bridge live intent trial on the retained U4 lighthouse

## Boundary and retained copies

This was one bounded text-generation trial against an isolated copy of the
retained U4 project `暴风灯塔` (`fbb913c8-534b-4439-ba68-211e70ec743d`).
The accepted F1–F5 source chain is recorded in
[`2026-09-22-u4-lighthouse-walkthrough.md`](2026-09-22-u4-lighthouse-walkthrough.md).
The original `.local/relay/u4-lighthouse-walkthrough/` project, its accepted
revisions, and the earlier fake-preview evidence were not edited. No media
generation, canonical confirmation, user creative acceptance, or push was in
scope. The allowance was at most two provider completions, with a second only
after a diagnosed definite failure; this trial used **one**.

The public snapshot API created snapshot
`b267032e-1290-4819-859e-bb8e94dfc0ab` from the original. Its U4-era
project schema could not be restored by the current runtime directly, so the
supported restore method from the U4 code revision `a869e7c` restored two
separate copies. Current code then opened/migrated only those copies:

| Copy | Purpose | Local service |
| --- | --- | --- |
| `.local/relay/bridge-intent-live-u4-trial/` | Deliberate changed-Brief failure evidence | `127.0.0.1:8820` |
| `.local/relay/bridge-intent-live-u4-source-trial/` | Original-Brief live inference and review | `127.0.0.1:8821` |

The first copy prepared a 3-scene, 27-cut, 57-target proposal and then changed
only its Brief shot maximum from 4 to 9. The bridge immediately became stale
because the current project update invalidates the accepted graph and its
downstream F2–F5 chain on any Brief change. This was a *pre-dispatch* guard,
not a provider failure. The copy remains as evidence. No selective
invalidation/runtime semantics were changed and no F1–F5 handoffs were rerun.
The original-Brief copy retained the 2–4 shot rule and current accepted F4
script r2/F5 review r2, so it was used for the authorized inference.

## One real provider completion

The fresh copy prepared proposal r1, hash
`d1c6fefd23f65e370cd0eb8ce9c737f0529a2cf75f9e7c926dbdd889afeeffe3`.
Its frozen inputs included accepted graph r1, cast r1, art r1, script r2,
review r2, and original Brief r1. The enabled `default` text profile was
version 1, hash
`bd2c82e13df613d8bf4f2e4058ee945691f6efcb1c80d0ee0bd784594d3d88b9`,
using the configured OpenAI-compatible gateway and model `qwen3527b`. This
differs from the profile revision noted in older evidence; the live profile
was freshly inspected and non-generatively probed before dispatch. The
`production_bridge_intent` prompt was version `1.0.0`, rendered hash
`257d53c0f47c380787df695b0ba9299875a41d3bd118b26946421b7abd6f0431`.

At `2026-09-23T00:20:25Z`, one `intent-jobs` request created job
`5ce94077-f764-49c2-ad33-e2de438c6f68`. It completed `ready` at
`00:21:31Z`, with provider request ID
`chatcmpl-iE4sOTzvB4wGUUR76VmAXIjSekoW5ZAn` and response hash
`705ec30d915f79233745f7b019414e6799e9fe2b0c1d830fd72d5e0dc1f85b14`.
The provider reported **5,360 input** and **2,771 output** tokens. A cost
amount was not available. The output covered all 57 required IDs with
nonblank Chinese intent suggestions; the resulting model proposal was r2,
hash `ae71f66f0583afeb24fd9ca904fb7b18b31356c0e7c726a53bad1717c304aca8`.
The redacted persisted prompt, response, profile, candidate and usage evidence
is at
`.local/relay/bridge-intent-live-u4-source-trial/evidence/attempt-1-redacted.json`
(SHA-256 `714779b4ab49d7117f8d2df68b1f8a6b92e07151a1efad0ee775ee6bdb9206c3`).
The derived request in that export is not claimed to be byte-exact wire data.
The file is local/ignored, mode `0600`, and was checked not to contain the
server API key.

## Source-grounded development review

The suggestions were semantically useful at the broad branch level, but 15
of 57 overstated outcomes, invented visual/audio direction, or framed a
scene objective as commentary rather than character action. A development
review saved those 15 `text` values through the supported whole-package API
while preserving every original `suggestedText`, source excerpt, target ID,
and model provenance separately. The resulting proposal is r3, hash
`0824446d567afa104967275f5d966ddd30ec9b45f4e3e8e4a59d740f832fcc6f`,
with `suggestionOrigin=model_inference.v1` and `reviewState=author_saved`.
That technical state means a reviewed package was saved; it is **not** human
creative acceptance or permission to install.

Examples of source → model → saved review:

| Source | Model suggestion issue | Saved review decision |
| --- | --- | --- |
| `药箱留在仓库。` | Called the box “abandoned” and a tragic loss. | Say it was not transferred; do not claim destruction. |
| `我们在风暴外缘漂泊到天亮。` | Called the wait a tragic sacrifice. | Retain drifting/waiting and risk; do not imply deaths. |
| `码头的人跟着我。` | Claimed people had accepted sacrifice. | Treat 阿岳 as organizing the dock evacuation. |
| `雨水沿厚玻璃灯室窗滑下。` | Invented an environmental sound effect. | Keep the visible rain and mounting pressure only. |
| Branch fuse insertion | Called outcomes “救船弃人” or “救人弃船”. | Keep distinct light allocations without asserting either side was abandoned. |

After an actual restart of the isolated `8821` runtime, the public API again
reported all 57 source-bound entries, 15 saved differences from immutable
model suggestions, the same r3 hash and job/response provenance, and no
installation. At both 1440×900 and 1920×1080 the supervised workbench showed
the source excerpt, original model suggestion, edited text, and disabled
confirmation. Local screenshots are in `output/playwright/bridge-intent-live-*`
and remain untracked. Console messages were limited to the expected sandbox
refusal to execute scripts inside optional upstream report iframes; the review
page remained available.

An independent read-only review inspected the source receipt, redacted job
evidence, isolated persisted project, and live bridge state. It found no
blocking source or provenance issue in the corrected package. A few unchanged
beat-purpose phrasings remain interpretive dramatic readings, not assertions
of installed canon. The restarted copy has no installed bridge stage revisions
and zero media tasks. The original project's `project.json`, `project.sqlite3`,
and application SQLite SHA-256 hashes remain, respectively,
`e4ad93038f1d7972cd7e48ef208aaeae53eeeabd3fef6fd124e3fe27bf9873ff`,
`8daae34d30a97d2847f514a3270183eb4985564d63db589d29b5f91f3a86ad97`,
and `4a550c52c4449a1848a7bc7f20697993f312483a0d7ddac54d985e2ff3f175df`.

## Stop condition and open dependencies

**Canonical installation is UNMET.** Each of the three retained scenes has
9 source cuts, while the original Brief allows 2–4 shots per scene; the r3
proposal reports three `brief_shot_count` conflicts and one corresponding
`canonical_validation` conflict. Confirmation is disabled in the UI and was
not called. The changed-Brief copy demonstrates that relaxing the rule through
the current Brief update makes the accepted F4/F5 context stale instead of
making this proposal installable. This is a separate product dependency for a
future scoped decision, not a reason to weaken the guard or rewrite accepted
source evidence inside this trial.

No second provider completion, automatic retry, fallback provider, media
dispatch, or source-contract mutation followed the ready job. The next action
requires a separately authorized resolution of the shot-policy/source-shape
conflict before any canonical confirmation or product acceptance can be
claimed.
