# ADR 0229: Complete native language-check envelope capacity

## Status

Accepted for the authorized Last Projection E2E delivery on 2026-10-31.

## Decision

A native `content-language-check` operation may use up to 2,000,000 UTF-8 bytes
for its exact projected `request.json`, including all source, candidate, response
schema, identity and validation-plan metadata. Every `inputs/*.json` retains its
1,000,000-byte limit. Generic creative and native bridge limits are unchanged.
Use the same filename-aware limits before attempt persistence/admission, before
package publication and during exact package verification/reopening. Refuse an
oversize complete file without truncating source or changing hashes. Keep the
native supervisor's existing 2 MB request reader and 1 MB validation-input caps.

This changes transport capacity only. It does not change independent semantic
checking, classifier ownership, provider-literal evidence, model/profile settings,
retry authority, source adoption or earlier check receipts.

## Context

The original 15-shot storyboard's complete projected checker envelope is
1,215,985 bytes. Its frozen candidate/source input is 825,853 bytes and response
schema 377,988 bytes, individually below 1 MB. The generic 1 MB package-reader
limit rejected the combined envelope before recording or submitting a checker.
Those two pre-dispatch refusals remain failures; no model result was fabricated.
A finite envelope bound matching the existing native reader resolves this
integration mismatch while preserving complete evidence and input limits.

## Verification

Require complete publication/reopening above 1 MB, inclusive 2 MB acceptance,
just-over-envelope/input refusals before publication/admission, and a supported
native check of the unchanged original candidate. Offline fixtures never claim
native semantic success. No fresh media is needed to exercise this repair.
