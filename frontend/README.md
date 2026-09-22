# Plotloom · 叙织 workbench

This directory is Plotloom's standalone React/TypeScript workbench. It uses the
versioned `/api/v2` contract and intentionally has no dependency on a parent
npm workspace or a legacy browser application.

## Layout and build contract

`index.html` is the Vite entry point and `src/main.tsx` starts the application.
`vite.config.ts` builds the reviewed production bundle into
`../src/plotloom/static/`, where the Python wheel can serve it. The public
workbench mount remains `/v2/`; the API remains `/api/v2`.

The development server listens on `127.0.0.1:5173` and proxies `/api/v2` to
`http://127.0.0.1:8775` by default. Set `PLOTLOOM_API_ORIGIN` to target another
backend origin.

Provider secrets are never part of project state or provider settings. A
browser-entered key is stored only in `sessionStorage` under Plotloom's key and
is sent only as `X-Plotloom-Session-API-Key` for requests that require it.

## Commands

```sh
npm ci
npm run typecheck
npm test
npm run dev
npm run build
npx playwright install chromium
npm run test:e2e
```

The E2E suite typechecks its fixture, starts `uv run plotloom` and this Vite
server on dynamically allocated loopback ports, and uses temporary SQLite and
artifact storage. It never contacts a real provider.

## Portable F3B presentation fixture

The environment/prop review demo is an explicit mock-only, read-only surface
that reuses `ArtReferenceGallery`; it is not a workbench route or API mode. It
serves five distinct static SVG cards for each isolated scene and prop subject,
and its controls cannot write project or provider state.

```sh
node e2e/f3b-mock-demo-api.mjs --port 8794
PLOTLOOM_API_ORIGIN=http://127.0.0.1:8794 npm run dev -- --port 8793 --strictPort
```

Open `http://127.0.0.1:8793/v2/e2e/f3b-mock-demo.html`. Both processes are
loopback-only and can be stopped when inspection is complete.

## Portable F3B reference-decision simulator

`f3b-reference-decision-demo.html` is a separate, local-state-only walkthrough
of explicit environment/prop choice and replacement. It reuses the production
gallery but its buttons only update React state in that tab. Its cards are
inline static SVG data URLs, so it makes no project/API request, provider,
project-storage, or creative-approval claim. The existing read-only fixture
remains unchanged.

With a Vite server running, open:

`http://127.0.0.1:8793/v2/e2e/f3b-reference-decision-demo.html`
