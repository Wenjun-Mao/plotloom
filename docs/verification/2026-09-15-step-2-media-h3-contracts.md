# Step 2 media and H3 contract receipt

Local candidate from `cd10f70` for the media/H3 portion of Step 2. This is
verification coverage, not creative-media acceptance, a live-provider claim, or
gateway deployment approval.

## Current contract evidence

- Manual image packages keep the frozen request hash and snapshot; a changed
  package is rejected before delivery admission. Existing project-folder tests
  retain secret-safe delivery admission, confined paths, partial/hash tamper
  rejection, late-cancel inapplicability, concurrent refresh, and frozen
  keyframe geometry. Those focused cases do not by themselves disposition the
  older forged-authority, missing-tool-evidence, or exact V1 package-shape
  assertions.
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

No gateway service source was changed. Its direct V4 routes, queue, worker and
retention are the gateway's contract; Plotloom's client covers its frozen
binding, local retention, and no-blind-replay behavior separately.

## Retained-runtime dispositions

The inventory now marks these individually reviewed baseline cases `verified`:

- cancelled late image delivery; confined cross-project/symlink delivery;
  exact adaptation geometry; and the manual prepare/copy/refresh/refine path;
- frozen H3/local-accounting without a Wan ledger; uncertain H3 submit with no
  replay; and identity-reference replacement before the first submit.

The inventory remains incomplete. Forged-authority, missing-tool-evidence,
full partial/tampered/conflicting-delivery, exact legacy-V1-package, other
image-reference, other H3 output/recovery, and all non-media entries remain
explicitly pending; none were inferred from the new tests.

## Local verification

```sh
uv run --locked pytest -q tests/services/minimax_h3_gateway tests/test_project_storage_image_delivery_contracts.py tests/test_project_storage_image_workflow.py tests/test_project_storage_video.py tests/video_backends/minimax_h3/test_transport.py
uv run --locked python scripts/retained_runtime_coverage_inventory.py --check
```

The first command completed locally with all selected tests passing; the second
validated the inventory's baseline evidence, replacement assertion hashes and
review-summary status. The FastAPI test client emits its existing Starlette
`httpx` deprecation warning.

## Boundary and acceptance

No live gateway, ComfyUI, provider, deployment, remote storage, frontend
feature, retention automation, or Step 3 data/configuration work ran. The Terra
semantic review cleared this local candidate; director acceptance remains
required before calling the media/H3 group or Step 2 accepted.
