# Creator UI batch and Brief-owned Source structures

Status: implemented, independently reviewed, fully locally qualified, published
and activated on normal 8841. Full remote CI is in progress; creator acceptance
remains separate.
Authority: [approved batch](../roadmap/2026-10-04-creator-ui-batch.md), including
the owner's expansion from the binary pilot to Brief-driven topology.
Baseline: retained `main`, `c6797d7`. Runtime candidate:
`79693f1e24e470016e79430fb13511f7a39418b4`, pushed to `origin/main`.
One source owner implemented through Relay Deliver; the manager remained read-only.

## Delivered behavior and owning repairs

| Outcome | Root cause and repair |
| --- | --- |
| Brief directions | Nullable text could not express grouped selections. Structured optional subject/narrative and representation/treatment/lighting selections preserve custom additions and existing detail text. One composed generation input reaches story, outline and visual consumers; no presets are silently selected. |
| Waiting and recovery | Acknowledgement, execution, successful reads and integrity failures were easy to confuse. Shared actions use sequential reads, bounded transient backoff, hidden-page pause/return refresh, identity isolation and visible last-successful-check/error states. Sending is never retried automatically; cancelling publication retains native ownership. |
| Accepted outline reading | Reading was tied to the current candidate rather than retained acceptance. The accepted report remains bound to its original candidate/revision; unavailable HTML exposes escaped read-only structured content. Starting another revision and explicitly returning to retained acceptance are separate, revision-checked actions. |
| Branch suggestions | Binary Source forms contradicted the authored Brief, and downstream bindings assumed three sections/one question. Trusted code plans feasible topology before prose. The model supplies all node, question, option/consequence and join prose against exact frozen identities. Adoption, map saving, graph installation and later acceptance remain separate. Cast, art, script route caps, production presentation and the player consume the complete canonical graph. |
| Current-project settings | Returning to Brief was hidden among secondary tools. A visible project settings control and explicit return to Source use the existing draft-gated navigation. Structural edits retain source/outline/media while staling dependent maps/proposals; preparing again freezes the new settings. |
| Setting help | Chinese help distinguishes actual choices, options, complete routes, endings, nodes and joins. Compact popups remain inside the viewport. A shared help group has one active explanation; focus/tap replaces an earlier pin, while incidental hover cannot replace focused help. |

Durable contracts: [ADR 0117](../adr/0117-creator-directions-and-branch-suggestions.md)
and [ADR 0118](../adr/0118-brief-owned-source-topology.md). The author owns Brief,
source and acceptance; trusted code owns feasibility, IDs, links, frozen basis,
currentness and installation; the model owns advisory prose. Source supports two
through six options per choice. Capacity constrains the planner search while the
frozen Brief retains its authored maximum. Infeasible settings are rejected
before reservation/dispatch without being rewritten.

Retained accepted binary evidence and installed production remain readable under
their original interpretation. New structures use planner v2; older evidence is
not relabelled or made to appear compliant. Installed production cannot be
replaced through this workflow. No V1 runtime path/data import was introduced.

## Independent review and diagnostic corrections

Read-only GPT-6.1 Sol / High review found two structural issues: non-decision
continuation forks introduced uncounted viewer choices, and rejecting the
unrestricted minimum above the receiving option cap could miss a larger feasible
shape. Planner v2 gives non-decision nodes one continuation and searches within
the receiving capacity. A regression admits the 16-node, two-choice/seven-ending
shape with authored maximum seven and actual choices no larger than six. The
reviewer requalified both corrections with 32 focused tests and CLI checks.

Screenshot QA found the compact popup extending left of the viewport; a follow-up
review found multiple independent pins overlapping the compact dock. The repair
changed the shared state model and its focus/pointer priority. The reviewer
closed this finding after the focused unit regression; browser checks exercise
later-pin → earlier-focus/tap, exactly one visible explanation and popup bounds
at 1920/1440/1280/390 widths. An intermediate failure caused by incidental hover
after viewport resize is retained in the local trace and fixed by that priority.

The first diagnostic Python run had one failure because a changed, uncommitted
specialist skill could not match the trusted Git recovery pin. No pin checks were
weakened; the committed candidate passed all 1,150 tests before final qualification.
Diagnostic browser runs exposed obsolete binary fixture Briefs and old control
selectors; those fixtures now explicitly request their intended supported shape
and use current controls. Partial browser runs interrupted for demonstrated
popup corrections are not claimed as release gates.

