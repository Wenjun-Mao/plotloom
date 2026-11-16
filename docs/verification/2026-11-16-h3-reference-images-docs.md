# H3 reference-image documentation refresh · 2026-11-16

The colleague workflow for `POST /v1/video-jobs/from-reference-images` is now
available as a dedicated [Chinese Bruno/curl guide](../operations/minimax-h3-reference-images-client-guide.md).
The existing general guide keeps its section 7B entry point and links to the
complete walkthrough. Repository/service/operations indexes, the operator manual,
prompt playbook, dashboard guide and timing-table scope point to the same contract.

The endpoint already existed. This is a documentation-only refresh against
`reference_api.py`, `reference_contracts.py`, `reference_files.py`,
`reference_execution.py` and the existing dashboard submission implementation,
at implementation baseline `ba0a782a`. No API, workflow, runtime, deployment,
dependency or generation behavior changed.

## Corrections and useful distinctions

- Ordered Ref2VA accepts 1–9 images, with one ordered encoding slot and timed
  guide per image; ordinary FL2VA start/end sockets remain a separate contract.
- `aspectPolicy` and integer `durationMs` 5000–15000 are required. The route
  rejects `quality`, `durationSeconds`, voice inputs and extra form fields.
- Multipart is one `request` JSON text field plus repeated `images` files in
  the same order. The full upload JSON is now provided, alongside the URL form.
- Combined image bytes are limited to 20 MiB; the two canvases, opaque-still
  rules, nearest-frame rounding, collisions and native frame-range bounds are explicit.
- The guide covers ID preservation, readback, output expiry and route-specific
  errors, including URL downloads exceeding the remaining byte allowance.
- Dashboard creation remains its existing start/optional-end form; ordered
  references are created through the typed API and displayed by the dashboard.
- The ordinary quality-based timing table does not estimate Ref2VA workloads.
  The historical successful five-image run is distinguished from the nine-image
  API limit and from actual learned capacity at other counts/durations.

## Executed verification

| Check | Result |
|---|---|
| Actual request parser, both fenced JSON examples | Both accepted; upload metadata and URL metadata use their respective schemas |
| Cardinality boundaries | One and nine references accepted without dispatch |
| Invalid request examples | Quality selector, seconds field, missing aspect policy, quantized collision and anchor outside native frame range all refused |
| Time mapping | 11300 ms → 277 frames; anchors → 0/60/108/163/216 |
| Shell examples | All five shell blocks passed `sh -n`; no curl submission was executed |
| Local documentation links | 170 referenced local paths existed at the final candidate |
| Live read-only Spark health | `status=ok`, reference version 1, ready=true, max=9, canvases 960x544/576x1024, duration 5000–15000 ms |
| Independent GPT-6.1 Terra/high review | Native-frame boundary omission found, corrected and narrowly rechecked; no remaining finding |

The parser checks used the locked local environment with the service source on
`PYTHONPATH`. The receipt is
`.local/documentation/h3-reference-images-20261116/validation.json`.
Read-only health confirms advertised capability, not learned nine-image capacity.
No new video, Bruno UI operation, hosted CI, deployment or service restart was
part of this documentation pass. Historical learned execution evidence remains
the [November 7 record](2026-11-07-h3-ordered-reference-images.md).

The operator manual remains above 500 lines because it is the cohesive runbook
for one service's deployment, lifecycle, retention and recovery. This pass makes
bounded corrections within those responsibilities. The longer colleague API
walkthrough was separated into its own guide; no unrelated restructuring was needed.
