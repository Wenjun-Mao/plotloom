# Step 2 media and H3 contract receipt

The initial media/H3 verification increment was director-accepted and pushed as
`55034d0fbe13041d82864167a8a5d9f8c6366119`. That accepted only the named
baseline assertions below; it was not media-group or whole-Step-2 acceptance.
This bounded follow-up closes the remaining delivery-authority, evidence,
identity, legacy-package, and H3-output dispositions before the next independent
review. It is verification coverage, not creative-media acceptance, a
live-provider claim, or gateway deployment approval.

## Current contract evidence

- Manual image packages keep the frozen request hash and snapshot; a changed
  package is rejected before delivery admission. The project owner now directly
  rejects browser-supplied delivery path/prompt authority, foreign approvals,
  foreign job refresh, symlinked output, missing built-in-tool evidence,
  partial output, hash tamper, conflicting delivery IDs, and second final
  deliveries. A rejected/conflicting return cannot replace the already
  admitted candidate or install another asset.
- The exchange still rechecks its historical V1 two-file projection
  (`COPY_ASSIGNMENT.txt` and `request.json`) from frozen request evidence. This
  is retained package readability only: no V1 runtime, route, provider worker,
  or deployment path is restored. P1.5 image jobs freeze explicit character
  decisions and role-mapped hashes, require observed specialist pin/provenance
  and reference-use attestation, then make the job, same-person review, and
  still preview stale when that decision is replaced.
- A direct H3 project job freezes adapter/backend identity and uses only the
  zero-unit local-capacity dispatch lease. The retained Wan pilot ledger is not
  created. A lost submit response becomes `outcome_unknown` and a second submit
  is refused. Replacing a character reference makes an already reviewed local
  video unselected and non-current. A separately prepared job bound to the old
  reference is rejected before its first submit with zero provider calls.
- The gateway-owned V4 tests use only offline fakes. They prove FIFO admission
  skips a cancelled item and never overtakes active work; a claimed dispatch is
  restart-marked `outcome_unknown`; an uncertain Comfy submission is not
  replayed; and expiry removes only the named managed MP4 while retaining an
  unrelated file and reporting the stable expiry error.

The H3 adapter directly rejects a browser-playable H.264/AAC output whose
geometry differs from the frozen profile. The direct project-video recovery
test separately proves a locally ingested H3 output remains range-readable
after snapshot/restore without a configured provider, provider replay, or Wan
accounting identity. A restored known job may reconcile only against the exact
frozen backend; an unknown job cannot reconcile or submit.

No gateway service source was changed. Its direct V4 routes, queue, worker and
retention are the gateway's contract; Plotloom's client covers its frozen
binding, local retention, and no-blind-replay behavior separately.

## Retained-runtime dispositions

The inventory now marks these individually reviewed baseline cases `verified`:

- cancelled late image delivery; confined cross-project/symlink delivery;
  exact adaptation geometry; and the manual prepare/copy/refresh/refine path;
- frozen H3/local-accounting without a Wan ledger; uncertain H3 submit with no
  replay; and identity-reference replacement before the first submit.
- browser path/prompt injection and foreign-approval authority; missing tool
  evidence; partial/hash-tampered/conflicting/finalized delivery; and exact V1
  package projection;
- P1.5 image identity reference admission, frozen package role/pin, attested
  delivery, explicit review, preview, and stale replacement propagation; and
  an H3 playable-but-wrong-profile output.

The inventory remains incomplete outside these named rows. In particular, the
old generic Wan remote-failure/poll rows are historical facade details rather
than current direct-H3 API requirements; they remain visibly pending instead
of being relabelled as equivalent. No claim is made that every legacy media row
is verified by this bounded work.

## Local verification

```sh
uv run --locked pytest -q tests/test_project_storage_image_delivery_contracts.py tests/test_project_storage_image_identity_contracts.py tests/test_image_job_exchange_contracts.py tests/video_backends/minimax_h3/test_transport.py tests/test_project_storage_video.py
uv run --locked python scripts/retained_runtime_coverage_inventory.py --check --require-verified-entry tests/backend_core/test_image_jobs.py::test_image_job_rejects_forged_authority_cross_project_and_browser_paths --require-verified-entry tests/backend_core/test_image_jobs.py::test_image_job_rejects_partial_tampered_and_conflicting_delivery --require-verified-entry tests/backend_core/test_image_jobs.py::test_legacy_v1_package_remains_recheckable_without_a_template --require-verified-entry tests/backend_core/test_image_jobs.py::test_identity_reference_job_is_explicitly_reviewed_and_stales_on_replacement --require-verified-entry tests/backend_core/test_p2_video_jobs.py::test_h3_rejects_a_playable_output_that_violates_the_frozen_profile
```

The first command completed locally with 29 selected tests passing; the second
validated the inventory's baseline evidence, replacement assertion hashes and
the five required reviewed rows. The FastAPI test client emits its existing
Starlette `httpx` deprecation warning.

## Boundary and acceptance

No live gateway, ComfyUI, provider, deployment, remote storage, frontend
feature, retention automation, or Step 3 data/configuration work ran. The prior
`55034d0` acceptance does not waive a fresh independent review of this bounded
delta. Director acceptance remains required before calling the media/H3 group
or Step 2 accepted.
