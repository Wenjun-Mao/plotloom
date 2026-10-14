# ADR 0175: Dependency-ready references, frames and progress

Status: accepted for the approved bounded implementation, 2026-10-14.
Full material/native qualification and human acceptance remain outstanding.

## Problem and evidence

The serial controller waits for installation and a complete inventory before
any image, then lets the first unfinished gallery subject block every later
frame. Current Cast-owned exploratory proposals already require no Story Bible,
Shot or Approval. Art follows Cast; later text follows Art. These existing
owners provide useful independent image work without changing text dependencies.

## Decision

- Freeze an early-reference allowance of at most four jobs per new CLI run,
  within its unchanged image/job ceilings. Discover current Cast subjects and
  then current Art subjects using their exact revision/hash, saved Brief and
  package pins. Keep provisional discovery distinct from complete inventory.
  Initially offer at most two Cast subjects, reserving opportunity for Art;
  once Art is current, use remaining allowance for available subjects in
  deterministic order. A prepared subject owns one operation/job identity.
- Before early admission, reject a demonstrated lower bound that cannot fit
  the frozen ceilings: known required references, reachable filmed material
  and the eight text jobs. Reserve each actual job/image atomically. If later
  complete inventory exceeds the ceilings, stop new dispatch, retain early
  results and offer manual takeover. Do not omit subjects or increase budgets.
- Retain early deliveries as candidates. After current installation, select
  those exact asset bytes against explicit current Story-Bible authority using
  the accepted Cast-to-consumer mapping and normal CAS. Cast and canonical
  contexts have different hashes; never rewrite the original request, pretend
  the hashes are interchangeable or infer shot authority from a gallery.
- Reconcile early operation identities into the final inventory without a
  second dispatch or budget count. Complete inventory still covers every
  required reference and unique reachable filmed shot across all routes.
  A frame is ready only after current installation and current canonical
  references for its own visible characters. Unrelated Art gallery work does
  not block that ready frame; Art gallery images do not condition it implicitly.
- Reconcile active jobs and perform adoption serially in the existing project
  owner transaction. Schedule only newly ready independent work through ADR
  0174's finite pool. Preserve source currentness, visible-character limits,
  frame geometry, manual takeover and genuine human review.
- Derive concurrent activities from durable attempts and checkpoints: waiting,
  queued, generating, validating and unknown outcomes. Show actual adopted and
  retained counts; total image inventory remains unknown until complete
  discovery. Keep the visible run indicator and Brief authority. No fabricated
  percentage, ETA, process-launch internals or human approval enters the UI.

## Rejected alternatives and consequences

Reject parallel dependent text stages, fake complete inventories, automatic
canonical promotion before installation, reference-hash substitution and
gallery-wide frame barriers. Early generation changes the guarantee that no
image exists before final inventory: disclose the bounded allowance and the
retain/manual-takeover outcome when later inventory cannot fit.

## Qualification

Cover source drift, early budgets and late oversize, exact candidate retention,
mapped canonical selection, no duplicate dispatch/count, per-frame readiness,
concurrent progress and manual control. The final pack must contain all required
material once and await human review. Native parallel/all-route qualification,
stable independent review and the combined full gate remain required.
