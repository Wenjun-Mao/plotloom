# Independent media-service packaging — 2026-10-22

Status: **LOCALLY IMPLEMENTED AND VERIFIED; DEPLOYMENT PENDING.**
Baseline `5fd5128b`, retained `codex/h3-ref2va-gateway` specialist checkout.
The [approved plan](../roadmap/2026-10-22-media-service-boundaries.md) and
[decision](../adr/media-services-monorepo-boundaries.md) define scope.

## Root cause and change

Gateway build ownership was incomplete: dependencies were hand-pinned in a
Dockerfile, and the dashboard installed Plotloom's root dependency set. Both
builds used a repository-root context. These were packaging boundaries, not a
reason to split the repository or redesign generation.

- Service-owned `pyproject.toml` and `uv.lock`; two console entrypoints and
  separate dashboard/gateway images built only from the service subtree.
- Non-editable installed packages include workflow JSON and dashboard assets;
  no source-tree `PYTHONPATH`, Plotloom installation or model frameworks.
- Dashboard omits gateway-only Pillow and retains its independent, non-root,
  CPU-only, read-only-data deployment. Its protected forwarding contract and
  private SQLite schema coupling are unchanged.
- Static import guards protect the three runtime owners. They are regression
  checks, not a runtime sandbox or a promise of arbitrary version compatibility.
- New maintenance entrypoint documents ownership, independent environments,
  selective checks/deployment, rollback and the differing data lifetimes.
- Production gateway/dashboard/Lab Python and JavaScript, Plotloom client code,
  root locks, APIs, database schemas, models and generation behavior are unchanged.

## Dependency reconciliation

Serving versions were inventoried before locking. The gateway's exact runtime
dependency closure is preserved, with Python 3.12.14. The dashboard keeps its
direct dependency versions and Python 3.12.15, while aligning three shared
transitives to the already-serving gateway: AnyIO 4.14.2 → 4.15.1, IDNA 3.19 → 3.20,
urllib3 2.7.0 → 2.8.0. Unused Plotloom database/template dependencies and Pillow
are absent from the dashboard artifact. No inference dependency was added.

Service lock SHA256:
`023b29e28d045d44610fe5425123d02403bfabe10d1fd59338607454f2fbf15c`.

Final locally built Linux ARM64 image identities (both isolated smokes passed):

- `plotloom-h3-dashboard:20261022-service-boundaries`:
  `sha256:e0cc6b0d0f702a19f52c50f6d50130791ab8c9f1b3a0da0a37db274c65aafc79`.
- `plotloom-h3-gateway:20261022-service-boundaries`:
  `sha256:6f1a6c9f4d802c850c54d97835a27b52106c188a84bcd8c1de13b6d3292ff32b`.

## Local verification

| Check | Result |
| --- | --- |
| Service locked, non-editable gateway suite plus import boundaries | 239 passed, 2 deprecation warnings |
| Dashboard Node UI suite | 14 passed |
| Voice Lab own locked environment, from its directory | 80 passed, 1 deprecation warning |
| Voice Lab wheel build | Passed |
| Plotloom extraction/import/H3 transport checks | 34 passed |
| Clean gateway and dashboard installed-wheel smokes | Passed, unrelated working directory, no Plotloom/source-path dependency |
| Linux ARM64 images built locally; both run with network disabled | Passed, zero generation calls |
| Focused Ruff / patch checks | Passed |
| Independent GPT-6.1 Sol / Medium review | No material findings; independently passed 9 packaging/boundary tests |

Commands are recorded in the [service README](../../services/minimax_h3_gateway/README.md#independent-package-checks-and-images)
and [maintenance entrypoint](../operations/media-services.md). Artifact smoke uses
temporary data and deliberately unavailable model backends: gateway health must
return the existing `503 comfy_unavailable`, not claim model readiness. Dashboard
viewer mode serves packaged assets, does not create a missing database, and
refuses submission without its dedicated key. Existing service fixtures cover
configured forwarding and incompatible-schema failure.

The initial Lab command incorrectly ran pytest from the repository root while
selecting the Lab environment; it collected unrelated Plotloom tests. Running
from the documented Lab directory passed. Two early smoke assertions incorrectly
assumed a flat workflow JSON and healthy absent backends; both were corrected
against owning contracts before the final passing runs. No production contract
was weakened. An initial browser navigation raced fixture startup; navigation
after the ready signal passed.

### Real browser, temporary records and retained media

Headed Chrome used the installed service against a disposable file-SQLite fixture.
It submitted one URL-image request through the dashboard and real FastAPI
admission, with the worker disabled and a local fake delivery transport. No
external image fetch, model call, serving data or new generated media was involved.

Passed: blank list, fixture submission, selected job/deep link, preview, native
playback, seeking, refresh, return-to-list/preview navigation, settings reuse and
native original-file download. Playback advanced from 1 to 2.15 seconds; seeking
to 3 seconds completed with no media error. Browser console had no warnings/errors.
The 1440×900 [screenshot](supporting/media-service-boundaries-preview-20261022.png)
was visually inspected. Its request metadata is a five-second fixture; its media
is the deliberately reused 15.083-second clip, not a duration-generation assertion.

Downloaded bytes match the source SHA256:
`e06de02f2f7a132a01b349e3ca44b9701383741f74318fd66cccf1ef68f69299`.
Owned fixture server and Chrome session were stopped. Scratch evidence was moved
from `output/playwright/` to `.local/media-service-boundaries-20261022/playwright/`
after verification, with no evidence discarded.

## Coordination and pending serving acceptance

The owner explicitly authorized coordination with `narrative-forge main`. The
director confirmed separate retained-branch source ownership, required later
reconciliation of documentation indexes/ADR numbering, and reserved Spark for
its live native-image/H3 E2E. No director checkout or installed Plotloom was edited.
The director received the local verification summary and proposed cutover scope.
Read-only byte comparison also matched every file in the serving gateway's
25-file package and dashboard's 21-file package against this source. The new
common distribution includes both entrypoints; it does not change those bytes.

**No Spark serving restart, deployment, model change or generation has occurred
in this slice.** Local ARM64 execution is not a substitute for target-host smoke
and private-HTTPS serving verification. Wait for explicit quiet-window release,
then perform the plan's fresh gateway/Lab/shared-lane/native-queue checks before
any replacement. Preserve uncertain work rather than replaying or clearing it.

Observed rollback baseline (read-only inventory, not a current idle assertion):

- Gateway: `plotloom-h3-gateway:vae-d-20261006`, image
  `sha256:f833c3469ea62c94c428ea5d98e0e8236fc317dd6a6721a8a4f7c7d51e6ad692`;
  directly created container, not assumed Compose-managed.
- Dashboard: `plotloom-h3-dashboard:20261022-output-actions-2`, image
  `sha256:dbae86250c22faa321625ff39b7e1efef60e635702424ab1c7d3418e6029aa4d`;
  Compose file under
  `/home/wjmao/services/plotloom-h3-dashboard/releases/20261022-output-actions2.zLJ3ON/services/minimax_h3_gateway/`.
- ComfyUI: `sha256:db0010004575a508b5ac67fb36ea4ab83cf1964a84e70932019749f330c64110`.

Full Plotloom/frontend suites were not repeated: no authoring/frontend/build
contract changed, and focused extraction/client checks passed. No merge, push,
hosted CI or product integration acceptance is claimed. Completion of the full
plan still requires coordinated deployment and its receipt update.
