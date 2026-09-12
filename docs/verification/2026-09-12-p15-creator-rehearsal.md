# P1.5 creator rehearsal receipt — 2026-09-12

This is a test-only, fictional creator-workflow rehearsal. It is not a human
review, production-quality acceptance, or a claim that canonical story
authoring was performed through the UI.

## Scope and runtime

- Source revision: `9245248c8e130b80efc5578d1192029b0d6383b8`.
- Project: `aa637c38-8d21-4444-8ae2-cc1ce87bfa2a` (`The Last Reel`), one
  fictional character, Mara Vale, in a municipal archive.
- The canonical fixture was manually authored through the public authoring API
  solely to avoid unrelated text-generation qualification. Creator workflow
  actions were performed in the local UI: proposal/refinement preparation and
  copy/refresh/reference selection; storyboard Approval; three shot job
  preparation/copy/refresh; candidate comparison/selection; visual-intent and
  same-person reviews; still-preview creation/playback; and post-restart reload.
- Isolated, non-repository runtime roots retained locally:
  `/Users/wjmao/projects/HU/plotloom-creator-rehearsal-ha6D6D/` (SQLite,
  artifacts, exchange packages, manifests, prompts, output PNGs, and logs).
- Storyboard Approval is `r1`, labelled `Codex`; all visual reviews are
  Codex assessments, not human or product decisions.
- Still durations were authored as milliseconds: close `6000`, three-quarter
  `6000`, wide `7000`.

## Actual ImageGen deliveries

| Purpose | Job | Built-in ImageGen task | Candidate | Output SHA-256 |
| --- | --- | --- | --- | --- |
| Original identity proposal | `ij_abed8c8bc74c4cd088d4177f1751e826` | `exec-56fea5e0-e6c2-4971-bf46-b1091dc724b5` | `50bbff9d` | `c9a29cd2c57dae9b8ad9ab6318f34fde393c7e4cc08d768629021552074d90a0` |
| Identity refinement (parent proposal) | `ij_e3250f1e743d48fa9c09be8b29b12a25` | `e31f8493-5f60-4e58-be16-0a73f476c939` | `72bf9cb6` | `4ad5e12a307f2b3604b17ca7b2505f490cc8d71b91891f26f82e101a05c2b6a1` |
| Close / steady spool | `ij_b7eb4e4754904d70a1728165c067dfdb` | `exec-def13627-5711-48b8-9d83-191d1f2bbcfc` | `39a8fd11` | `55f7f4b11068b63fc0d577bbcbd4f45d63a1a9410ab95dcbbe18c2cafd925a68` |
| Three-quarter / hand rewind | `ij_32d4311b98d345d8890eca1efa809de3` | `exec-9630e72b-09d3-454e-8c6a-67a7b5785e52` | `74c59d05` | `a1d41746747f6406a9fa124d49f624fba6eedf2dd210f42e0a7e9d97441a79a7` |
| Wide / seal at dawn | `ij_294261d02f9d452f86fc436e9196fc9d` | `exec-8ca01495-e9ef-4ee5-b7f8-a99c370f9735` | `b21c05c6` | `574ceba029c916e1bfffbbfa076792212d620b95296c0ab3ef9a0a9dc9bedaae` |

Each package was pinned to the stated source revision before specialist
execution. Each retained `completion.json` records `codex_imagegen` task
evidence and the actual prompt. The three shot deliveries include the frozen
identity reference attestation. The selected primary identity reference is
the refinement candidate `72bf9cb6` at reference decision `r1`.

The first identity-proposal delivery was initially rejected by the contract
because an optional `referenceUse` object had an empty `viewedReferenceHashes`
list. The retry removed that invalid optional metadata only; no image was
regenerated and no provenance was changed. The rejected receipt remains in the
isolated exchange history.

## Visual review and persistence observations

- Likeness and state continuity: the selected reference and all three shots
  visually retain Mara's dark wavy hair, round glasses, charcoal coat, and the
  deliberately authored one dark **right** glove with a bare left hand.
- Shot direction: the wide sleeve-at-dawn action is materially wider and
  distinct. The close and three-quarter results are both usable for likeness
  and stated hand/costume continuity, but are too similar in medium-close
  framing and hand/reel pose to support a strong three-distinct-compositions
  claim. This limitation is recorded in their UI compatibility and review
  notes; no extra generation was used to hide it.
- The UI froze the reviewed still animatic
  `shot_close → shot_threequarter → shot_wide` and its Play control was
  activated. The retained screenshot records the resulting Pause-button state;
  it is not evidence of timed progression or seek verification. After
  restarting the owned service against the same SQLite, artifact, and exchange
  roots, the UI reload restored the project, selected identity reference,
  reviewed assets, Approval, and the persisted three-shot preview history (the
  existing preview was opened from its UI history).

Tracked UI proof copied from the isolated runtime:

- `docs/verification/supporting/p15-creator-preview-playback.png`
