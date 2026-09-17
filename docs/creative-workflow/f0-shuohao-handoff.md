# F0 Shuohao handoff contract

Status: implemented candidate boundary, 2026-09-17. This is not creative or
product acceptance.

## Pin and operation

`third_party/shuohao-skills` is a Git submodule pinned to
`4322897e6d2bdaf66365534fd40194360c75a85f` (2026-08-26). It is the reviewed
revision used by the handbook and contains all five public skills, their
schemas, deterministic Node scripts, `LICENSE`, and `NOTICE`. A submodule is
the smallest reproducible copy: a clean checkout uses
`git clone --recurse-submodules`; Plotloom never reads the user-home research
clone or installs the skills globally. The upstream is Apache-2.0 and its
NOTICE is retained in the submodule and attributed in the repository NOTICE.
The exchange compares the initialized submodule `HEAD` to Plotloom's recorded
Git gitlink before it freezes a package; a merely available upstream checkout is
not a pin. This deliberately operates from a source checkout: an installed
Plotloom wheel does not package or resolve the specialist/upstream skill tree.

The F0 CLI is deliberately small:

```bash
uv run python scripts/creative_handoff.py prepare \
  --root <project>/outputs/creative-handoff --request <frozen-request.json>
```

It produces `jobs/<id>/package/`; a disposable specialist reads that package
with `plotloom-shuohao-specialist` and writes only the matching `delivery/`
candidate, derived `report.html`, and completion receipt. `inspect` admits no
candidate automatically and can check the current accepted stage revision.
There is no F0 browser entrypoint; that user-operability gap remains F1/F10
work, rather than a hidden developer-edit workflow.

## Field and authority map

| Stage | Upstream candidate shape | Model owns | Author owns | Trusted code owns | F0 gap / retirement |
| --- | --- | --- | --- | --- | --- |
| outline | `outline.json` | proposed adaptation, characters, scenes, beats, episodes | supplied text, genre, duration, preferences, adaptation choice | request hash, stage revision, candidate admission | Existing Brief/Bible/Graph proposal path is not retired until F1 proves replacement. |
| characters | `cast.json` | profiles, image/voice direction | source evidence and approval of identity direction | request hash, review and later asset selection | Existing character-reference review remains owner; no F0 identity generation. |
| art | `art.json` | scene/prop anchors, prompts, variants | visual intent and acceptance | managed assets and selected references | Existing image-job handoff remains owner; no F0 images. |
| script | `script.json` | scenes, action beats, dialogue | source/adaptation facts and acceptance | revision/currentness and canonical installation | Existing scene-beat authoring is not retired until F4. |
| storyboard | `storyboard.json` | segment/cut plan and H3 direction | source/production intent and acceptance | review, media jobs, selections, playback | Existing storyboard/media paths stay intact until F5–F8. |

The request carries a self-contained source object, upstream JSON inputs, a
creative brief, and `expectedStageRevision`. The completion receipt binds the
candidate and report bytes to its job/request/stage and to the pinned upstream
revision/skill hash plus local specialist skill hash. The exchange is a
**transport** validator, not a second semantic validator: the specialist runs
the upstream validator, while a future existing review/canonical owner decides
semantic acceptance. Before it even reports a candidate ready, it verifies every
specialist-consumed package entry (`request.json`, instructions, template, and
each input) against the frozen projection. It rejects malformed packages,
non-exact delivery shapes, identity and execution-pin mismatches, hashes, and
symlinks. `assert_current` rejects a candidate whose frozen revision is no
longer current. Neither method can write accepted project content: F0 defines
no review or installation owner, and only a later selected existing
review/canonical owner may install after an integration decision.

## Deliberate exclusions

F0 does not implement source-route UI, persistence migration, automatic
execution, five services, queues, custom plan expansion, Qwen calls, media
generation, report embedding, or retirement. Upstream reports remain isolated
HTML files in the handoff delivery until an owning review surface is selected.
