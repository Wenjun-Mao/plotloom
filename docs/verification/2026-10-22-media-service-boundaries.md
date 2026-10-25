# Independent media-service packaging — 2026-10-22

> Only QA artifacts listed in the [2026-10-25 cleanup scope](../roadmap/2026-10-25-top-five-cleanup.md)
> were retired. References to those artifacts describe historical
> runs, not available files or current launch/recovery instructions.
> Recorded outcomes and limits stand.

Status: **IMPLEMENTED, VERIFIED AND DEPLOYED.** Implementation source `37828fd3`.
Baseline `5fd5128b`, retained `codex/h3-ref2va-gateway` specialist checkout.
The [approved plan](../roadmap/2026-10-22-media-service-boundaries.md) and
[decision](../adr/0216-media-services-monorepo-boundaries.md) define scope.

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

Final locally built Linux ARM64 OCI index identities (both isolated smokes passed):

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

## Coordination and serving acceptance

The owner explicitly authorized coordination with `narrative-forge main`. The
director confirmed separate retained-branch source ownership, required later
reconciliation of documentation indexes/ADR numbering, and reserved Spark for
its live native-image/H3 E2E. No director checkout or installed Plotloom was edited.
The director received the local verification summary and proposed cutover scope.
Read-only byte comparison also matched every file in the serving gateway's
25-file package and dashboard's 21-file package against this source. The new
common distribution includes both entrypoints; it does not change those bytes.

The local implementation checkpoint deliberately held deployment. The director
subsequently cancelled its new native QA run with adopted text preserved and no
H3 submission, then explicitly released the quiet window. Its historical Mac
UNKNOWN image attempts were outside this cutover and were not touched.

Fresh Spark checks found no gateway nonterminal/unknown jobs, no unfinished lane
entries, no queued/running/unknown Lab work or unreleased grants, and no ComfyUI
queued/running prompts. Both exact transferred ARM64 artifacts passed isolated
`--network none` installed-package smokes on Spark before promotion.

The dashboard was replaced first at **15:26:46 UTC / 11:26:46 Toronto**. A
post-replacement assertion stopped because Mac Docker reported the OCI index ID
while Spark reported the image config ID. The service was healthy. The exported
`manifest.json` maps each tag to the exact config digest below, and both rootfs
layer lists matched across hosts. The operator check was corrected at that layer;
no service code, image bytes or validation contract was changed, and the dashboard
was not needlessly replaced again. Isolation/mount/settings checks then passed.

After a fresh idle check, the gateway was stopped, persistent state rechecked for
racing admissions, and its original container retained for rollback. The new
gateway started at **15:29:30 UTC / 11:29:30 Toronto**. Operator environment
overrides were preserved privately over the new image defaults; no old source-tree
`PYTHONPATH` was copied. Credentials never entered commands/receipts. Mounts match;
no second worker ran against live data.

### Exact deployed artifacts

Release source/config/operator evidence root on Spark:
`/home/wjmao/services/plotloom-h3-gateway/releases/media-service-boundaries-20261022-37828fd3/`.
The service Compose files and smoke helper are under `services/minimax_h3_gateway/`.
Dashboard Compose project remains `plotloom-h3-dashboard`; gateway remains a
directly created container with its installed `plotloom-h3-gateway` entrypoint.

| Service | Spark image config digest | Serving container |
| --- | --- | --- |
| Dashboard | `sha256:46236b29450af391650dc234e9e51a402caf33d221bcebb44ffd206af8239d11` | `7c4f2909182efa3a3b014f336bfe8e6f4394286ecc099bbbe54898c20c7edb24` |
| Gateway | `sha256:16137351b8103d812a02680fe054703007529c1b0631d23b5a3ce525d5dd38c4` | `ea78201826381058704b0c478c06c90580f2d350e30e781b36332e2897e14fa9` |

Both use their `:20261022-service-boundaries` tags. The preceding OCI index
digests describe the local/export artifact, not Spark's config IDs.

### Preservation and consumer checks

- All gateway and Lab table row fingerprints matched before/after: 174 gateway
  jobs, 126 lane records, 3 published voices and 2 takes, plus remaining tables.
- File size/mtime manifests matched for 138 gateway assets/outputs and 12 Lab
  voice/take files. This is scoped metadata evidence, not a byte-hash audit of all
  Comfy/model/input storage. No reset, migration, copy-back or manual cleanup ran.
- ComfyUI, embedding and playground container IDs/images/start times matched;
  Voice Lab and SGLang systemd PIDs/start timestamps matched. Their runtimes,
  model mounts and settings were not restarted or edited.
- Gateway health `ok`, queued/active zero; Lab healthy/worker idle; Qwen backend
  health HTTP 200; Comfy queue empty. Dashboard Docker health is `healthy`.
- Authenticated gateway status and original-output GET passed for existing job
  `h3_f28efec4ce59466f954b1660faa63187`. Both existing take metadata/audio GETs through
  the gateway facade passed, with source-audio hashes verified.
- Real private HTTPS preview/playback, seeking to 3 seconds, original download
  and refresh passed. MP4 duration 5.167 seconds; no media or console errors.
  Download SHA256 matches the stored original:
  `9abfeb93c27893a12acf5cc9bd61eed6ffdda76b220dab398f90d95eda54b4f9`.
  The [1440×900 serving screenshot](supporting/media-service-boundaries-spark-20261022.png)
  was visually inspected. The owned Chrome session was closed afterward.
- Tailnet-only `https://gx10-1523.tail6040ad.ts.net/dashboard` remains the same
  handler to `127.0.0.1:8091/dashboard`; no Tailscale configuration changed.

No inference or generation replay occurred. Exact identities, health and the
released quiet window were reported back to `narrative-forge main`, which will
re-preflight before its next H3 batch. Operational evidence is retained in
`before.json`, `dashboard-activated.json`, `gateway-activated.json`, `after.json`
and the one-off `cutover.py` at the release root (also locally under `.local/`).

### Rollback references

- Gateway: `plotloom-h3-gateway:vae-d-20261006`, image
  `sha256:f833c3469ea62c94c428ea5d98e0e8236fc317dd6a6721a8a4f7c7d51e6ad692`;
  directly created container, not assumed Compose-managed.
  Original container `4020bc9e8dff13da68ca839f91e142f53e5104df60e8257f4cc22400520a42d6`
  remains stopped as `plotloom-h3-gateway-before-packaging-20261022`, with restart
  policy `no`. After fresh idle checks, stop/retain the candidate, restore the old
  name and `unless-stopped` policy, then start the predecessor as the sole gateway.
  Do not roll back/reinitialize data. Unknown or racing work blocks this procedure.
- Dashboard: `plotloom-h3-dashboard:20261022-output-actions-2`, image
  `sha256:dbae86250c22faa321625ff39b7e1efef60e635702424ab1c7d3418e6029aa4d`;
  Compose file under
  `/home/wjmao/services/plotloom-h3-dashboard/releases/20261022-output-actions2.zLJ3ON/services/minimax_h3_gateway/`.
  The previous image/config remain available; dashboard rollback uses that Compose
  file/project with `up -d --no-deps --no-build dashboard`, without restarting gateway.
- ComfyUI: `sha256:db0010004575a508b5ac67fb36ea4ab83cf1964a84e70932019749f330c64110`.

Full Plotloom/frontend suites were not repeated: no authoring/frontend/build
contract changed, and focused extraction/client checks passed. No merge, push,
hosted CI or product integration acceptance is claimed. The approved packaging
and selective-deployment plan is complete; no new model/creative qualification
is implied by these operational checks.