## Executed verification

Ignored logs: `.local/creator-ui-*.log`; preservation captures and help failure
trace: `.local/source-entry-2026-10-04/` and `.local/creator-ui-2026-10-04/`.

| Check | Result |
| --- | --- |
| Frozen all-group Python sync / API F401 | Passed |
| Focused topology, branches, full downstream journey and outline settings | 55 passed |
| Frontend unit suite / types | 509 passed across 70 files; types passed |
| Archived prompt reader | Passed |
| Production frontend / deterministic checked static | Passed; committed bundle rebuild has no diff |
| Focused browser navigation/help/retained drafts | 27 passed |
| Focused directions/source round trip and frozen inputs | 2 passed |
| Final full Python gate | 1,150 passed in 427.34 seconds on the committed runtime candidate |
| Final unfiltered browser gate | 167 passed in 8.8 minutes, two workers; no filter/skips |
| Final wheel build / installed-wheel smoke | Passed |
| Remote CI | [Run 37257391441](https://github.com/Wenjun-Mao/plotloom/actions/runs/37257391441), full `browser_grep=.*`, started on the exact runtime candidate at `2026-10-05T02:56:47Z`; in progress at activation |

The Python gate retains the existing Starlette/httpx deprecation warning; the
production build retains the existing large-chunk warning. Neither was hidden
or bypassed. No supported checks were skipped or weakened.

## Activation and acceptance

Normal 8841 was stopped through the supported lifecycle at an idle native
checkpoint. Before-capture SHA-256:
`5572826eca3e9a0a047117c8e79cc9ebc614887978a8609448213d56e577473f`.
Both projects are preserved: 雨停以后 (`ee271b49-f384-414c-9711-452ee6333b84`)
and 风里的纸飞机 (`2f52cf22-3f4a-4f05-8dc3-4f55e76687b9`). The capture covers
74 table projections per project, seven API projections, 67/17 non-database file
hashes respectively and specialist settings.

The supported `manage.py start --data-root .local/creator-walkthrough` completed
successfully and verified the native bridge. Activation used the qualified
runtime candidate; later delivery documentation does not change its executable
source or relabel the executed revision.

- Container: `82d0e4f29bc22d66607600af060e612281e088cede443728c84d195d9592eed7`.
- Image: `sha256:0cc23a0d344d632bef8d669d754583bbfc434dd94e505b9ea7a03f467ab48261`.
- Start: `2026-10-05T02:56:49.719241636Z` (October 4 Toronto).
- Container / `/healthz`: healthy / `status: ok`.
- OpenAPI exposes the branch-suggestion routes and structured Brief fields.
- Served JavaScript SHA-256: `bfc18c5e54d00b4ecc693e410eda509a44cd94a312b7b45be0c1c20e07b9cc04`.
- Served CSS SHA-256: `051ebce9a982b0517a30183eae0bb02f34c0a604740c683b8e3b4d1fad603cfc`.

Both served assets match the committed bytes. After-capture SHA-256:
`356fa42d42e780d90272545f7662658973017ee09938c239f4e3711e941e7727`.
The comparison requires exact equality of all database table rows, all captured
project-home file hashes and specialist settings. All passed (54/21 rows,
67/17 files). No tables were added. API changes are limited to empty direction
selection defaults and the nullable/empty general-map fields in the retained
binary projection; normalization permits only these additive defaults. All
other projections match. This is row/projection/file equality, not a claim of
whole-SQLite-file byte equality. Deployment configuration, credential hash/mode/
ownership and specialist settings also compare exactly in the protection check.

Both original accepted outline r1 reports remain available and match the retained
report files byte-for-byte. The native registry is idle (`busy: false`,
`activeTasks: []`). No send, cancel, acceptance, source/Brief save, lifecycle
mutation, reset, copy, deletion or H3 activation was used on either owner project.
The owner's browser was not refreshed or operated; unsaved browser input was
left intact. Implementation and fixture verification are complete; remote CI
and the owner's fresh walkthrough remain the next acceptance steps.

The 8851 completed-media copy, H3 configuration/credentials, specialist bindings,
Chinese manual and V1 source were not changed. Tests use disposable fixtures and
deterministic transport; no live model/media generation or creative acceptance
is claimed. The owner’s new walkthrough remains the usability acceptance step.
Existing records provide no task-level usage/cost delta; none is invented.
