# Graph workbench G2 creator presentation qualification

Qualified 2026-10-06 on retained `main`, baseline `e542f49c4e815d797f17e0a83c0631c54f9f6ea3`.
Source/static/frontend/tests aggregate SHA-256:
`bc3363a9006bf324af8a973bff5af8bdb1368e3578fb608130b1cb6fe97334a5`.
Manifest `.local/graph-workbench/g2-source-manifest.json` enumerates current files
from src/plotloom, frontend/src/tests/e2e, tests and ADRs 0120–0122; aggregate is
SHA-256 of sorted `path NUL file-sha256 LF` entries. No G3–G5 release or product
acceptance is implied by this checkpoint.

## Delivered and independently reviewed

Creator/professional destinations use the same root and navigation gates. Opening
an existing project from the directory enters creator mode. Automatic longest-path
ranks preserve sibling rows, route skip links through an outside gutter and give
each incoming label its own lane. The document owns vertical scroll; the graph
pans horizontally. Row defaults, exact input replacement, insertion, reuse, pending
outputs and real connection dragging all prepare the same atomic current command.
Immutable preview tables show the exact before/after arrows, with retained option
identity and explicit affected joins.

Private inspector width, page/chart position and project selection preferences do
not dirty authored state. Width has pointer, keyboard, cancellation and automatic
reset controls. Selection follows/clamps the tall inspector without remounting
fields. The interface and developer entrypoint visibly require desktop >=1280px.
Brief target changes have a current-actual versus before/after target preview;
cancel changes nothing and confirmation preserves the graph rather than reshaping it.
Fresh decisions explicitly create two pending choices; restoring retained choices
can explicitly omit scaffolds. Reuse retains node identity, prose and outputs.

Attended read-only GPT-6.1 Sol / Medium review found incoming labels overlapping at
joins and selection-only reload loss. The layout owner now assigns distinct lanes;
the provider persists selection in private presentation storage. Focused guards
cover first incoming-edge clickability and selection reload with unchanged root
revision. The same reviewer closed both findings and reviewed target preview with
no further blocker. No parallel writer was used.

## Executed verification

All listed process exit statuses were collected:

- Graph commands/API: **20 passed**, existing Starlette warning,
  `.local/graph-workbench/g2-commands.txt`.
- Full frontend: **513 passed**, 72 files, `g2-final-frontend.txt`.
- App types and E2E types: exit **0**, `g2-final-types.txt` and
  `g2-final-e2e-types.txt`.
- Deterministic current bundled static build: exit **0**,
  `g2-final-styled-build.txt`.
- Native G2 browser: **6 passed**, `g2-qualified-browser.txt`: three desktop
  cases, repeated operations, capacity/reuse/restoration and target preview.
  Final preview styling reran the three operation cases: **3 passed**,
  `g2-preview-styled-browser.txt`.
- Current playback fixture correction: **2 passed** (1.9 min),
  `g2-footage-browser-current.txt`; the playback decision explicitly has footage,
  with original scene, shot and video assertions retained. This closes the G1
  receipt's dated E2E-type correction, not a new creative/media acceptance.

Earlier failed G2 matrix/fixture logs remain local. The first matrix exposed last
row controls beyond declared chart height; layout height now includes that row gap.
A screenshot review exposed initial restore/reveal ordering in short windows;
geometry readiness now sequences initial scroll restore before selection reveal.
The first capacity test expected a nonexistent diagnostic name; the existing
`out_degree:choose` contract correctly refused the seventh option without writes.
No tolerance or alternate executor was introduced. Earlier frontend logs include
a React SettingsDialog missing-key warning; its unchanged stage-number mapping is
present at baseline and is unrelated to graph changes. Browser runner emits the
NO_COLOR/FORCE_COLOR environment warning. These are not described as warning-free.

## Actual browser observations

Source owner directly inspected all 12 final desktop screenshots and four final
operation screenshots, retained under [supporting/graph-workbench-g2](supporting/graph-workbench-g2/).
Matrix: 1280×768, 1280×460, 1700×900; top/middle/bottom selection and resized/reopened
state at each size. Observed readable Chinese card/option labels, six siblings on
one row, natural tall graph, top/middle/bottom inspector clamps, fixed reachable
header/actions and 300/380 automatic widths. Explicit resize persisted 350px;
reload retained intentional user pan (so the selected card can remain partly
outside the panned viewport). Selection-only reload independently restored the
chosen node without an authored revision. Incoming labels occupy separate lanes;
clicking the first converging connection opens its exact identity.

