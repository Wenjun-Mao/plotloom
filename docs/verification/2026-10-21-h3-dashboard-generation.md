# H3 dashboard generation console — 2026-10-21

Status: **DELIVERED; SPARK PRIVATE HTTPS VERIFIED ON 2026-10-21 AFTER OWNER ACTIVATION.**

Owner approved the [single-image-generation console plan](../roadmap/2026-10-21-h3-dashboard-generation.md)
with “Good. Go”. Source implementation: `30c3df75`, retained specialist branch
`codex/h3-ref2va-gateway`; baseline `deebca11`. This does not release the broader
specialist integration/merge/push hold or contact the Plotloom director.

## Delivered boundary

Chinese H3 image-to-video form, upload or URL input, optional same-mode end frame,
quality1/2/3/8, six exact resolutions, duration5–15/default5, optional exact 63-bit
seed, aspect policies; accepted ID opens the existing selected-job/queue interface.
Native original-byte playback/download is retained. Settings reuse copies only
prompt/scalars and clears input media; it never submits. Drafts survive a rejected
submission, but are not persisted across browser reloads.

One fixed server-side POST targets the existing H3 API. It requires exact browser
origin/Host and a custom header; no arbitrary proxy, redirects or replay. The key
is a dedicated read-only mode0600/UID1000 file, not the entire gateway environment,
and never reaches browser responses. Data/media remain mounted read-only. No new
database, worker, scheduler, model, cancellation/deletion/batch/T2V/voice/Qwen control.

## Verification

- Final locked gateway plus extraction suite: **243 passed** (230 gateway,13 extraction),
  one existing Starlette/httpx deprecation warning. No deselections.
- Node UI regression tests: **5 passed**; targeted Ruff and whitespace checks passed.
- Independent GPT-6.1 Sol/Medium review identified two P2s: Unicode prompt byte
  allowance and numeric seed rounding. Both fixed at their owning boundaries;
  reviewer independently reran the two regressions:2passed, no material remaining finding.
- Initial multipart tests also exposed misuse of Starlette's context-manager wrapper;
  corrected to `async with request.form(...)` rather than awaiting away that wrapper.
  Initial tracking-boundary extraction test failed before new service files were
  staged; the unchanged gate passes after proper source admission/commit.
- Real headed Chrome on disposable FastAPI/file-SQLite fixture exercised start/end
  upload and JSON URL inputs through the **actual gateway admission API**, with its
  worker disabled and external source retrieval replaced by fixture-only bytes.
  Retained unchanged MP4 is explicitly playback fixture data, not new inference.
- Browser verified max seed9223372036854775807, explicit settings reuse/no dispatch,
  accepted ID selection, refresh persistence, uncertain committed-reply loss warning
  without retry, seek/play advancement, attachment download4080043bytes and mobile
  no-horizontal-overflow. Exactly3disposable jobs exist after3submissions; no replay.
- One browser assertion initially used a relative URL with Playwright's API client
  lacking a baseURL; corrected to an absolute URL without resubmitting any job.
  Initial fixture startup omitted its Comfy output override and refused `/comfy`
  creation; all fixture paths are now explicit under the disposable root.
- [Desktop screenshot](supporting/h3-console-desktop-20261021.png) and
  [phone screenshot](supporting/h3-console-phone-20261021.png) visually inspected.
  Fixture server/browser were stopped. Local fixtures and failed-run evidence remain
  inspectable; previous downloaded user videos were not modified/deleted.
- Main authoring frontend, wheel packaging and model/runtime are unchanged; their
  broad suites are not newly claimed by this narrowly scoped service verification.

## Spark deployment

Release `/home/wjmao/services/plotloom-h3-dashboard/releases/20261021.SN81Z5`.
ARM64 Docker build installs repository `uv.lock`, uv0.13.1. Image tag
`plotloom-h3-dashboard:20261021`, digest
`sha256:eef52ef944757d8143de5ebd20c08475bd2c147531e07dbe119ee43a251f39ca`.
Container `plotloom-h3-dashboard`:
`1cea1997bed660b0d2909f71f76227889c7ec3a5928a24ea1780afbe32051827`.

