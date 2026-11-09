# ADR 0239 — Source handoff, still-frame and assembly checking

Accepted November 8, 2026 for the owner-authorized three-episode continuation.

## Decision

Extend ADR 0238 with three manually invoked, versioned personal Codex skills,
kept in `tools/codex-skills/` and linked into the personal skills directory:

- `authoring-handoff-checking` binds current outline/script/staging/storyboard
  evidence and checks hooks, dialogue, state, action ownership and sound scope.
  Existing upstream validators retain their mechanical contracts; Terra/high
  reviews semantic consistency. Source review does not prove provider fidelity
  or generated-media quality.
- `reference-frame-checking` binds still-image roles to source expectations and
  relevant current character/environment references. Terra/high opens actual
  pixels and judges material contradictions. Cropped or occluded state is not
  inferred absent; identical images can serve different authored roles.
- `assembly-progress-checking` derives order, gaps and status from current source,
  explicit decisions and actual receipts. Supplied partial selections stay partial;
  no best/latest take is inferred. Technical completion, review, selection and
  current export bindings remain separate. Reuse PCM/frame/clock proofs with their
  actual source and selection boundaries; AAC output is not bit-identical PCM.

Generic tools own pins, freshness and structural checks. Production adapters use
the existing project's current-authority/selection contracts without changing
runtime APIs. Tool checks cannot prove that a model viewed images or understood
source. The coordinator audits original evidence and corrects demonstrated
checker weaknesses with focused regressions, preserving old reports.

## Scope

The owner explicitly permits autonomous invocation of these skills and Terra
subagents for this run, then completion of all three episodes and a combined
video. Retained usable work is reviewed/reused. This prospectively resumes the
operational pause; it neither rewrites old pause evidence nor replays held grants.
Dispatch needs a new exact grant and current readiness. No UNKNOWN clearing,
provider fallback, permanent-caption-fix study, CI or push is implied.

These remain optional checking workflows rather than new Plotloom runtime gates.
The expanded plan is
`docs/roadmap/2026-11-08-checking-extensions-and-complete-story.md`.

## Future assembly troubleshooting

Assembly checking 0.1.1 documents conditional troubleshooting when the exact
post-intent admission digest is absent from the owning local registry. An
authorized coordinator may resolve a demonstrated registry issue; the read-only
checker does not register grants automatically. This adds no routine gate or
dispatch authority. This run used 0.1.0; the guidance applies to future
invocations and does not rebind historical evidence.
