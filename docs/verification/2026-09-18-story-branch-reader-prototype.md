# Story-and-branch reader prototype verification

Date: 2026-09-18. Scope: the approved representative U2 reader only.

## Contract checked

`?view=story-prototype&project=<project-id>` is an opt-in read-only frontend
surface. It requests the existing project, canonical `story_graph` stage, and
accepted F4 script. Routes come from the existing `deriveRoutes` owner;
`sectionBindings` select the already accepted episode for each graph node.
No API mutation is available from this view.

The browser proof creates a disposable F1B/F4 current-contract project from
the retained beacon/dock screenplay fixture. It confirms the opening and both
ending branches, then selects the dock branch and verifies that the beacon
episode is absent from the route reader. Network observation confirms that the
page itself made no non-GET `/api/v2/` request.

## Commands and results

From `frontend/`:

```text
npm run typecheck
# passed

npm test
# 18 files, 164 tests passed

npm exec playwright test -- --config playwright.config.ts e2e/story-prototype.spec.ts
# 1 test passed; browser interaction and no-write assertion

npm run build
# passed; refreshed src/plotloom/static/
```

The first attempted unit command appended Jest's unsupported `--runInBand`
flag; Vitest refused it before running tests. The native command above then
passed. A rejected cleanup command using `rm -rf test-results` was not run.
The complete final command output is retained in
[`2026-09-18-story-branch-reader-prototype.log`](2026-09-18-story-branch-reader-prototype.log).

## Visual evidence

Headless Chromium screenshots were inspected after the passing browser run:

- `frontend/test-results/story-prototype-reads-the--3aa0b--screenplay-without-writing/story-prototype-1440.png`
  — 1440 × 3936, opening and beacon route.
- `frontend/test-results/story-prototype-reads-the--3aa0b--screenplay-without-writing/story-prototype-768.png`
  — 768 × 4371, dock route after selection.

At both widths the first viewport contains a single navigation/header, current
script revision, opening-to-two-ending map, current route focus, and a readable
screenplay column. The narrow layout stacks the branch map and collapses the
screenplay metadata without horizontal clipping.

## Reproduce manually

Run a backend that serves an existing project with a ready `story_graph` and
accepted F4 script, then from `frontend/` run:

```text
PLOTLOOM_API_ORIGIN=http://127.0.0.1:8775 npm run dev
```

Open the exact route shape:

```text
http://127.0.0.1:5173/v2/?view=story-prototype&project=<accepted-f4-project-id>
```

This is a UI prototype only. Browser/test success is not human usability or
creative acceptance; it does not approve media generation or connect F5 review
to production media.
