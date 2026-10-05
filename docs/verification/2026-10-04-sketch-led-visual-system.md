# Sketch-led visual system delivery

Status: independently reviewed, locally qualified, published and activated.
Owner walkthrough acceptance remains pending; remote CI is in progress.
Authority: [approved visual assignment](../roadmap/2026-10-04-sketch-led-visual-system.md).
Baseline: retained clean `main` at `f570e3e`; that approved-scope commit remains
in the history. Executable candidate: `7eef6aac85786f729f781f41416b0178c0ef2cb8`
(includes visual commit `fd7a028` and the reviewed narrow-overlay correction).
Final qualification and delivery occur October 5, 2026, Toronto time.
One source owner implemented through the Relay Deliver
reporting route; the manager remained read-only. No graph-centred workflow,
mode toggle, new navigation model or placeholder capability was introduced.

## Owning diagnosis and implementation

The presentation layer had repeated role definitions, tiny metadata, oversized
headings, nested bordered groups and competing equal-width Source columns.
[ADR 0119](../adr/0119-current-workbench-visual-roles.md) records the repair:
consolidate exact later declarations into their owning rule, split the oversized
stylesheet into shell/readers, media/tools and authoring modules, and use shared
19px workspace / 16px section / 14px body / 12px support roles. Narrative titles
retain a deliberate 24–36px scale with 15px reading prose.

Dark surfaces, gold actions/selection, restrained borders, spacing and control
roles now carry through shell/onboarding/directory, Brief/settings/presets,
Source/tasks/accepted reports/branches, characters/art/reference views,
script/storyboard/production/media controls, reader/player and professional tools.
Critical instructions, errors, retained acceptance/currentness and next actions
remain visible. Custom preset additions use native disclosures; authored values,
selected presets and free text retain their existing state and input contracts.

Brief directions share columns where space permits, Source separates authoring
and task work from full-width accepted reading/map editing, and narrow creator
links use a horizontal rail. The existing graph inspector moves beside the
canvas only when actual editor width supports it. A definite flex canvas height
fixes the React Flow sizing contract exposed by that side layout. Selection,
focus and unsaved input remain owned by the existing editor. Grouped help retains
hover/focus/tap/Escape and one active explanation, with a small label-aligned ⓘ.

## Independent review and diagnostics

GPT-6.1 Sol / Medium performed read-only source and screenshot review against
the retained sketch. Its one P2 finding was a desktop preset disclosure rule
placed after the narrow 44px target rule. Moving the owning desktop rule before
the responsive rule fixed the cascade; the reviewer independently closed it.
A rendered-height assertion at 390px guards the repair. Manual viewport review
then exposed inherited modal widths exceeding their padded container. The reviewer
confirmed this in-scope blocker and independently closed the owning repair:
container-relative widths, bounded height and narrow directory identity/action
stacking. All four visible overlay bounds now have rendered regression assertions.
The reviewer did not run tests or operate the owner browser.

Diagnostic captures exposed the graph canvas sizing issue above. Test setup
corrections scoped directory close to its footer, established keyboard modality
before checking focus-visible, cancelled a prepared publication before editing
Source, and allowed the existing quarantine count in the button name. Persisted
project drafts safely flush through their existing store; the capture fixture
no longer incorrectly expects a dialog on that navigation. Existing structure
unit/browser selectors now target `.brief-settings` rather than the first details
inside Brief, preserving their default-open/manual-collapse/value assertions.
These failures and interrupted diagnostics are retained, not claimed as gates.
The preliminary broad run was stopped before source edits for the modal correction
(115 browser checks passed before interruption); final full gates qualify the
corrected bytes.

## Executed verification

Ignored logs/captures: `.local/sketch-led-2026-10-04/`. Before views cover Brief at
1920/1440/1280/390. `final-views/` contains actual product fixtures at
1920/1280/390; `overlay-qualified-views/` retains their corrected final captures,
including populated directories, accepted/current and stale reports, waiting,
failed reads, dirty Source input, reader/player, all six professional tools,
assistant settings and DOM media consent. The 27-node graph stress fixture checks
navigator/detail scroll, retained identity/input and nonzero rendered canvas;
it does not establish the creative quality of long-graph layout.

