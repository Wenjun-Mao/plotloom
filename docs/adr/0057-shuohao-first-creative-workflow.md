# ADR 0057: Shuohao-first creative workflow

Status: Accepted direction, 2026-09-17; F0 foundation implemented, F1–F10 pending.

## Context

Plotloom rebuilt creative stages inspired by Shuohao instead of executing its
workflow. Structural checks did not establish narrative coherence. Bounded
novel-script trials with Terra and Qwen now support reuse feasibility, not general
quality or causal superiority. The user chose reuse-first delivery, five creative
stages, a Terra repo specialist and Plotloom as the interactive product.

## Decision

Use pinned, project-local Shuohao-derived outline, characters, art, script and
storyboard skills. One repo specialist routes stage work; a disposable Terra task
executes it initially. A skill is not a backend process. Start with an explicit
manual job handoff rather than build a new agent runtime.

Plotloom owns projects, stable section routing, accepted revisions, review,
managed assets and production/playback. Creative outputs arrive as candidates.
Reuse upstream JSON where suitable, with minimal interactive metadata; Markdown
and HTML remain derived views, not competing data authorities. Reuse report UI
safely and preserve license/NOTICE. A versioned integration decides exact schema
ownership before changing current canonical storage.

F0 pins upstream `4322897e6d2bdaf66365534fd40194360c75a85f` as the
`third_party/shuohao-skills` submodule, retaining its Apache-2.0 LICENSE and
NOTICE. The project-local `CreativeHandoffExchange` freezes a self-contained
single-stage request and admits only a traceable candidate plus derived report.
It verifies the initialized submodule against Plotloom's recorded Git gitlink
and verifies every specialist-consumed package file again at candidate-read
time. The author owns source/adaptation and acceptance; the specialist owns
proposed upstream-shaped JSON; F0 trusted code owns package/delivery transport
integrity and stale-revision admission. A later selected existing owner, not
F0, owns review and any canonical installation. F0 does not install candidates
and its specialist seam is intentionally checkout-operated, not packaged-wheel
runtime support.

Source may be a synopsis developed into a short story/treatment, externally
written material, or an existing work. Preserve source versus adaptation choices.
Interactive stories are DAGs of stable sections with shared character/art data,
not duplicated full-route episodes. Briefs carry relevant incoming history and
consequence. Episode-only gates need explicit applicability, not fake pass values.

Qwen is deferred from immediate authoring delivery, not deleted. Custom two-phase
integration is paused. Existing working media, storage and player components are
reused; superseded authoring code is removed as replacement behavior is proven.
No global skill install, blanket data reset or backwards-compatibility project.

## Alternatives and consequences

- Continuing the bespoke generation pipeline would invest in overlapping
  authoring orchestration before testing existing reusable work.
- Installing upstream globally would hide project versioning and affect unrelated
  projects. The exact portable dependency mechanism remains F0 work.
- Replacing Plotloom wholesale would lose interactive routing and working
  review/production behavior not supplied by the creative skills.
- Keeping two permanent authoring pipelines would increase drift and maintenance.
  A bounded transition is allowed, with explicit retirement per checkpoint.

Terra execution introduces a Codex dependency and usage cost; model-independent
handoff data preserves future options without implementing them now. Native H3
prompt exports do not establish deployed voice or lip-sync capability. Audio
qualification precedes substantial dialogue production.

## Guardrails

The [revision-4 roadmap](../roadmap/playable-mvp-milestones.md) is current authority.
Earlier ADRs/receipts remain evidence for retained behavior, not authority to
resume the superseded authoring qualification queue. No claim that old 3B passed.
F0–F10 require usable outputs, source-backed review and explicit replacement scope.
First pilot: one decision/two endings; reconvergence separately qualified.
Preserve credentials, transaction/dispatch safety and valued assets throughout.