Observed shared lane and Comfy queue empty before replacing **only** the dashboard.
Job count146before/after; existing normal retention had reduced the previous day's
count independently. Container healthy, unless-stopped, loopback127.0.0.1:8091,
read-only root/data/secret, no GPU or Docker socket, bounded64MiB multipart tmpfs.
Dedicated secret copied internally from the existing gateway credential without
printing, rotating or exposing it. Only `/data` and the dedicated key are bind mounts.

Live loopback page/assets/config passed. Missing-origin POST refused403; a valid
same-origin2MiB multipart invalid-PNG probe reached authenticated existing gateway
and returned `image_decode_invalid`422, proving credential/forwarding/spooling
without media admission, provider inference or a new job. Count remained146.
`/v1` is not published by the dashboard. No new live H3 generation was run.

Generation services retain exact identities/start times:

- Gateway `4020bc9e8dff13da68ca839f91e142f53e5104df60e8257f4cc22400520a42d6`,
  started2026-10-06T21:33:47.772890479Z.
- Comfy `8542065d40cb5226eb50ecfbd838565e264fe8c2b02c0efe604d1af68b68354e`,
  started2026-10-06T21:33:47.591783543Z.

## Initial native HTTPS gate and rollback

At the initial deployment Serve status was `{}` and noninteractive administrator
access unavailable. The URL was not advertised as live. Owner subsequently ran:

```sh
sudo tailscale serve --bg --https=443 --set-path=/dashboard http://127.0.0.1:8091/dashboard
```

Verification results are recorded below for
`https://gx10-1523.tail6040ad.ts.net/dashboard/`. No permission widening, Funnel,
alternative publication, global Serve reset or generation-service restart was used.

Rollback only the dashboard using preceding release
`/home/wjmao/services/plotloom-h3-dashboard/releases/20261020.phi6au` and its Compose
file/image tag20261020. Leave the unused dedicated key protected; do not delete or
alter gateway data. If the new Serve handler is actually installed and must be
rolled back, remove only that exact handler as documented in the prior receipt.

## Private HTTPS closeout — 2026-10-21

Owner used the native sudo command above. Fresh Serve configuration contains only
HTTPS443 and `/dashboard` → `http://127.0.0.1:8091/dashboard`; no Funnel and no `/v1`
handler. This is the installed v1.102.4 prefix mapping, not a path-strip assumption.
Container IDs, images and start times remain unchanged from the deployment above.
Dashboard remains healthy/unless-stopped; shared lane and Comfy queues observed idle.

From the Mac, with **normal certificate verification**:

- `/dashboard`307redirect to `/dashboard/`; page, scripts, CSS, JSON/config200;
  generation API route outside `/dashboard`404.
- Missing-origin POST403; correct browser same-origin/custom-header empty request422
  `request_invalid`. This verifies access/routing without admitting a generation job.
- Retained job `h3_7975b0fcecc14cdf9ce9c6bcd41ebe55` output HEAD/GET Range206;
  unsatisfiable range416; original attachment download4930200bytes, SHA256
  `89a64b849533d030bf73cff51c13334fb7b034b7b521045bf7996c2180b20771`,
  equal to its existing database record. No media was transcoded or regenerated.
- Real headed Chrome: native seek to8seconds and playback advancement, same video
  node retained across a polling interval, enabled generation form, same-origin
  rejection test above, actual MP4 download, selected job surviving reload, phone
  layout without horizontal overflow. No TLS-ignore, muted substitute or fake ended.
- [HTTPS desktop](supporting/h3-console-https-desktop-20261021.png) and
  [HTTPS phone](supporting/h3-console-https-phone-20261021.png) inspected.

The approved console/access slice is delivered. Successful model generation was
not repeated for this closeout: local actual-admission/fixture verification and
prior live gateway rejection evidence remain separately labelled. This is neither
new model-quality/creative acceptance nor a diagnosis of the colleague's reported
timeline issue. Usage/cost telemetry unavailable. No merge/push/CI or director contact.
