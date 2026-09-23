# Repository simplification tracker

Status: candidate backlog, 2026-09-23. This is not approval to delete code, change product contracts, or bundle cleanup into the shot-count policy slice.

## Evidence and decision rule

The outside audits in `/Users/wjmao/Downloads/plotloom simplifications/` examined an earlier revision. Their findings are leads, not current-main facts. Before each change, recheck reachability and ownership on current `main`, name the behavior that must remain, choose a bounded slice, and record any contract decision in an ADR. A reduction in supported paths and independent rule owners matters more than line count. Preserve current user-valued assets, recovery, dispatch safety, credentials, and all still-supported generation/repair flows.

## Candidate sequence

- [ ] Run existing CI and installed-wheel/browser gates against the shipped artifact; resolve current-main failures first (audit F1, F21, S1).
- [ ] Make the two scoped ADR clarifications: authored stable IDs versus record UUIDs (ADR 0004), and server-owned durable draft receipts versus browser buffers (ADR 0014). Preserve historical context rather than rewriting it (independent ADR-SIM-01/02).
- [ ] Characterize and retire the unused provider container/interface family and startup auto-dispatch helper in separate changes. Keep active startup recovery and relevant regression tests (independent SIM-01/02).
- [ ] Review residual modules, unreachable tables, imports, compatibility shims, and duplicated build entrypoints symbol by symbol. Remove only proven dead paths with focused tests; do not treat an old audit inventory as deletion authority (audit F5–F7, F20–F24, S2–S3).
- [ ] Replace frontend old/new-storage capability branching with one explicit current-runtime initialization contract. Test delayed, failed, malformed and retrying capability responses, draft persistence failure, new-project state, project switching, server-draft restoration, two-tab CAS, close draining, and snapshots (independent SIM-03).
- [ ] Characterize identity-critical duplication before extraction: fresh V3 profile assembly, canonical JSON/hash ownership, schema presence, and generated type ownership. Share only pure rules; retain distinct read/write and frozen-profile boundaries (audit F13–F15, S5, S11; independent SIM-04).
- [ ] Triage broader review-route, correction, and frontend render duplication as separate design work, not a blanket generic-framework pass (audit F16–F19, F22, S7, S10, S12).
- [ ] Build an ADR index and reconcile specific live claims and supersession links in bounded documentation changes. Treat conflicting ADR claims as decisions to resolve, not wording-only cleanup (ADR audit A1–A16, S1–S10).

## Explicit deferrals

Do not retire the current generation pipeline until replacement ownership is proven. Do not conflate read-only profile loading with writable repositories, delete all false capability branches blindly, rekey authored IDs, or fold H3 gateway extraction, security findings, acceptance-tool relocation, and platform bugs into these slices. The outside reports retain their detailed evidence and rejected alternatives; this page is only the local navigation and stopping checklist.
