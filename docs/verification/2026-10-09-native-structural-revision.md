# Native structural revision and graph label layout

This is the Revise round of the approved full creator E2E run, on the same
completed native project `90c0f895-48de-4b57-8725-4b6f72797633` at isolated8865.
Revised production and playback remain pending. No native job was dispatched
during these structural operations; normal8841 and protected projects were not edited.

## Authoring actions and saved state

After explicitly changing Brief nodeBudget4→8, the UI recovered the existing
draft against the current binding. An exact East-choice-edge insertion created
scene `graph-3d5df4ce8b4141e19bdc13e7` and continuation
`graph-b9c9410be53e4696ac3d48dd`. Draft r3 contained the insertion, r6 the final
title and prose. A value-matched save ACK and independent readback preceded reload;
the text and identities survived. This avoids confusing an earlier title-blur ACK
with a later full-prose save.

Safe bypass removed that scene at r7 and restored the original East edge. Undo
restored its identity, prose and connections at r8. Undo uses authoring-drafts PUT;
an automation wait incorrectly expected graph apply POST and timed out, but the
readback established the applied r8 and no duplicate action was issued.

Deleting the old East ending with “仅删除，保留待连接” produced r9 and a pending
continuation endpoint. Changing the new scene to an ending correctly refused
while that output remained. Explicitly deleting the pending continuation produced
r10; the subsequent ending conversion succeeded at r11. Final East title, summary
and choice consequence were acknowledged at r13 and independently read back.

The final topology has four nodes and three edges: original opening, original
route-only choice, unchanged West ending and the new East ending. Original East
choice edge `edge-ab8a8b8d-dfa8-5fc2-895b-13d1ead701d4` now targets the new ending.
The new East summary retains a five-second left-lamp/left-turn ending and the
ten-second opening, without new characters, settings or props.

Normal UI confirmation returned200 at03:27:45UTC; graph application returned200
at03:28:06UTC on October9. Confirmed map r3 hash:
`dae2b0721c9833baaa1403b3bbc5eda97e136dca0232a050c87ab88b5a338c89`.
Applied graph r3 hash:
`30a0f7257cffed8454838d81ddb0e397b8f827e5db3ddaf89f561d346d7fc894`.
The graph admission is current. All four baseline H3 jobs remain ingested with
one retained segment each, current=false and selected=false. Old media is retained,
not admitted as revised production.

## Label layout root cause and repair

Insertion appended a node identity while the visible row put West before the
new East scene. Label lanes still followed historical edge creation order, so
the outgoing option curves crossed. This was a presentation-layer ordering bug,
not a wrong story connection. `creatorLayout` now sorts each copied label lane by
visible target position, then source position at joins. It does not reorder or
rewrite the story topology or edge identities.

A regression reproduces the appended-middle-node case and asserts label order
and unchanged edge output. The existing six-sibling/converging-label check now
tests geometric separation independently of original edge creation order.
Independent read-only review found no concrete defects. The previous stable
checkpoint passed840 frontend tests, types and the isolated frontend build;
this continuation reran all three layout tests and diff checks successfully.
Full browser and publication gates remain separate.

Directly inspected evidence under the main checkout's
`output/playwright/native-intent-2026-10-08/`:

- `revise-inserted-middle-1700.png`: original crossing defect.
- `revise-inserted-fixed-1700x900.png`, `revise-inserted-fixed-1280x768.png`,
  `revise-inserted-fixed-1280x460.png`: repaired routing and retained side editor.
- `revise-delete-bypass-preview-1280x460.png`: initial short-height preview;
  its lower controls were outside that captured viewport.
- `revise-delete-ending-controls-1280x460.png`: scrolled preview with confirmation
  controls visible and subsequently used successfully.

C06 now permanently includes insertion-induced label ordering. This checkpoint
does not close character/reference revision, production rebuild, fresh media,
all revised routes or the remaining whole-product E22 audit.
