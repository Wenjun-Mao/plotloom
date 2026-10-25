# ADR 0219: Validated installation-only reader

Status: accepted for implementation, 2026-10-25, under the owner-approved
[retained plan](../roadmap/2026-10-25-installation-only-reader.md).

Material inventory requires installed-production authority but previously obtained
it from the complete production review projection, including pending proposal,
presentation, preparation and job views.

`ProductionBridgeInstallation.get_installation(project_id)` acquires the existing
read lease, requires the project and bridge head, and delegates to
`installation_in_session()`. `ProjectStore.production_bridge_installation()` exposes
the typed `InstalledProduction | None` result; only `initial_inventory()` switches
to it. The existing validator remains the sole owner of admission/proposal evidence,
canonical identities and upstream currentness. Missing or outdated installation
still refuses material inventory; corrupt evidence and unexpected failures propagate.

A current installation remains independent of a pending replacement proposal.
Full production-review projection and its proposal-first exception order remain
unchanged. Readers use current lease/snapshot semantics without a new cache,
fallback, schema, endpoint or write. Cast/art, topology, production closure and
workload checks retain their owners. This decision makes no speedup claim.

Current regressions live in `tests/test_production_bridge_installation_read.py`
under creative-production ownership, with API readiness coverage in
`tests/test_autopilot_review_readiness.py` under story-authoring. Source qualification
and installed activation are reported separately in the retained plan.
