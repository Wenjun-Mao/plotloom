# Storage cleanup integration closeout

Captured 2026-09-13 for the preserved correction baseline
`e964888d97c8b852ac74eb4b62450ba12317f86e`. That baseline is not accepted as
a release: its original Relay failure history remains intact. This closeout
changes only the two named integration gates and staging-cleanup safety
hardening; it does not repeat migration, touch live media/data, alter selection
or the 15/100 ledger, call a provider/ImageGen, or delete a real path.

## Root cause and correction

The extraction contract admitted only enumerated repository roots. The tracked
private `services/minimax_h3_gateway/` subtree therefore failed the root gate,
while adding `services` without a narrower contract would permit unrelated
runtime material. The gate now admits exactly that tracked subtree and rejects
other service children, direct files, and untracked files below it. Negative
synthetic fixtures exercise both rejection classes; gateway implementation was
not changed.

The staging helper initially derived a task root from unchecked environment text
and validated mutable metadata by pathname. A source directory entry could also
be replaced after descriptor verification but before its final unlink. The
durable correction rejects non-single-component task IDs, requires private,
current-user transaction directories, locks staging/delivery/outputs in order,
reads request and completion metadata through descriptor-relative no-follow
opens, and retains locks through copy, verification, and unlink. Preflight
creates the private delivery transaction directories. ADR 0032 and the
repository skill state the cooperative same-UID boundary explicitly; a hostile
same-UID process that ignores advisory locks is outside this portable POSIX
contract.

## Independent review

An attended, read-only `gpt-5.6-terra` review independently found the unsafe
task-ID confinement and final-unlink race, then verified the private-directory,
ordered-lock, descriptor-read correction. Its final follow-up found and closed
two P2 wording/contract mismatches: leading/trailing task-ID whitespace now
refuses rather than normalizes, and every shell path placeholder in the skill is
quoted. Final disposition: approved.

## Verification

- Focused integration and safety tests:
  `uv run pytest tests/test_cleanup_imagegen_staging.py tests/test_extraction_contract.py tests/backend_core/test_image_jobs.py -q`
  — `52 passed` (synthetic files only).
- Repository skill validation:
  `uv run python /Users/wjmao/.codex/skills/.system/skill-creator/scripts/quick_validate.py .agents/skills/plotloom-image-specialist`
  — passed.
- Locked Python suite: `uv run pytest -q` — `623 passed, 9 skipped`.
- Distribution check: `uv build --wheel && uv run python scripts/smoke_installed_wheel.py dist`
  — passed.

No frontend source changed, so frontend build/type/browser gates were not
rerun. The attempted `uv run ruff` check remains unavailable because `ruff` is
not declared or installed in this locked environment; no lint result is claimed.
