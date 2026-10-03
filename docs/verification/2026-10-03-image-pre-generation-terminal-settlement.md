# Pre-generation image terminal settlement — verification

Owner approved the bounded recovery implementation during the Oct 2 evening
continuation (Oct 3 UTC). Root identified the layer before changing source:
B1's cancellation succeeded, while ADR 0074/0093 correctly retained native
ownership. A completed blocked-before-ImageGen attempt had no admitted terminal
outcome. This work adds the [ADR 0106](../adr/0106-reviewed-pre-generation-image-terminal-outcome.md)
protocol, not a cancellation shortcut or a fake successful image delivery.

## Deterministic verification

- `uv run pytest tests/test_image_terminal_settlement.py tests/test_pin_image_specialist.py -q`: **51 passed**.
- Broader terminal/registry/dispatch/creative-reconciliation/exchange/pin suite:
  **130 passed**, including those focused checks.
- Static freshness, specialist routes, real project image workflow/identity/
  delivery and art-reference additional-candidate suite: **26 passed**.
- Frontend full suite: **402 tests / 52 files passed** (two new terminal UI tests).
- Frontend `typecheck` and `typecheck:e2e`: **passed**.
- Frontend production build: **passed**; existing large-chunk advisory remains.
- `git diff --check`: **passed**.

Fixtures are deterministic, with no live image/video generation. Real SQLite
owners and immutable exchanges cover shot/character/art requests, unknown queue
acknowledgement, cancellation eligibility, package/reference/pin integrity,
strict boolean no-output declarations, explicit hash/task-bound operator review,
conflicting/staged output, exact competing leases, restart/repeat and crash
tombstones. Logical database contents and immutable project files remain
unchanged by settlement; ordinary SQLite checkpoint/WAL byte movement is not
misrepresented as content mutation. New terminal/lifecycle sources join the
committed execution pin boundary. Dedicated UI tests cover explicit review,
double-click serialization, no resend and invalidated project proof.

## Independent review

GPT-6.1 Sol / Medium read-only review first found the successor-after-unlink
crash gap and missing pin-owner coverage. Root addressed both with named
regressions and added role-mapped reference/noncancelled cases. Final review
reported **no blocking findings**. The reviewer did not execute these tests;
results above are root's actual executions.

## Live trial

Pending deployment and explicit UI settlement of cancelled
`ij_fa5d92f47309455db808ef45600ea145`. Its request SHA-256 is
`82176d3dce375e3faae7f58b1814d3a11aabe1693458a82e7db00a042120914a`.
The original pin and package are preserved. No live lease has been cleared,
no failed package replayed, and no terminal success fabricated. Record the
supplementary same-worker acknowledgement and explicit operator review here
after they actually complete. This recovery alone is not image or route acceptance.
