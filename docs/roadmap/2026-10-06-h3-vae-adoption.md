# H3 D adoption · 2026-10-06

Owner approved maintained video-only precision, reload/clone correction,
focused lifecycle tests, audio BF16 confirmation and deployment. Root is sole
writer; independent review is read-only. Baseline: `e422b4e` on the specialist
branch. [ADR 0098](../adr/0098-h3-video-only-vae-precision.md) owns the contract.

1. Implement maintained Comfy loader and frozen gateway VAE binding. Test all
   qualities, Ref2VA, rejection of missing runtime policy and old snapshots.
2. Run focused tests, broader Python/package checks and independent review.
3. Prove managed lane/Comfy idle; preserve published voice/take records and bytes.
   Stage an immutable source release, retain prior containers and model assets.
4. Verify real pinned-runtime clone/deepclone/offload compute using a 128px
   image and 0.1s audio, then deploy same Comfy image with only fast flag and
   maintained node. No experiment observer is installed in production.
5. At most two managed full clips: quality-1 704x1280 and voice-conditioned
   576x1024, each 124 frames. Use retained inputs; no voice synthesis. Decode
   outputs, verify dimensions/duration/audio, exact runtime and healthy lane.
   Persist uncertainty before each sole submission. Do not replay unknown work.
6. Record deployment, current reproduction instructions and rollback. Local
   commit only; director contact, Plotloom integration, merge and push remain held.

Stopping condition: D serving, focused lifecycle/audio proof and bounded managed
canaries passed, user assets unchanged, receipt/docs saved. Any failure preserves
evidence and restores the prior serving setup only when work is safely terminal.
The earlier twelve-cell trial remains immutable and is not extended.

Closeout: D is serving; real lifecycle proof, both acknowledged managed clips
and idle same-container restart passed. Three published voices/two takes and
their bytes are unchanged. See [the receipt](../verification/2026-10-06-h3-vae-d-adoption.md)
for exact runtime, retained observer/build failures and no-replay reconciliation.
Plotloom integration/director messaging, merge and push remain held.
