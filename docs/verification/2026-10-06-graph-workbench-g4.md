# G4 Production context qualification, 2026-10-06

Current source/static manifest `.local/graph-workbench/g4-source-manifest.json`,
aggregate `58e1fba5f40f71e623cca5634c024a94e1ac10111bbb0ac9db5abfd58fb3c64a`.
Retained `main`, baseline `e542f49`; no publishing or service activation yet.

## Implementation

Production context projects every scene occurrence and ordered cut through exact
current F4/bridge coordinates, including repeated S01 locations. It preserves
bridge identities and rejects ambiguous/missing/currentness mismatches rather than
inferring shots. Handoff additionally verifies installed storyboard revision,
shot scene membership and exact millisecond duration, then uses the existing
navigation gate and shot/media owner. Package review, per-shot approval, image
candidates/review and video candidates/selection retain their existing commands.
There is no new node generator, approval authority or media readiness inference.

The footer now compares mapping content semantically rather than JSON key order,
checks the exact admitted map revision/hash and canonical graph revision, and
explains first-install-only production. Current installed production disables
reinstallation; structural/footage replacement disables content confirmation.
Unknown production reads suspend installation. Draft changes suspend shot handoff
while retaining installed content. ADR 0123 records the current ownership contract.

## Executed verification

All terminal results collected, with local logs under `.local/graph-workbench/`.

- Projection/admission regression **13 passed**, `g4-projection-final.txt`, including
  deliberately different JSON key ordering with equal content.
- Full frontend **528 passed**, 74 files, `g4-frontend.txt`.
- App types and deterministic static build exit **0**, `g4-types.txt`, `g4-build.txt`;
  E2E types exit **0** through the completed native commands.
- Graph footage/bridge/presentation backend **45 passed**, `g4-production-backend.txt`.
- Clean combined native creator Production and professional shot handoff **2 passed**,
  `g4-native-qualified.txt`. Creator includes two S01 occurrences/nine cuts, exact
  second-scene cut handoff, route-only zero cuts, graph draft pause, installed
  structural replacement refusal and downstream revision drift. Browse writes zero;
  installed stages/bridge evidence read back unchanged before disposable drift.
- Existing native still/image/H3/branch playback **4 passed**, `g4-media-current.txt`:
  imported/reviewed still survives restart; frozen specialist image prepare/send/
  refresh/refine and stale intent guards; reviewed H3 profile; both native-ended
  routes and episode reset. Only test-owned roots and fake transport; no live calls.

Initial new native test failed on a decision ID guessed from another fixture.
The test now reads the accepted route-only binding; retained diagnostic log
`g4-native-first.txt`. No application contract was weakened. Existing Starlette
and NO_COLOR/FORCE_COLOR warnings remain documented.

## Independent and visual observations

Attended independent GPT-6.1 Sol / Medium read-only review inspected 12 candidate
paths plus existing graph/script/shot/admission owners, matched those hashes to
the then-current `d8fb2d7a…` manifest and found no concrete G4 blocker.
The final manifest differs only by the stronger key-order regression assertion;
runtime files are unchanged. Reviewer executed reads/hashes, not tests or providers.

Source owner directly inspected both viewport PNGs in
[supporting evidence](supporting/graph-workbench-g4/). At 1700×900, graph and selected
opening remain visible beside Production; package scope and first-install-only
footer are readable. The scrolled second-scene cut shows its exact 2.5-second
duration, current installed binding, pending approval, readable wrapped title and
existing media handoff. These observations are separate from native assertions.
Final desktop matrix, full-suite source/static/wheel checks and owner walkthrough
remain G5; screenshot presence alone does not qualify them.

## Preservation and next step

No retained project reset, credential/settings change, real provider dispatch,
commit, push or activation. Implementation and this bounded verification are
qualified; owner creative/media/product acceptance remains pending. G5 now owns
the permanent C01–C47/P01–P06 contract, current-candidate matrix and complete gates,
then scoped publishing and quiescent normal 8841 activation with preservation.
