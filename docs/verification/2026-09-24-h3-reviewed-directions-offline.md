# H3 reviewed-direction offline preview · 2026-09-24

This is an **offline, agent-authored proposal**, not a provider request or a claim that the speech defect is fixed. It reads the retained B job `vj_83dc62e692f24ca3a95e9c1a524fcec0` through the local read-only API and applies the new `plotloom.h3-i2va.v3-reviewed-en` compiler in memory. It does not alter that job, its prompt hash, its media, or the project. The preserved B recording remains the evidence that the model spoke the canonical action sentence before the intended dialogue.

The review source hash is `56e55747592801bdb21d9dc99b96d488a6784155ff8a2bfc796b9f78fc989d3b`; the UTF-8 SHA-256 of the complete prompt below is `685b03af7d41648e9857ffd84995d67c030920165797b141a6b51e8beed66c3c`. Those hashes describe this in-memory reconstruction, **not an admitted future job**. A future prepare must obtain a fresh server preview bound to its then-current source, keyframe, provider, request, and timing.

| Frozen source path | Source | Reviewed provider direction |
| --- | --- | --- |
| `shot.composition` | medium shot of a female lighthouse keeper setting a brass fuse between two parallel sockets on a deep green switchboard, rain-streaked lantern-room glass behind her, cinematic film still, cold storm-blue and amber palette, 16:9 | A medium cinematic shot frames a female lighthouse keeper at a deep-green switchboard with two parallel sockets and a brass fuse. Rain-streaked lantern-room glass is behind her, in a cold storm-blue and amber palette, 16:9. |
| `shot.action` | 沈岚把铜质熔断器放在两条并列插槽之间。 | The keeper places the brass fuse between the two parallel sockets. |
| `shot.cameraMovement` | Push In | The camera pushes in toward the keeper and the fuse. |
| `resolvedContext.characters.C01.voiceAnchors.0` | 清冷而结实的女中音，胸腔支撑稳定 | A cool, firm mezzo-soprano voice with steady chest support. |
| `resolvedContext.dialogueCues.0.delivery` | natural | natural |
| `resolvedContext.dialogueCues.0.performanceNotes` | 盯着线路标签 | She watches the circuit labels. |
| `reviewedSoundscape` | No ambient or physical sound event is authored in this shot. | Faint handling sounds from the keeper moving the brass fuse at the switchboard. |

The soundscape row is an agent-reviewed supplement, not an F4/F5 authored audio event. It remains visible in the complete prompt for final preflight review. The canonical cue text `一枚，只够一边。` is deliberately **not translated**; it is inserted once by trusted code, outside the reviewed-direction fields. The source composition describes an action as a still-frame pose; the reviewed direction separates framing from the one moving action without adding a new story beat.

```text
For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced.

integrated_multimodal_description: [Shot 1] <Picture 1> establishes the opening visual style, composition, subjects, objects, and spatial relationships; preserve them as the action develops in one continuous shot. A medium cinematic shot frames a female lighthouse keeper at a deep-green switchboard with two parallel sockets and a brass fuse. Rain-streaked lantern-room glass is behind her, in a cold storm-blue and amber palette, 16:9. The keeper places the brass fuse between the two parallel sockets. The camera pushes in toward the keeper and the fuse. The visible speaker established by <Picture 1> (S1) speaks with a cool, firm mezzo-soprano voice with steady chest support. She watches the circuit labels. The visible speaker established by <Picture 1> (S1) says once with natural delivery: <d>[Chinese] 一枚，只够一边。</d> Do not add text overlays or words absent from the reviewed first frame and authored shot.

overall_soundscape: Faint handling sounds from the keeper moving the brass fuse at the switchboard.

non_diegetic_music: N/A
```

Inspection: the canonical Chinese action is absent from provider directions, while the intended Chinese line occurs once inside `<d>`. This checks the rendering contract only. There is no H3 completion, observed output, creative approval, or evidence that a model will obey the contract. The failed “only vocal utterance” treatment is not included in this new-use prompt.

The governing workflow and the official pinned guide links are in [the living playbook](../operations/h3-prompt-writing-playbook.md). The original A/B receipt remains [separate historical evidence](2026-09-24-u4-h3-vocal-control-comparison.md).

## Isolated technical verification

An offline fixture at `.local/h3-prompt-review/source/` used the shipped static bundle with a typed fake H3 transport. Browser interaction completed current-source load → four fixture-source English directions → one package review → complete prompt preview → explicit preparation. Read-only API inspection found exactly one `prepared` job with compiler `plotloom.h3-i2va.v3-reviewed-en` and a frozen compiled prompt. No submit route was invoked; the job never left `prepared`, and no generation or media result occurred. This fixture is not the retained U4 story or an H3 quality demonstration. Browser screenshots after the basic field/checkbox layout correction are in `output/playwright/h3-manager-1440-final.png` and `output/playwright/h3-manager-1920-final.png`; these are local untracked evidence, not committed assets. The isolated port `8834` was stopped after inspection, while its fixture files were retained.

Verification at this checkpoint: focused H3/project-video tests, 42 passed; production-runtime plus project-video rerun after the stale fixture correction, 28 passed; full frontend unit suite, 215 passed; both TypeScript checks and production static build passed. The full backend run before that last test-only correction had 746 passing tests and one failure in the stale production-runtime fixture, which directly prepared without the newly required reviewed package. The affected test then passed in the focused rerun. This sequence is not represented as a full post-correction backend pass. An independent read-only review found no remaining scoped blocker after a prompt-structure injection guard was added. Backend tests emitted the existing Starlette/httpx deprecation warning; frontend unit tests passed with existing React act/list-key warnings.
