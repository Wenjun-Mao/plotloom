# Project save-and-close and force exit

Status: scoped implementation reviewed, locally qualified, published and
activated. Full remote CI remains in progress. Creator usability acceptance
remains separate.

Scope: the owner's approved save-and-close fix and directory force-close,
discarding this tab's unsent edits while leaving background jobs running.
Contract: [ADR 0113](../adr/0113-project-save-close-and-force-exit.md).
Plan: [bounded delivery](../roadmap/2026-10-04-project-save-close.md).

## Delivered boundary

**保存并关闭项目** saves recoverable author input before requesting the
existing quiescent folder-close gate. Partial Source, section-map, Cast, Art
and Script input uses bounded review buffers with exact draft CAS and its
original review basis. Restore is explicit; stale buffers cannot be applied
to newer authority. Saving input does not confirm, accept or generate content.
Preparation inputs that cannot safely become authoring drafts block ordinary
close with an explanation, rather than becoming implicit consent.

**强制关闭** requires DOM confirmation. It abandons unsent local edits,
settles already-started writes and preserves acknowledged server drafts,
canonical content and media. Jobs are neither cancelled nor inferred finished.
Busy or unknown server outcomes cannot become copy-safe closed folders. A busy
current project leaves the workspace while remaining open for background work;
forcing another project does not clear the current workspace.

The directory distinguishes 当前项目, 可打开, 已关闭·可安全复制 and
已归档·只读. **关闭窗口** only dismisses the directory. Project close is not
deletion; separately confirmed permanent deletion retains its existing scope.

## Root causes and review

The unloaded-project drain compared an absent revision with zero. Its shared
coordinator now normalizes the absent writer consistently; the server's safe
close contract was not weakened. New review editors previously held input
outside the legacy draft registry; the repair belongs in bounded authoring
persistence, not automatic canonical acceptance or whole-browser snapshots.

Independent GPT-6.1 Sol / Medium read-only review identified an in-flight discard
flush and stale section-map save. Queue abandonment now precedes flight waits,
and stale bases remain blocked. Held directory inspection exposed a competing
read lease and workspace ownership race: inspection completes before Close,
and ownership is captured before that wait. Cached row actions stay disabled
during inspection. Retained explicit-review guards and late recovery callbacks
bind to their original project/editor/authority session, preventing cross-project
input resets. Each correction has focused regression coverage. Final independent
review found no blockers; the reviewer did not rerun the latest owner tests or
interact with live data.

The second recovery failure's evidence and the two initial held-navigation test
interaction failures were preserved under `.local/save-close-2026-10-04/` before
changing the method. Interrupted broad runs are not counted as qualification.

## Executed verification

Runtime candidate: `c61d0195d7492d84837a8ef669bbe836dfb4d7a0`, published to
`origin/main`. The completion receipt update changes documentation only.

| Check | Result |
| --- | --- |
| Full Python suite | 1,088 passed in 345.62 seconds; existing Starlette/httpx warning |
| Frontend unit suite | 464 passed across 62 files on the final candidate |
| Frontend and browser type contracts | Passed |
| Production build | Passed; existing large-chunk warning |
| API and new-module F401 | Passed |
| Archived prompt reader | Passed |
| Wheel build and installed-wheel smoke | Passed |
| Focused save/force-close and lifecycle browser checks | 19 passed |
| Full unfiltered browser run | 153 passed in 8.4 minutes, two workers |
| Whitespace | Passed |
| Full remote CI | [Run 37233109002](https://github.com/Wenjun-Mao/plotloom/actions/runs/37233109002), in progress on the exact runtime candidate, `browser_grep=.*` |

Checked bundle SHA-256:
`ba7043fb86a96a35cf384916640e28ecd821c233ea70054ba6b1c019e131f1b9`.
Installed-smoke wheel SHA-256:
`456aa91856ffb10c6aba99979c046c9597ee7490e20d62096eae2007936423fe`.

## Normal activation and preservation

The supported `uv run --locked python services/creator_workbench/manage.py
start --data-root .local/creator-walkthrough` command successfully recreated
normal 8841 after a fresh quiescence check: both projects had zero generation,
image, video and media-task records, and the native specialist registry had
`busy: false`, `activeTasks: []`. The container is healthy, `/healthz` is `ok`
and the native Codex bridge is available. No schema migration or data copy was
needed for the bounded draft scope.

- Container: `377fb803a758966546ce0585d3b5ead80282918905435d573d6a733717752ac0`.
- Image: `sha256:d34531081f5944bee000e54d5e012e92a6bc742b3bbda2a0f60486b68463d177`.
- Start: `2026-10-04T20:42:19.482916766Z` (October 4, 16:42 Toronto).
- Served `/v2/workbench.js` matches the checked bundle hash above.

The read-only captures in `.local/source-entry-2026-10-04/` are byte-identical:
`before-save-close.json`, `preflight-save-close.json`,
`before-save-close-activation.json`, `after-save-close-activation.json` and
`after-save-close-browser.json`. `cmp` passed; their SHA-256 is
`086d881719da44ec2dd8978ad67dc76fb7de9a08453ce7f7d69a74a201930210`.
They cover both normal projects' 74 table projections each, seven API projections
each, two managed files for 风里的纸飞机 and 67 for 雨停以后, plus specialist
settings. The existing bridge credential hash is unchanged, and H3 remains
disabled. This is captured row/projection/file equality, not whole-SQLite-file
byte equality. Retained 8851 was not used or changed.

A fresh temporary background tab visibly showed the workspace close control,
both directory actions, 当前项目 versus 可打开, and the close-is-not-deletion
explanation. Force-close consent was opened and cancelled without dispatching
Close; **关闭窗口** dismissed the directory while Source and the project
remained open. The temporary tab was closed. No save, project close, generation
or acceptance action was used on either existing project. Mutation coverage
belongs to the isolated browser fixtures, not the creator's projects.

Live screenshots in `.local/save-close-2026-10-04/`:

| Evidence | SHA-256 |
| --- | --- |
| `directory.png` | `5de5c9f1f2c8e8b129a7d3a9713ea8ca4847f28f2c0eb27117248e065dcce9d2` |
| `force-consent.png` | `fa4c47d6a442b3abd1a7e41ada59449f235d734fca623d904202cb9638a223f2` |

## Deferred and next action

No Chinese manual edits, V1 changes, generation, creative acceptance, job
cancellation, real deletion, credential replacement or H3 activation.
The manual remains SHA-256
`c44adfddba45a4db4a3e5e5d0a9fcc376278a3baeaed502f9b8259c934e30db8`.
The existing creator tab will not be refreshed by automation: text unsent in
that old runtime should be copied before the creator refreshes it.

Scoped implementation stops here. The next product step is the owner's
continued new-project walkthrough, not additional automatic UI redesign or
manual synchronization. Pending remote CI is not represented as a passed gate.
