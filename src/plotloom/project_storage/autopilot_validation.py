"""Validate persisted machine provenance without reinterpreting human history."""
import json

from ..autopilot_contracts import (
    CheckpointEvidence,
    LaunchPolicy,
    MachineDecision,
    ProvisionalFrame,
)
from ..codex_exec_contracts import (
    CodexExecAttempt,
    CodexExecReceipt,
    assert_receipt_matches_attempt,
)
from ..persistence.codec import stable_hash
from ..persistence.project.autopilot_bindings import (
    _assert_checkpoint_binding,
    _retained_checkpoint_validation_plan,
    assert_frame_binding,
)
from ..persistence.project.autopilot_profile_construction import _ProfileConstruction
from .format import ProjectStorageCorruptionError

STATES = {"running", "waiting", "paused", "cancelled", "stale", "blocked", "awaiting_review", "handed_off", "taken_over"}


def assert_autopilot_contracts(connection, *, asset_home=None, continuation=True):
    profile_construction = _ProfileConstruction()
    try:
        if continuation:
            from ..persistence.project.autopilot_continuation import (
                assert_continuation_lineage,
            )
            assert_continuation_lineage(connection)
        runs = {}
        run_policies = {}
        for identifier, project, policy, digest, brief_hash, state, bundle, bundle_hash, handoff in connection.execute(
                "SELECT id,project_id,policy,policy_hash,brief_hash,state,bundle,bundle_hash,handoff FROM v2_autopilot_runs"):
            raw = json.loads(policy)
            parsed = LaunchPolicy.model_validate(raw)
            if stable_hash(raw) != digest or stable_hash(parsed.brief) != brief_hash or state not in STATES:
                raise ValueError("run policy or state changed")
            if bundle is not None and stable_hash(json.loads(bundle)) != bundle_hash:
                raise ValueError("material bundle hash changed")
            if bundle is not None:
                from .material_bundle_validation import assert_material_bundle
                assert_material_bundle(connection, identifier, project, digest, parsed, json.loads(bundle))
            if state == "handed_off" and handoff is None:
                raise ValueError("handed-off run lacks immutable review evidence")
            runs[identifier] = (project, digest)
            run_policies[identifier] = parsed
        for identifier, run_id, project, operation_key, state, raw in connection.execute("SELECT id,run_id,project_id,operation_key,state,evidence FROM v2_autopilot_checkpoints"):
            parsed = CheckpointEvidence.model_validate_json(raw)
            _assert_checkpoint_binding(connection, project, state, parsed, run_id=run_id,
                operation_key=operation_key, asset_home=asset_home,
                validation_plan_for_request=_retained_checkpoint_validation_plan,
                profile_construction=profile_construction, continuation=continuation)
            if run_id not in runs or runs[run_id][0] != project:
                raise ValueError("checkpoint run identity changed")
        if connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='v2_autopilot_exec_attempts'").fetchone():
            budget_totals = {}
            for attempt_id, run_id, project, operation_key, job_id, domain, state, budget_state, reserved, snapshot, raw_receipt in connection.execute(
                    "SELECT id,run_id,project_id,operation_key,job_id,domain,state,image_budget_state,reserved_image_outputs,snapshot,receipt FROM v2_autopilot_exec_attempts"):
                raw_attempt = json.loads(snapshot)
                attempt = CodexExecAttempt.model_validate(raw_attempt)
                if (str(attempt.attempt_id), str(attempt.run_id), str(attempt.project_id), attempt.operation_key,
                        attempt.job_id, attempt.domain, attempt.state, attempt.image_budget_state,
                        attempt.reserved_image_outputs) != (attempt_id, run_id, project, operation_key, job_id, domain, state, budget_state, reserved):
                    raise ValueError("project CLI attempt index differs from its typed snapshot")
                if attempt.model_dump(mode="json", by_alias=True) != raw_attempt:
                    raise ValueError("project CLI attempt snapshot is not canonical")
                receipt = CodexExecReceipt.model_validate_json(raw_receipt) if raw_receipt is not None else None
                if attempt.state in {"completed", "settled"} and attempt.terminal_result == "success":
                    if receipt is None:
                        raise ValueError("successful project CLI attempt lacks its typed host receipt")
                    assert_receipt_matches_attempt(attempt, receipt)
                elif receipt is not None:
                    raise ValueError("non-successful project CLI attempt cannot retain a success receipt")
                if runs.get(run_id, (None,))[0] != project:
                    raise ValueError("project CLI attempt run identity changed")
                policy = run_policies[run_id]
                if policy.version == "plotloom.pre-video.v4" and (
                        policy.executor_binding is None or attempt.profile_hash != policy.executor_binding.profile_hash):
                    raise ValueError("project CLI attempt profile differs from its frozen launch")
                if (policy.version == "plotloom.pre-video.v4"
                        and policy.executor_binding.contract_version in {"plotloom.codex-exec.v5", "plotloom.codex-exec.v6", "plotloom.codex-exec.v7", "plotloom.codex-exec.v8"}
                        and attempt.plotloom_code_revision != policy.code_revision):
                    raise ValueError("project CLI attempt Plotloom source revision differs from its frozen launch")
                if (policy.version == "plotloom.pre-video.v4"
                        and policy.executor_binding.contract_version in {"plotloom.codex-exec.v6", "plotloom.codex-exec.v7", "plotloom.codex-exec.v8"}
                        and attempt.domain == "text" and attempt.validation_plan_hash is None):
                    raise ValueError("fresh text CLI attempt omits its frozen trusted validation plan")
                checkpoint = connection.execute(
                    "SELECT evidence FROM v2_autopilot_checkpoints WHERE run_id=? AND operation_key=?",
                    (run_id, operation_key),
                ).fetchone()
                if checkpoint is None:
                    raise ValueError("project CLI attempt has no owning stage checkpoint")
                evidence = CheckpointEvidence.model_validate_json(checkpoint[0])
                if (evidence.executor_attempt_id != attempt.attempt_id or evidence.job_id != attempt.job_id
                        or evidence.request_hash != attempt.request_hash):
                    raise ValueError("project CLI attempt differs from its stage checkpoint")
                expected_receipt = attempt.evidence_hash if attempt.state in {"completed", "failed", "settled"} else None
                if evidence.executor_receipt_hash != expected_receipt:
                    raise ValueError("project CLI receipt binding differs from its terminal attempt")
                if attempt.domain == "image" and attempt.image_budget_state in {"reserved", "consumed"}:
                    budget_totals[run_id] = budget_totals.get(run_id, 0) + attempt.reserved_image_outputs
            for run_id, reserved in budget_totals.items():
                if reserved > run_policies[run_id].max_images:
                    raise ValueError("project CLI image reservations exceed the frozen run budget")
        for run_id, project, scope, checkpoint, raw in connection.execute("SELECT run_id,project_id,scope,checkpoint_id,decision FROM v2_autopilot_decisions"):
            parsed = MachineDecision.model_validate_json(raw)
            if runs.get(run_id) != (project, parsed.policy_hash) or parsed.scope.value != scope:
                raise ValueError("machine decision identity changed")
            retained = connection.execute("SELECT run_id,project_id,evidence FROM v2_autopilot_checkpoints WHERE id=?", (checkpoint,)).fetchone()
            if retained is None or retained[:2] != (run_id, project):
                raise ValueError("decision checkpoint ownership changed")
            recorded = CheckpointEvidence.model_validate_json(retained[2])
            for field in ("owner", "subject_id", "job_id", "request_hash", "execution_pin", "geometry_preparation"):
                if getattr(parsed.evidence, field) != getattr(recorded, field):
                    raise ValueError("decision native owner differs from checkpoint")
            if parsed.evidence.delivery_hash not in {None, recorded.delivery_hash} or any(recorded.result.get(key) != value for key, value in parsed.evidence.result.items()):
                raise ValueError("decision retained evidence differs from checkpoint")
            retained_checkpoint = connection.execute(
                "SELECT operation_key FROM v2_autopilot_checkpoints WHERE id=?", (checkpoint,)
            ).fetchone()
            _assert_checkpoint_binding(connection, project,
                "delivered" if parsed.evidence.delivery_hash else "prepared", parsed.evidence,
                run_id=run_id, operation_key=retained_checkpoint[0], asset_home=asset_home,
                validation_plan_for_request=_retained_checkpoint_validation_plan,
                profile_construction=profile_construction, continuation=continuation)
        for run_id, project, shot, job, asset, decision, raw in connection.execute("SELECT run_id,project_id,shot_id,job_id,asset_id,decision_id,frame FROM v2_autopilot_frames"):
            parsed = ProvisionalFrame.model_validate_json(raw)
            if runs.get(run_id, (None,))[0] != project or (parsed.shot_id, parsed.job_id, parsed.asset_id) != (shot, job, asset):
                raise ValueError("provisional frame identity changed")
            assert_frame_binding(connection, run_id, project, decision, parsed, asset_home=asset_home, continuation=continuation)
        from .bridge_adoption_validation import assert_bridge_adoption_contracts
        if continuation:
            assert_bridge_adoption_contracts(connection)
        else:
            from functools import partial
            assert_bridge_adoption_contracts(connection, checkpoint_validator=partial(_assert_checkpoint_binding,
                asset_home=asset_home, validation_plan_for_request=_retained_checkpoint_validation_plan, continuation=False))
        from .handoff_validation import assert_handoff
        receipts = {}
        unnamed_approvals, unnamed_reviews = set(), set()
        source_intents = set()
        for identifier, run_id, project, approval, raw, digest in connection.execute("SELECT id,run_id,project_id,approval_id,receipt,receipt_hash FROM v2_autopilot_handoffs"):
            if runs.get(run_id, (None,))[0] != project:
                raise ValueError("human handoff run changed")
            receipt = assert_handoff(connection, identifier, run_id, project, approval, json.loads(raw), digest, asset_home=asset_home, continuation=continuation)
            if receipt.version == "pre-video.handoff.v3":
                source_intents.update(fact["intentId"] for fact, observation in zip(receipt.bindings, receipt.observation.frames, strict=True)
                    if "sourceEndorsement" in observation.intent.model_dump(mode="json", by_alias=True))
            receipts[identifier] = (run_id, digest, receipt.bundle_hash, receipt.material_closure)
            if receipt.version in {"pre-video.handoff.v2", "pre-video.handoff.v3"}:
                if receipt.approval_origin == "created":
                    unnamed_approvals.add(receipt.approval_id)
                unnamed_reviews.update(fact["samePersonReviewId"] for fact in receipt.bindings if "samePersonReviewId" in fact)
        # An empty reviewer is an explicit no-name encoding only for validated
        # creator confirmation facts; it cannot legitimize an orphan/manual row.
        for table, admitted in (("v2_approval_decisions", unnamed_approvals), ("v2_same_person_reviews", unnamed_reviews)):
            for identifier, reviewer in connection.execute(f'SELECT id,reviewer FROM "{table}" WHERE trim(reviewer)=\'\''):
                if reviewer != "" or identifier not in admitted:
                    raise ValueError("unnamed human fact lacks exact creator confirmation evidence")
        for identifier, project, payload in connection.execute("SELECT id,project_id,intent FROM v2_visual_intents"):
            value = json.loads(payload)
            if "sourceEndorsement" in value:
                if identifier not in source_intents:
                    raise ValueError("source-endorsed intent lacks exact whole-pack receipt evidence")
                from ..persistence.project.handoff_intent_context import assert_source_intent
                assert_source_intent(connection, project, {key: item for key, item in value.items() if key != "targetUse"})
        for run_id, pointer in connection.execute("SELECT id,handoff FROM v2_autopilot_runs WHERE handoff IS NOT NULL"):
            value = json.loads(pointer)
            if receipts.get(value.get("receiptId")) != (run_id, value.get("receiptHash"), value.get("bundleHash"), value.get("materialClosure")):
                raise ValueError("current human handoff pointer changed")
    except (ValueError, TypeError, KeyError) as error:
        raise ProjectStorageCorruptionError("persisted autopilot authority is invalid") from error
