"""Validate persisted machine provenance without reinterpreting human history."""
import json

from ..autopilot_contracts import (
    CheckpointEvidence,
    LaunchPolicy,
    MachineDecision,
    ProvisionalFrame,
)
from ..persistence.codec import stable_hash
from ..persistence.project.autopilot_bindings import (
    assert_checkpoint_binding,
    assert_frame_binding,
)
from .format import ProjectStorageCorruptionError

STATES = {"running", "waiting", "paused", "cancelled", "stale", "blocked", "awaiting_review", "handed_off", "taken_over"}


def assert_autopilot_contracts(connection, *, asset_home=None):
    try:
        runs = {}
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
        for identifier, run_id, project, state, raw in connection.execute("SELECT id,run_id,project_id,state,evidence FROM v2_autopilot_checkpoints"):
            parsed = CheckpointEvidence.model_validate_json(raw)
            assert_checkpoint_binding(connection, project, state, parsed, run_id=run_id, asset_home=asset_home)
            if run_id not in runs or runs[run_id][0] != project:
                raise ValueError("checkpoint run identity changed")
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
            assert_checkpoint_binding(connection, project, "delivered" if parsed.evidence.delivery_hash else "prepared", parsed.evidence, run_id=run_id, asset_home=asset_home)
        for run_id, project, shot, job, asset, decision, raw in connection.execute("SELECT run_id,project_id,shot_id,job_id,asset_id,decision_id,frame FROM v2_autopilot_frames"):
            parsed = ProvisionalFrame.model_validate_json(raw)
            if runs.get(run_id, (None,))[0] != project or (parsed.shot_id, parsed.job_id, parsed.asset_id) != (shot, job, asset):
                raise ValueError("provisional frame identity changed")
            assert_frame_binding(connection, run_id, project, decision, parsed, asset_home=asset_home)
        from .bridge_adoption_validation import assert_bridge_adoption_contracts
        assert_bridge_adoption_contracts(connection)
        from .handoff_validation import assert_handoff
        receipts = {}
        unnamed_approvals, unnamed_reviews = set(), set()
        for identifier, run_id, project, approval, raw, digest in connection.execute("SELECT id,run_id,project_id,approval_id,receipt,receipt_hash FROM v2_autopilot_handoffs"):
            if runs.get(run_id, (None,))[0] != project:
                raise ValueError("human handoff run changed")
            receipt = assert_handoff(connection, identifier, run_id, project, approval, json.loads(raw), digest, asset_home=asset_home)
            receipts[identifier] = (run_id, digest, receipt.bundle_hash, receipt.material_closure)
            if receipt.version == "pre-video.handoff.v2":
                if receipt.approval_origin == "created":
                    unnamed_approvals.add(receipt.approval_id)
                unnamed_reviews.update(fact["samePersonReviewId"] for fact in receipt.bindings if "samePersonReviewId" in fact)
        # An empty reviewer is an explicit no-name encoding only for validated
        # creator confirmation facts; it cannot legitimize an orphan/manual row.
        for table, admitted in (("v2_approval_decisions", unnamed_approvals), ("v2_same_person_reviews", unnamed_reviews)):
            for identifier, reviewer in connection.execute(f'SELECT id,reviewer FROM "{table}" WHERE trim(reviewer)=\'\''):
                if reviewer != "" or identifier not in admitted:
                    raise ValueError("unnamed human fact lacks exact creator confirmation evidence")
        for run_id, pointer in connection.execute("SELECT id,handoff FROM v2_autopilot_runs WHERE handoff IS NOT NULL"):
            value = json.loads(pointer)
            if receipts.get(value.get("receiptId")) != (run_id, value.get("receiptHash"), value.get("bundleHash"), value.get("materialClosure")):
                raise ValueError("current human handoff pointer changed")
    except (ValueError, TypeError, KeyError) as error:
        raise ProjectStorageCorruptionError("persisted autopilot authority is invalid") from error
