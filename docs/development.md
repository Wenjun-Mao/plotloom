# Plotloom developer guide

## Product flow

```text
ProjectBrief
  -> StoryBible
  -> StoryGraph (DAG + joins)
  -> SceneBeatPlan
  -> Storyboard (Shot + ShotBeatLink)
  -> package-owned, versioned media prompt compiler
  -> one-shot image/video tasks
```

A valid first run may advance through all four canonical stages. Editing a stage creates a new revision and marks downstream stages stale; it never spends provider credits until the user explicitly starts a rebuild.

## Repository shape

```text
src/plotloom/       Python domain, API, persistence, prompts, migrations, built UI
frontend/           React/TypeScript source, unit tests, and Playwright tests
tests/              Python contracts, integration tests, and release boundary gates
docs/adr/           durable architecture decisions
docs/roadmap/       capability-based progress tracking
```

The frontend build writes directly to `src/plotloom/static/`, so an installed wheel is a complete single-process local application.

## Development commands

```sh
uv sync --all-groups
npm --prefix frontend ci

# terminal 1
uv run plotloom

# terminal 2
npm --prefix frontend run dev
```

The production server defaults to `127.0.0.1:8775`; the Vite server defaults to `127.0.0.1:5173`. Open `/v2/` on either origin. `PLOTLOOM_API_ORIGIN` changes the Vite proxy target.

## Data and secrets

- A source checkout defaults to `data/plotloom.sqlite3` and `data/artifacts/`.
- An installed wheel uses the OS user-data location: `~/Library/Application Support/Plotloom` on macOS, `%LOCALAPPDATA%\\Plotloom` on Windows, and `$XDG_DATA_HOME/plotloom` or `~/.local/share/plotloom` on Linux.
- Only a source checkout loads its trusted repository-root `.env`; host environment values override it.
- Public provider settings are persisted. API keys are not.
- A browser key lives only in the current tab's `sessionStorage` and is sent as `X-Plotloom-Session-API-Key`.
- A run freezes public provider/model settings when queued. Image and video tasks freeze their own public settings.
- Remote instances must remain private or use an external authentication layer.

## Verification order

```sh
uv run pytest -q
npm --prefix frontend test
npm --prefix frontend run typecheck
npm --prefix frontend run build
git diff --exit-code -- src/plotloom/static
npm --prefix frontend run test:e2e
uv build --wheel
uv run python scripts/smoke_installed_wheel.py dist
```

The E2E fixture uses temporary SQLite and artifact storage, empties provider keys, and never contacts a live provider. Install Chromium once with `cd frontend && npx playwright install chromium`.

The distribution contract builds and probes a wheel in isolation. It verifies that all seven prompt templates, the production UI, migrations, LICENSE, and NOTICE are packaged, and that an installed release ignores an unrelated working-directory `.env`.
