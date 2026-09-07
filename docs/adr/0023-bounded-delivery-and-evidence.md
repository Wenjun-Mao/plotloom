# ADR 0023: Bounded delivery and evidence

## Status

Accepted for development workflow. Generation field ownership remains governed
by the existing domain ADRs; this record does not change a runtime contract or
lower an acceptance threshold.

## Context

The September 2026 process audit reconciled the user's September 3, 4, and 7
usage export with local task records: 10,172 responses across one root and 107
distinct subagents. Input was 1,338,960,944 tokens, including 1,310,035,072 cached
tokens; output was 3,809,167, including 1,469,012 reasoning tokens. Ordinary
Sol/Terra API rates reproduce an estimated $539.23 for this period, including
$378.87 on September 4. These are estimated API equivalents, not an invoice.

About 75% of estimated cost was cached input and about 4% was reasoning.
September 4 alone had 77 root spawn calls, 29 root context compactions, and
40 launches of the exact full-suite command `uv run pytest -q`. Distinct agents
are not concurrent agents; test launches are not necessarily successful runs.
The inspection found no request that day above the suggested 272K pricing
threshold. Expensive model choice amplified a context/response/rework problem.

The work produced substantial features. At `ea2d6e1`, project lifecycle, typed
editing, exact repair, and Gate/Approval are implemented; M1-C real generation
and independent content review remain open. Replanning completed features would
add rework. ADRs 0018, 0019, and 0022 record repeated timing, identity, continuity,
and correction-contract failures discovered during live preflights.

## Decision

Use the following evidence-to-action rules, reflected in root `AGENTS.md`.

| Observed lesson | Required behavior | Evidence at the checkpoint |
|---|---|---|
| Repeated large contexts dominated cost | One bounded outcome; a compact brief based on verified repository state; targeted reads | Baseline, scope, result, and available response/context/cost deltas |
| Coordination and overlapping reviews multiplied work | One implementation owner; separate ownership for delegates; one review of a stable candidate, reopened only for a concrete reason | Delegate scope, review disposition, and any reopening reason |
| Full verification repeatedly ran while contracts changed | Focused checks during edits; complete required checks on a stable candidate; justified repeats | Commands/results and why broader or repeated checks were needed |
| Model-owned arithmetic/identity caused avoidable failures | Check author/model/code field ownership before extending repairs | A short ownership decision referencing the controlling ADR |
| Infrastructure evidence was confused with product evidence | After one supporting-tool checkpoint, attempt the product outcome | A real observable outcome or an explicit blocker; no inferred acceptance |
| Long jobs encouraged frequent model-driven polling | Use existing completion/error mechanisms and compact terminal receipts | Terminal result, frozen source identity, and unresolved lifecycle state |
| Token totals alone obscure cost | Separate fresh input, cached input, and output; reasoning is an output subset | Measured or explicitly unavailable usage; assumptions for estimated cost |

A checkpoint starts with a short brief containing verified HEAD and worktree
state, one observable outcome, owned scope, acceptance evidence, and a stopping
condition. It ends with the result, commit/worktree state, check results, gaps,
next action, and available usage deltas. Use the completion plan's active record
instead of creating a separate reporting system. The capability matrix remains
the product-level progress authority.

GPT-5.6 Terra is the user's default for subagents. Primary-model choice is based
on measured cost per accepted result and the reasoning needed; this ADR does
not assert that a cheaper model or lower effort is always cheaper overall.
Use existing usage data. If delayed or absent, report that limitation rather
than blocking product work to build a meter. Spend or response guardrails may
be agreed for a task, but must not be described as enforced without a mechanism.

If a targeted fix leaves the same failure class unresolved, checkpoint and
reassess the contract, ownership, and smallest useful experiment. Another
general review or another full pipeline run requires an explicit causal reason.
Unknown submission outcomes continue to follow existing recovery policy and
must not be blindly replayed.

## Rejected alternatives

- **Only switch the primary model.** This leaves the measured multiplication of
  responses and context untouched and assumes equal completion efficiency.
- **Restart the product milestones.** Existing implementation and evidence must
  be preserved; verification gaps do not imply features are absent.
- **Set an unconditional one-test-run rule or invented token cap.** Later
  material changes need verification; a proposed limit is not enforcement.
- **Add a general monitoring/orchestration framework.** Existing task, receipt,
  test, and usage mechanisms are adequate for the next bounded delivery.
- **Silently repair arbitrary model output.** Moving deterministic ownership
  requires an explicit versioned contract and retained raw evidence; ambiguity
  and creative decisions cannot be guessed by a binder.

## Consequences

Progress is evaluated through accepted product outcomes and their evidence,
with cost as a measured efficiency signal. Behavioral rules are discoverable
by future agents through `AGENTS.md`; they are not an automatic spending cap.
The first bounded M1-C checkpoints will calibrate the operating approach.
Existing security, immutable history, atomic installation, model neutrality,
and formal Alpha gates remain authoritative.

## Related records

- [M1-C completion plan](../roadmap/m1c-completion-plan.md)
- [Capability matrix](../roadmap/capability-matrix.md)
- [Trusted timing ownership](0018-trusted-story-timing-allocation.md)
- [Fragment and join contracts](0019-exact-fragment-and-join-state-contracts.md)
- [Current correction contracts](0022-executable-correction-contracts.md)
- [Formal Alpha acceptance](../alpha-acceptance.md)
