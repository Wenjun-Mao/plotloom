# ADR 0097: Published voice performance takes and shared admission

**Status:** Accepted 2026-09-30; runtime adoption technically verified 2026-10-01
under the owner-approved [bounded plan](../roadmap/2026-09-30-voice-takes-h3-plan.md)
and [completion receipt](../verification/2026-10-01-published-voice-takes-shared-admission.md).
This supersedes ADR 0096's independent-queue operating boundary for managed
gateway/Lab callers, not its limits on direct backend clients or memory claims.
Plotloom integration, director contact, merge and push remain withheld.

## Context

Published Voice IDs protect identity from candidate/project changes. Current
reuse trials instead require a mutable project selection and retain their audio
only within that project. The matched H3 reference comparison found stronger
urgency with an Index dialogue-specific take, with no owner-reported identity,
word or lip-sync penalty in that shot. H3 already accepts frozen reference WAV
bytes, but this does not promise the generated soundtrack exactly repeats them.

At the planning baseline, gateway H3/Qwen-Image and Voice Lab dispatched independently. Combining
them through a convenience endpoint alone would expose a production-looking
API without solving that known scheduling boundary.

## Decision

- Keep `voiceId` as the permanent identity and introduce immutable successful
  audio behind a separate `takeId`, generated from published identity, dialogue
  and explicit delivery. Regeneration creates a new take, never a new identity
  or replacement of previously selected bytes. Preserve native audio and prepare
  a separately hashed H3 derivative under the existing media contract.
- Voice Lab remains the synthesis/provenance/storage owner. Expose take creation,
  listing, status, verified audio and explicit terminal deletion through the
  authenticated gateway. Retain take assets independently of source projects,
  with no automatic TTL; temporary gateway media retention must not erase them.
- Keep two caller-controlled stages: obtain/select a take, then supply its
  prepared audio bytes to the existing H3 endpoint. Do not add inference hidden
  in video submission, take-ID lookup inside H3, automatic acting approval or
  exact-waveform claims. Plotloom owns its eventual selection and retained copies.
- Extend the gateway-owned durable lane to **all** managed Lab generation,
  including existing candidate creation/trials. Use typed owner/job bindings,
  recoverable registration and a narrow grant-based voice execution boundary.
  Voice Lab ceases independent dispatch in this deployment, but retains its
  short-lived, pinned-environment engine processes. No inference dependencies
  enter the gateway API, and no four-model resident cache is introduced.
- Preserve dispatch uncertainty and block further lane admission to execution
  until owned work is resolved/reaped. Health, idle-looking services or expiring
  leases are not proof of execution completion. Registration bookkeeping may
  deduplicate/reconcile; inference is never blindly resubmitted.
- Preserve existing voices, media and terminal evidence through checked
  migrations. The original CUDA cause remains parked, not declared repaired.

## Alternatives and consequences

**Expose current clone trials unchanged:** smaller API work, but consumers remain
bound to editable selection/project lifetime and cannot rely on durable H3 audio.

**Generate speech automatically inside the H3 request:** fewer caller steps, but
couples acting iteration to expensive video work, hides two failure boundaries
and removes the useful audition/selection point.

**Keep two queues with idle checks or a lease timeout:** easy to bolt on, but
retains admission races and can allow overlapping work after an uncertain remote
result. A common dispatch owner is the narrow durable fix for managed clients.

The chosen design costs a small take domain plus cross-service registration and
restart handling. It avoids forcing voice data into video schemas, duplicating
model logic or building a general distributed scheduler. Serial generation can
prevent managed overlap; it does not establish unlimited memory, creative
quality or safety against callers bypassing the services.

## Guardrails

Freeze all synthesis inputs; expose actual interpreted controls; prove source
and prepared hashes, immutable regeneration, explicit deletion, cross-service
FIFO, process-group release, lost acknowledgements and restart behavior before
deployment. Keep data preservation, bounded live calls and specialist/director
ownership explicit in the plan. Runtime adoption requires the plan's verification.
