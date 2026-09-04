# ADR 0021: Alpha source provenance belongs at the publication boundary

## Status

Accepted.

## Context

Alpha receipts and blinded review packs claim one exact Git commit. Validating
that claim only in the command-line wrapper leaves direct callers of the
library runner able to publish arbitrary commit labels. A single check before
the 18-run matrix also misses source or prompt changes made while the long
acceptance run is in progress.

## Decision

`run_alpha_acceptance` is the provenance and publication boundary. It resolves
the Git checkout that owns the running module, rejects every tracked or
non-ignored untracked change, resolves `HEAD` from that checkout, and requires
an explicitly supplied commit to equal `HEAD`.

After all disposable model runs finish, the same boundary repeats the check
and requires the checkout root and commit to match the initial provenance.
Only then may it return receipts or atomically publish the review pack. The CLI
delegates to this boundary and converts setup or provenance errors into its
generic, secret-free failure message.

Tests replace the private provenance resolver rather than adding a public
runtime bypass parameter. This keeps fixture runs hermetic without weakening
the production contract.

## Rejected alternatives

- **Validate only in the CLI.** Direct library callers can still mislabel a
  pack.
- **Trust any well-formed 40-character SHA.** Syntax does not establish that
  the running checkout contains that revision.
- **Check only before the matrix.** Tracked prompts and source can change
  during a long real-provider run.
- **Ignore untracked files.** An untracked Python module inside the source tree
  can participate in execution without appearing in the claimed commit.

## Consequences and guardrails

- Formal Alpha runs require a clean source checkout from start through finish.
- Ignored runtime state such as `.env`, the virtual environment, build output,
  and the configured database does not make the Git checkout dirty.
- Review output remains outside the checkout and therefore cannot invalidate
  its own run.
- Any provenance change fails closed before public receipt or pack emission.
