# Source-bound shot presentation amendment checkpoint

Implemented on retained `main` for the owner-authorized
[E2E-first continuation](../roadmap/2026-10-03-e2e-first-continuation.md).
This is an uncommitted source checkpoint for independent manager review, not
live project adoption or audiovisual acceptance. ADR
[0107](../adr/0107-shot-production-presentation.md) owns the contract.

## Root cause and implementation

Accepted bridge presentation cannot be edited after installation. Storyboard
changes invalidate its global approval. Asset VisualIntent and English H3
translation cannot safely replace phone-screen/typing source authority.

The new append-only shot presentation owner records explicit author review,
revision CAS, approval identity and exact source hash without changing canonical
stages. Exact message words come from trusted current-shot or immediate same-scene
predecessor pointers, retaining original coordinates/hash. Physical action,
composition, visual/motion intent and camera rendering are separately reviewed.
One effective projection feeds both image and H3 snapshots; old mixed beat
direction cannot reactivate the superseded phone/typing instruction.

The draft treatment starts with the complete unsent popped-out preview. The send
treatment starts unsent and requires a deliberate send action plus intelligible
sent state. Neither adds a runtime compositor. A new decision withdraws the
affected binding and frozen jobs; selecting again confirms the exact presentation
revision. Unchanged shots retain their original request/compiler bytes and
selected media. The schema transition admits only the exact previous layout and
adds an empty decision table.

Creator controls are in the shot media workbench's “镜头呈现调整” panel. Edits are
buffered per project/shot in session storage. Unreviewed edits block Close;
recovered stale buffers cannot inherit newer source/CAS authority. Exact text
selection is read-only source data rather than a freeform text input. Actual media
still requires review. The existing ending-frame choice, identity comparison,
segment and audiovisual review controls remain separate.

The unbound-candidate history warning now follows delivered job currentness:
current delivered candidates await keyframe review; truly stale deliveries retain
the warning and refusal. Required API lint also exposed one pre-existing unused
`ImageJobError` import in the terminal-review route; it was removed.

To respect module size, video preparation was extracted from the 532-line
lifecycle owner, and schema transition execution from the 659-line classifier.
Both responsibilities remain under their existing public ports. The classifier
is now under 500 lines; each new module is under 300 lines.

## Verification

- Backend: `uv run pytest -q tests/test_shot_presentation.py
  tests/test_shot_presentation_integration.py tests/test_h3_i2va_prompt.py
  tests/test_production_presentation.py tests/test_project_storage_video.py
  tests/test_project_storage_image_workflow.py tests/test_image_job_exchange_contracts.py
  tests/test_project_storage_image_identity_contracts.py tests/test_project_storage_recovery.py`
  — **123 passed**.
- `uv run pytest -q tests/test_pin_image_specialist.py` — **20 passed**.
  The committed-checkout fixture now includes the new required source owner;
  dirty contract and nested persistence owners still fail preflight.
- Frontend: `npm test` — **406 passed / 53 files**. `npm run typecheck` and
  `npm run typecheck:e2e` passed.
- Ruff passed for the new/extracted backend modules and tests; the established
  API F401 check passed. `git diff --check` passed.
- `npm run build:deterministic` refreshed shipped static files. The existing
  large-chunk advisory remains. `workbench.js` SHA-256:
  `4ad1ed8a7be8bcc81482d3a56d478abdec41b66004711c4db7a021b108103bca`.

The storage/API regression creates six explicitly synthetic selected audiovisual
segments. Reviewing B2 stales its old request/binding, leaves all six selected
jobs current with identical snapshots/hashes, and leaves canonical stages
unchanged. Image/H3 effective shot, context and presentation snapshots match.
B3 inherits B2's exact literal/provenance. Repeated CAS, stale source, invented
text and unrelated literal pointers are refused. An exact predecessor schema
inspection is read-only; writable open adds only the empty table.

No provider calls, live project edits, runtime restart, normal installation
change, source commit or push occurred. Browser E2E, live adoption, actual new
media, sound acceptance and route acceptance remain the manager's next steps.
