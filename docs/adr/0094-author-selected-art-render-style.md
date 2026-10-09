# ADR 0094 — Author-selected art render style

Status: accepted, 2026-09-29. Supersedes the deferred painterly/live-action
qualification in ADRs 0062 and 0063, not their review or selection boundaries.

## Problem and ownership

The creator selected live-action realism, but the F3A assignment explicitly
required retaining the upstream `realistic` painterly preset. Its validator
also required that preset's render sentence. The specialist followed a
contradictory contract; a later image overlay would only hide the cause.

The author owns the render-style choice and project visual direction. The
model owns scene/prop proposals. Trusted code freezes that choice, supplies
the preset, validates it at admission/acceptance/edit-save, and detects stale
project visual direction. Text acceptance and image selection remain explicit.

## Decision

Art preparation requires an explicit style ID: `live-action`, `realistic`
(labelled 半写实厚涂), or `ghibli`. The UI starts with no selection. Do not infer
style from prose, overwrite accepted cast, or redefine upstream `realistic`.
Freeze a versioned `art-style-contract.json` with the actual Brief visual
direction, selected preset and adapter byte hash; include it in the request
hash and art binding. Brief changes or adapter/preset changes require a new
task. Historical bindings without this contract remain readable evidence,
but cannot be admitted, accepted or consumed as current art.

A narrow repository-local Node adapter registers a distinct live-action preset
in the pinned upstream's exported registry and calls its validator/renderer
on the original candidate. It retains every structural gate and adds style
agreement, live-action prompt/sheet continuity and contradictory-style checks.
The specialist and backend use this same entrypoint. No vendor edits, candidate
translation, fake upstream identity or skipped validator gates are allowed.
Mechanical checks do not replace human review of visual intent.

## Consequences and guardrails

The new preset is an explicit Plotloom integration, not an upstream capability
claim. Future upstream changes must retain tested registry integration or fail
closed. Keep old delivery bytes/manifests unchanged; prepare a new request.
Tests cover all presets, unchanged upstream failures, stale direction/pins,
delivery and author-edit validation, and required UI/API style selection.
This change generates no images, accepts no art, and does not change existing
identity references. Other stages' style semantics are not redesigned here.

## Amendment — Owned report-renderer fork (2026-10-09)

[ADR0147](0147-owned-pinned-report-renderers.md) supersedes the no-vendor-edit
restriction only for its narrow owned Apache-2.0 renderer fork. Art validation,
gates and rendering now share an explicit Cast-bearing context. The adapter's
changed byte hash requires freshly prepared Art contracts and explicit review;
old requests, accepted reports and media cannot be rebound automatically.
Style selection and every structural/contamination gate remain unchanged.

## Amendment — Chinese reference-image preparation (2026-09-29)

The F3B author-facing form uses Chinese labels, lifecycle states and default
image requirements derived from the accepted art style, not a hardcoded English
cinematic-realism override. Unknown styles receive a neutral inheritance
instruction, never an inferred style. Draft requirements belong to one project,
accepted revision/hash and subject; ordinary refreshes preserve them. The
accepted subject's model prompts remain unchanged in collapsed advanced details.

Preparation freezes the author's requirements verbatim (apart from trimming),
alongside the accepted subject. An existing current task displays its frozen
requirements read-only; it must not suggest that editing a draft changes an
already prepared task. No translation service, backend schema change or rewrite
of retained reports/requests is introduced. Tests cover style inheritance,
draft isolation, frozen presentation and Chinese request round-tripping.
