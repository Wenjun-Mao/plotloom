# Plotloom external review — start here

This GitHub-only package supports two independent reviews of the proposed
story-to-playable roadmap. Read the [roadmap](../story-to-playable-alpha.md),
then give each reviewer its **complete prompt**, not just a repository link:

1. [Reviewer A: creative workflow and audiovisual continuity](creative-workflow.md)
2. [Reviewer B: architecture boundaries and bounded delivery](architecture-delivery.md)

Both prompts are self-contained. Supporting documents and all required source
are in this repository; no local filesystem access is required.

## Exact versions

- Product source: [`9afbefd2f82a620d79b82cd6607571057f23a6c4`](https://github.com/Wenjun-Mao/plotloom/tree/9afbefd2f82a620d79b82cd6607571057f23a6c4).
- Packet: the documentation commit containing this entrypoint. Prefer the
  commit-pinned URL supplied with the handoff; on a branch URL, use GitHub's
  permalink action and record the resulting commit before reviewing.
- Publication branch: `codex/m1b-alpha`. `main` is older and is not the review
  source. Publication does not claim Alpha qualification or release acceptance.

## Supporting evidence

- [Proposed decision record](../../adr/0026-story-to-playable-product-direction.md)
- [Capability/progress matrix](../capability-matrix.md)
- [Text qualification completion plan](../m1c-completion-plan.md)
- [Retained readiness verification ledger](../../verification/2026-09-10-provider-readiness-offline-candidate.md)
- [Retained disconnected-workbench screenshot](../../verification/assets/provider-readiness-disconnected-1440x900.png)

The architecture prompt supplies the exact source paths to inspect. Reports
must distinguish directly inspected facts, repository receipts, supplied
summaries and hypotheses. Local credentials, databases, private content-review
packs and generated trial media are intentionally excluded; their absence is
an evidence boundary, not a request to obtain them. A failed access attempt must
be reported rather than replaced silently with another revision.

Return each report unchanged. We will synthesize them separately using
Use/Test/Park/Discard and verify claims before implementation. No consultation
has been dispatched merely by publishing this package.