| Check | Result |
| --- | --- |
| Frozen all-group dependency sync / API F401 | Passed |
| Frontend unit / types | 509 passed across 70 files; types passed |
| Archived prompt reader | Passed |
| First focused UI/graph/settings / journey checks | 7 passed / 15 passed |
| Final visual journeys | 5 passed; all visible sampled label/support roles ≥12px and contrast ≥4.5:1, viewport bounds, keyboard/help focus/Escape, 44px narrow targets, reduced motion, retained dirty identity and consent cancellation |
| Final focused Brief/preset round-trip / overlay, consent and draft regressions | 6 passed / 20 passed |
| Production frontend / deterministic static | Passed; committed bundle rebuild has no diff |
| Full Python gate | 1,150 passed; one existing Starlette/httpx deprecation warning; 455.15s |
| Full unfiltered browser gate | 172 passed; 9.3 minutes |
| Wheel / installed-wheel smoke | Passed |
| Remote CI | [Run 37262414456](https://github.com/Wenjun-Mao/plotloom/actions/runs/37262414456), dispatched with `browser_grep=.*` on exact executable `7eef6aa`; in progress at handoff |

The existing large-chunk build warning remains visible. No supported check was
weakened or skipped. Deterministic fixtures and fake transports establish technical
behavior; no generation/provider call or creative/media approval is claimed.

## Activation and preservation

Normal 8841 was stopped through the supported lifecycle after a captured native
checkpoint (`busy: false`, `activeTasks: []`), before replacing its mounted static
bytes. Initial and pre-stop captures are exactly equal. All gates passed before
publication. A refreshed remote-divergence check found three local commits ahead
and zero remote-only commits; `main` was pushed at the exact executable revision
`7eef6aa`, including the retained approved-scope commit. CI was dispatched on that
revision before this documentation-only delivery record.

The supported `manage.py start --data-root .local/creator-walkthrough` recreated
the normal workbench. Container
`2bb6541e378aab78486e3740ea0f9f5a044b03faee6698dc3e16ee1eb0d1e714`, image
`sha256:b56ceadd56fb1bd5433de37eb06961a315ce574aa189bfa20c89300cccdaead2`,
started `2026-10-05T04:11:22.44274287Z`; native lifecycle status reports healthy
and `check-bridge` confirms availability. `/healthz` returns `status: ok`.
All seven served static files match the frozen committed SHA-256 manifest.
Four fresh read-only Chromium captures of normal Source/Brief at 1440/390px
passed viewport checks with zero API mutation attempts; retained in
`normal-activated-views/`. No backend/schema change was required.

Preservation covers both owner projects: 雨停以后
(`ee271b49-f384-414c-9711-452ee6333b84`) and 风里的纸飞机
(`2f52cf22-3f4a-4f05-8dc3-4f55e76687b9`).
The capture retains complete table projections, seven API projections per project,
non-database project-home file hashes and specialist settings. Protection captures
hash/mode/ownership of deployment configuration, credential and specialist settings
without copying or displaying credential bytes. After-activation captures are
strictly identical to the originals across both projects: 74 tables each,
54 retained rows / 67 non-database files for 雨停以后 and 21 rows / 17 files for
风里的纸飞机, accepted outlines still at r1, all API projections and specialist
settings unchanged. All three
protected file hashes, modes and ownership match. The complete equality assertion
and served-byte verification are retained in `activation-summary.json`.
No owner story save/send/cancel/acceptance/reset/delete/copy was performed;
no owner Safari session was operated or refreshed. 8851, V1, H3 configuration,
Chinese manual and Relay documentation cleanup remain untouched.

Implementation, local qualification, publication/activation, remote CI and owner
walkthrough acceptance are separate outcomes. Existing records provide no task
usage/cost delta; none is invented.
