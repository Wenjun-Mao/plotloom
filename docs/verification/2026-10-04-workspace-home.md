# Workspace Home delivery

Status: implemented, independently reviewed, locally qualified, published and
verified on normal 8841. Creator usability acceptance remains separate; full
remote CI is running.

Runtime source: `6a2075fb20d8b433c86139081c74da44c90f1409` on published `main`.
Scope: [approved Home add-on](../roadmap/2026-10-04-workspace-home.md).
Contract: [ADR 0115](../adr/0115-workspace-home-navigation.md).

## Outcome

The upper-left brand is a native **返回首页** button with a visible **首页** cue,
hover feedback and the existing keyboard focus treatment. It returns to the
existing start screen through the draft-gated navigation owner. Explicit Home
intent distinguishes clean blank/sample sessions from ordinary local page
changes; both otherwise share an empty persisted project ID. No raw link,
reload-based reset or lifecycle bypass was added.

Unsaved local Brief input retains Save/Discard/Cancel. Durable Brief navigation
waits for draft admission; failed admission retains the editor. Source review
buffers remain recoverable without source confirmation. Saved-project history
still works. Home never closes, archives, deletes, cancels, approves or generates;
the control is disabled during hydration, canonical saves, lifecycle transitions
and snapshots. Public APIs and backend schemas did not change.

## Verification and review

- Targeted Home/navigation/owner unit checks: 21 passed.
- Full frontend unit suite: 480 passed across 64 files.
- Frontend and browser typechecks: passed.
- Deterministic production build and whitespace checks: passed; existing
  large-chunk warning remains.
- Browser Home, navigation shell, source workflow and save/force-close checks:
  28 passed in 1.1 minutes with two workers. This is a focused local gate, not a
  claim that the entire browser suite was rerun.
- GPT-6.1 Sol / Medium independently reviewed the source, read-only, and found
  no remaining findings. It ran 18 Home/loading-navigation unit checks and
  inspected browser scenarios; it did not independently execute browser tests
  or normal-installation acceptance.
- Full remote [CI 37243705853](https://github.com/Wenjun-Mao/plotloom/actions/runs/37243705853)
  is running on the exact runtime source with `browser_grep=.*`; not yet a
  passed release gate. The prior deletion CI is a separate run.

Initial browser failures were new-test errors, not changes to the product's
draft contract: exact raw labels included help text or a hidden required star,
and a saved title assertion incorrectly assumed a flat directory field. The
revised locator uses the textbox's accessible name; the API assertion now uses
the typed current `ProjectListResponse` and `brief.title`. First, second and
third failure traces were preserved before reruns. The final scoped browser
command passed unfiltered within its four selected files.

Evidence is under `.local/workspace-home-2026-10-04/`, including `unit-full.log`,
`build.log`, `browser-final.log`, the three retained failure folders, captures
and live screenshots. Checked and served bundle SHA-256:
`cd61a0eeb80b4e0cff8254c9329d0eb5c8d3e2396e552c574043a3807d5bd5e6`.

## Normal installation and preservation

Normal 8841 already serves the checked frontend from its read-only source bind
mount. No API process, Docker container or bridge restart was necessary. The
existing healthy container remains
`332d33f1f9109999afdf4fb9d1d3193973f4105fa20635a1c6e566a169d9117f`,
started at `2026-10-04T23:07:27.723137248Z` before this add-on.

A fresh background browser tab loaded 雨停以后, showed the branded Home control,
and returned to **从一个项目开始** without editing or saving anything. The tab
was then closed; the user's original tab was not reloaded or modified.
`live-home-control.png` and `live-home-landing.png` record the control and result.

This task's directory baseline contains one current project, not the two-project
baseline from the preceding deletion assignment. End-of-slice all-status
enumeration also confirms that one active/open row. No project was deleted,
restored or recreated by this Home implementation. Before/after/published
captures compare equal across project metadata, 74 project tables, 67 owned
file hashes, API projections, 12 application tables and specialist settings.
Capture SHA-256:
`683b5fe5bff25ba23291e6d878207a77c2c39ce6d55584d948f5246dbead9a31`.

The Chinese manual remains unchanged at SHA-256
`c44adfddba45a4db4a3e5e5d0a9fcc376278a3baeaed502f9b8259c934e30db8`.
No generation, cancellation, credentials, H3, V1, retained 8851 or broader
contract-audit work belongs to this add-on.
