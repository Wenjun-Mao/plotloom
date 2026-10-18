"""Retained AI bridge provenance is checked against its historical native owner."""
import json

from ..autopilot_contracts import MachineDecision
from ..creative_handoff_contracts import CreativeHandoffRequest
from ..machine_adoption import MachineAdoption
from ..native_bridge_presentation_contract import native_presentation_suggestions
from ..production_bridge_contracts import ProductionBridgeIntentPackage
from ..production_presentation import ProductionPresentation, PresentationUpdate, bind_presentation_spans
from ..persistence.codec import stable_hash
from ..persistence.project.autopilot_bindings import _row, assert_checkpoint_binding


def assert_adoption(connection, project, adoption: MachineAdoption, owner, *, checkpoint_validator=assert_checkpoint_binding):
    run = _row(connection, "SELECT project_id,policy_hash FROM v2_autopilot_runs WHERE id=?", (adoption.run_id,))
    decision = _row(connection, "SELECT run_id,project_id,scope,decision FROM v2_autopilot_decisions WHERE id=?", (adoption.decision_id,))
    facts = MachineDecision.model_validate_json(decision["decision"])
    expected = {"proposalRevision": adoption.proposal_revision, "proposalHash": adoption.proposal_hash}
    evidence = facts.evidence
    if (run["project_id"] != project or run["policy_hash"] != adoption.policy_hash or decision["run_id"] != adoption.run_id
            or decision["project_id"] != project or decision["scope"] != "production_installation"
            or facts.subject != expected or facts.policy_hash != adoption.policy_hash
            or evidence.owner != owner or evidence.job_id != adoption.job_id or evidence.request_hash != adoption.request_hash
            or evidence.delivery_hash != adoption.delivery_hash):
        raise ValueError("machine bridge native decision binding changed")
    checkpoint_validator(connection, project, "delivered", evidence, run_id=adoption.run_id,
        operation_key=owner)
    source = _row(connection, "SELECT content_hash,proposal FROM v2_production_bridge_revisions WHERE project_id=? AND revision=?",
        (project, adoption.proposal_revision))
    job = _row(connection, "SELECT * FROM v2_production_bridge_intent_jobs WHERE id=?", (adoption.job_id,))
    expected_revision = job["result_proposal_revision"] if owner == "bridge-intent" else job["proposal_revision"]
    if (source["content_hash"] != adoption.proposal_hash or job["project_id"] != project
            or expected_revision != adoption.proposal_revision):
        raise ValueError("machine bridge historical proposal binding changed")
    return json.loads(source["proposal"]), job


def assert_bridge_adoption_contracts(connection, *, checkpoint_validator=assert_checkpoint_binding):
    for project, revision, digest, inputs, raw, conflicts in connection.execute(
            "SELECT project_id,revision,content_hash,inputs,proposal,conflicts FROM v2_production_bridge_revisions"):
        payload = json.loads(raw)
        intent = ProductionBridgeIntentPackage.model_validate(payload["intentPackage"])
        presentation = ProductionPresentation.model_validate(payload["presentation"])
        machine_owned = intent.machine_adoption is not None or presentation.machine_adoption is not None
        if machine_owned and stable_hash({"inputs": json.loads(inputs), "proposal": payload, "conflicts": json.loads(conflicts)}) != digest:
            raise ValueError("machine bridge retained proposal bytes changed")
        if intent.machine_adoption is not None:
            adoption = intent.machine_adoption
            source, _job = assert_adoption(connection, project, adoption, "bridge-intent", checkpoint_validator=checkpoint_validator)
            original = ProductionBridgeIntentPackage.model_validate(source["intentPackage"])
            if revision <= adoption.proposal_revision or original.review_state != "model_suggested" or intent.entries != original.entries or intent.provenance != original.provenance:
                raise ValueError("machine adopted intent differs from its exact native suggestion")
        if presentation.machine_adoption is not None:
            adoption = presentation.machine_adoption
            source, job = assert_adoption(connection, project, adoption, "bridge-presentation", checkpoint_validator=checkpoint_validator)
            original = ProductionPresentation.model_validate(source["presentation"])
            request = CreativeHandoffRequest.model_validate_json(job["native_request"])
            suggestions = native_presentation_suggestions(request, json.loads(job["candidate"]))
            entries = [PresentationUpdate(id=entry.id, spans=entry.spans) for entry in suggestions.entries]
            expected_sources = bind_presentation_spans(original, entries)
            if (revision <= adoption.proposal_revision or presentation.sources != expected_sources
                    or presentation.source_hash != original.source_hash or presentation.frozen_evidence != original.frozen_evidence
                    or presentation.runtime_choice != original.runtime_choice):
                raise ValueError("machine adopted presentation differs from its exact native suggestion")
