# ADR 0111: Journey-first creator presentation

Status: accepted for the owner-approved October 4, 2026 UI polish pass.

## Problem

The genuine E2E walkthrough needed developer narration despite functional
generation/review paths. Local styles gave ordinary numbers status-like emphasis,
cards omitted spacing, and disabled/busy actions looked alike. Some headings
showed retained accepted content instead of the current editing/review task;
video guidance counted historical selections that playback correctly refused.

## Decision

Order the work and guidance by creator tasks, not internal module names. Each
stage explains its input, action consequence, result and next destination.
`StageGuide` renders instructions supplied by the owning stage; it owns no
readiness or progress state. Continue actions call existing guarded workspace
navigation and preserve dirty-source/section, currentness and lifecycle checks.
Reference images remain optional where the existing contract makes them optional.

Extract shared typography, spacing and action roles into `creator-ui.css`.
Equivalent creator roles share a small readable scale; technical disclosures
and narrative reading retain intentional exceptions. Accent/status colors keep
their semantic meaning. Optional/legacy workflow actions remain accessible but
subordinate. Required markers identify actual required inputs with accessible
required information; markers do not change persistence or validation authority.
Unavailable controls use consistent neutral treatment with nearby reasons;
busy is a separate announced operation, not the default meaning of disabled.
Expanded toolbar diagnostics occupy normal layout and scroll with the page;
they never float over authoring controls. Collapsed toolbars may remain sticky.

Headings prioritize stale/reopened/prepared/ready work over retained accepted
versions. Failed reads show error/retry instead of indefinite loading. Video
selection guidance uses the same current-job/current-selected-segment predicate
as route playback, plus the authored duration where applicable. Unknown/loading
is never relabeled as absence or failure. These are presentation corrections,
not permission to relax review, retry uncertain dispatch or rewrite history.

The existing run observer follows React effect lifecycle as well as the route
epoch: setup is live after a development StrictMode cleanup/setup replay, while
a real unmount refuses held progress, final project reloads and error feedback.
Terminal progress triggers the existing canonical refresh; an early aggregate
read is not a replacement for observing generation completion. No run is
resubmitted to recover the UI and route-currentness checks remain authoritative.
Same-project navigation hands an active run to a new route-current observer
when no aggregate load or trace selection owns that transition. The handoff
only reads progress; it neither resumes nor resubmits the run. Pending trace
selection, another project's run and terminal runs are not handed off.
An empty quarantine projection does not establish successful validation.

The owner permits direct normal-installation UI iteration while sleeping.
Source/media/approvals remain unchanged; automated fixtures own mutating tests.
After UI qualification, the Chinese Creator's Manual uses exact visible terms,
reviewed screenshots and a recorded applicable revision. The manual explains
tasks and recovery; routine next-step guidance remains in the UI itself.

## Alternatives and consequences

Page-specific CSS patches would perpetuate drift. A new wizard/progress store
would duplicate existing owners and restrict useful revisiting. A manual-only
remedy would leave routine navigation ambiguity. No new backend, provider,
schema, generation contract or automatic backup is required by this decision.

Guardrails cover required labels, disabled/busy distinctions, candidate-plus-
accepted/reopened states, read failure/retry, historical video selections,
guarded continuation and comparable desktop/compact layouts. Final human
self-guidance acceptance remains the owner's later uncoached walkthrough;
automated fixtures and agent reports do not establish it.