Native 123→222→333 journey inspected insertion, two-arrow row preview, retained
choice prose, 123→222→333 reconnection, pending outgoing edit, cycle refusal with
no partial commit, safe bypass/Undo and only-delete/Undo. Decision/join/ending/
detached deletion each cancel, commit and Undo without cascades; opening deletion
is disabled. Pointer connection drag is separate from click/input replacement and
commits the exact output while retaining its displaced target. Both modes and
reload read the same saved mapping. Capacity refusal, retained-node reuse and
explicit zero-scaffold restoration preserve the expected identities/content.

## Preservation and next slice

Only disposable test-owned projects/fake transport were used. No retained project
reset/rebuild, live provider dispatch, credentials/settings mutation, service
activation, commit or push. Canonical/accepted data and downstream media were not
changed by graph draft browsing/operations. Owner UI and creative acceptance remain
pending. G3 now owns real node-bound Story scenes/revision editing; G4 owns exact
Production bindings and actions; G5 owns permanent checklist and full release gates.
The temporary Story/Production placeholders are explicitly not G2-qualified features.

## G2 directory-entry amendment, 2026-10-06

Opening G3 wiring found the two direct directory callbacks still requested Brief;
only the closed-project lifecycle callback had changed. The graph-first entry claim
above was therefore too broad at the original hash. Both direct callbacks now
request creator through the same navigation owner. Actual native directory opening
passes (**1 passed**, collected exit 0, `g2-directory-browser.txt`), and deterministic
static build passes (`g2-directory-build.txt`, exit 0). The amended candidate is
`a18df3c5fa25b68f925dbe0977bae006e7d6bb40c8951ade354eb1fda789d47a`, manifest
`g2-directory-source-manifest.json`. Original evidence/hash is retained. No other
behavior, retained store or service changed; G3 proceeds after this correction.

## G2 all-member inference and readable-preview amendment, 2026-10-06

Manager inspection reopened G2: a mixed connected/detached row inferred a parent
from only connected members, and primary preview text exposed long identities.
The layout now requires direct choice input evidence from every member. Any
member without that evidence leaves the parent unspecified. Previews use actual
node/option labels and explicit new/pending descriptions; stable IDs are folded
technical details. Insert impact prose also contains no raw IDs. ADR 0122 records
these semantics. No command, identity, CAS or impact-hash contract changed.

Amended candidate: `8543209070544a6052f60a3692cb3430d66e3a959a2d08966e422ba6b5af2d2f`, manifest
`g2-manager-amended-source-manifest.json`. This manifest includes partial G3 Story
files; those are **unqualified** here. Original G2 hashes and evidence above remain
historical evidence. This amendment qualifies only G2 presentation repairs.

Collected terminal exits: graph commands/API **20 passed** (existing Starlette
warning); native operations **4 passed** (`g2-manager-final-browser.txt`); app and
E2E types exit **0**; full frontend **513 passed**
(`g2-manager-amended-frontend-current.txt`); deterministic static build exit **0**
(`g2-manager-final-build.txt`). The first full frontend rerun found one test still
expecting a Brief immediately after directory entry. It now checks creator entry
and then verifies the unchanged delayed-PATCH ownership guard through Brief.
The failure log remains `g2-manager-amended-frontend.txt`.

Source owner directly inspected the amended row and insert screenshots, retained
as `2026-10-06-amended-row-preview.png` and
`2026-10-06-amended-insert-preview.png` in supporting evidence. Both show readable
human endpoints and both affected connections; technical identities are folded.
The mixed-row native exercise observes an empty parent and cancels without writes.
Attended independent GPT-6.1 Sol / Medium review closed the residual impact-prose
finding and reported no further concrete G2 blocker. No provider dispatch, retained
data mutation/reset, service activation, commit or push. G3 resumes after this
candidate-bound amendment; G3–G5 remain unqualified.
