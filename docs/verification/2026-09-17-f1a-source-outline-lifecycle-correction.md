# F1A source-outline publication lifecycle correction

Date: 2026-09-17
Scope: bounded F1A P1 correction after the incomplete `174b98b` publication.

## Result

Prepared source-outline specialist publications now have an explicit persisted
lifecycle: `prepared` blocks close, archive, permanent delete, and portable
snapshot; a verified completion becomes `ready`; explicit author install becomes
`accepted`; and an author cancel becomes durable `cancelled`.  Cancellation
prevents later refresh, delivery admission, or acceptance from changing source,
accepted outline, or a newer candidate.  The shared persistence busy guard also
covers direct `ProjectStore.archive()`, not only the folder registry routes.

The original `174b98b` F1A handoff was pushed before this lifecycle correction
and is preserved as incomplete evidence. This receipt is not F1 acceptance,
F1B acceptance, a creative review, or a fresh specialist trial.

## Verification

| Check | Result |
| --- | --- |
| Focused source-outline persistence/API tests | 9 passed (one existing FastAPI/TestClient deprecation warning) |
| Full Python suite, direct bounded batches | 583 passed (the same deprecation warning only) |
| Frontend unit tests | 16 files / 158 tests passed |
| Frontend and E2E TypeScript checks | passed |
| Deterministic frontend build / static refresh | passed; existing Vite over-500 kB chunk warning retained |
| Production FastAPI browser journey | passed: prepare → explicit cancel → close → reopen → source-page confirmation |
| Isolated wheel build and installed-wheel smoke | passed for `plotloom-0.1.0-py3-none-any.whl` |
| Independent Terra safety review | initial direct-archive bypass found; fixed in the shared busy guard; final read-only review found no blocking issue |

The focused tests cover persisted prepared blockers for close, archive, snapshot,
and historical permanent-delete state; cancellation unblocking; late delivery,
refresh, and accept rejection; direct archive; foreign cancellation targeting;
and closed-project writes.
