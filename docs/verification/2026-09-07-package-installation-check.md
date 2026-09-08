# Package installation check — 2026-09-07

## Checkpoint

- **Tested source:** `70475ada584fa9fdaf671dd0f598fe4a233cf577` (`docs: establish bounded M1-C completion workflow`); worktree was clean before the report was created.
- **Observable outcome:** build one fresh Plotloom wheel, install it independently of the source checkout, and run the checked installed-wheel smoke contract.
- **Owned scope:** packaging and installation only. No provider call, browser journey, source/runtime edit, or generated-asset change was made.
- **Stopping condition:** one successful build and smoke run, or one diagnosed failure.

## Reusable source identity

| Input | Git identity |
| --- | --- |
| `src/plotloom` tree | `2b8e15d844cd0ba0631fe3872515bd0f2fe9290d` |
| `uv.lock` | `187236c39ed9ff02ab31f1dbc7347c53e4356f3b` |
| `pyproject.toml` / uv build configuration | `5614dfe596b705e8bcad772c78d04e91cc7a75f5` |
| `scripts/smoke_installed_wheel.py` | `4d4a63677d2c58bc5ee9fef4ee0a44276afbae55` |

The source checkout's full tree was `a5c7a1d3d3709b78c30c43a62f9f01475c4e9787`.
This evidence is invalidated by a change to the corresponding listed input.

## Commands and result

The wheel directory was newly created with `mktemp -d /tmp/plotloom-wheel-XXXXXX`, so no pre-existing wheel could be selected.

```sh
uv build --wheel --out-dir /tmp/plotloom-wheel-Us77Zr
uv run python scripts/smoke_installed_wheel.py /tmp/plotloom-wheel-Us77Zr
shasum -a 256 /tmp/plotloom-wheel-Us77Zr/plotloom-0.1.0-py3-none-any.whl
```

| Check | Exit status | Result |
| --- | ---: | --- |
| `uv build --wheel` | 0 | Built `plotloom-0.1.0-py3-none-any.whl` in the isolated output directory. |
| Installed-wheel smoke | 0 | Passed. |

Wheel SHA-256: `9e97db2115756087bb5c60349f59de25d6d270dc60ce95ec99475f0d65774275`.

The smoke script created a separate Python 3.12 virtual environment, installed
the wheel there, and ran from an unrelated working directory. It verified the
`plotloom` console entry point, all eleven prompt template IDs, `static/index.html`
and `static/workbench.js`, migrations 0001/0006/0007 and migration head, and
non-empty packaged `LICENSE` and `NOTICE`. It also used a poisoned unrelated
`.env` and an isolated home/data directory to confirm an installed wheel neither
loads that `.env` nor uses a source-checkout data path.

## Limitation and next action

This is a one-platform package/install contract at the tested source revision.
It is not a clean-machine upgrade/recovery test, full release acceptance, a
browser regression run, or a live-provider evaluation. No code change is
indicated; rerun this check after a package, runtime, dependency, or relevant
source identity changes.

Usage and cost telemetry were unavailable without adding instrumentation, which
was outside this check's scope.
