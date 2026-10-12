"""One atomic human handoff using existing approval, intent and review owners."""
from sqlalchemy import select
from ...autopilot_contracts import CommandAuthority, OperationScope
from ...autopilot_handoff_contracts import HumanHandoffRequest, HumanHandoffReceipt
from ...domain import new_id, utc_now
from ...exceptions import InvalidTransitionError, RevisionConflictError
from ...validation import STORYBOARD_GATE_SET_VERSION
from ..codec import stable_hash
from ..schema import AutopilotHandoffRow, VisualSelectionStateRow, SamePersonReviewStateRow, ReviewedShotBindingRow, SamePersonReviewRow, ApprovalDecisionRow
from .autopilot_closure import material_closure
from .autopilot_review_bundle import current_review_bundle


def review_material(store):
    with store.repository._read() as session:
        run = store.repository.autopilot.row(session, store.manifest.project_id)
        if run is None:
            raise InvalidTransitionError("project has no pre-video run")
        return current_review_bundle(store, session, run)


def record_handoff(store, request: HumanHandoffRequest):
    repository, project_id = store.repository, store.manifest.project_id
    # This authority is constructed only by this human endpoint; it never admits
    # machine scopes or relies on an expired controller claim after takeover.
    run = repository.autopilot.current(project_id)
    if run is None:
        raise InvalidTransitionError("project has no pre-video run")
    with repository.autopilot_command(CommandAuthority(run.id, "human-handoff", OperationScope.HANDOFF)) as session:
        row = repository.autopilot.row(session, project_id)
        if row.revision != request.expected_run_revision:
            raise RevisionConflictError("autopilot", request.expected_run_revision, row.revision)
        current = current_review_bundle(store, session, row)
        if current["bundleHash"] != request.bundle_hash:
            raise InvalidTransitionError("material changed after review; reload the complete current bundle")
        bundle = current["bundle"]
        references = [item["decisionId"] for item in bundle["references"]]
        if sorted(request.endorsed_reference_ids) != sorted(references):
            raise InvalidTransitionError("explicitly endorse every exact current gallery reference once")
        expected = bundle["frames"]
        if [item.shot_id for item in request.frames] != [item["shotId"] for item in expected]:
            raise InvalidTransitionError("review every filmed shot exactly once in displayed order")
        for observation, frame in zip(request.frames, expected, strict=True):
            if observation.asset_id != frame["assetId"] or [item.character_id for item in observation.comparisons] != frame["characterIds"]:
                raise InvalidTransitionError("frame review must cover exact displayed bytes and visible characters")
            if observation.comparisons and not repository._media.same_person.comparisons_authorize_production(
                    [item.model_dump(mode="json", by_alias=True, exclude_none=True) for item in observation.comparisons]):
                raise InvalidTransitionError("failed or held identity observations cannot authorize a handoff")
        authored_intents = {}
        for observation in request.frames:
            payload = observation.intent.model_dump(mode="json", by_alias=True)
            if observation.asset_id in authored_intents and authored_intents[observation.asset_id] != payload:
                raise InvalidTransitionError("one shared asset requires the same current visual intent across its shot bindings")
            authored_intents[observation.asset_id] = payload
        inventory = bundle["inventory"]
        latest = session.scalar(select(ApprovalDecisionRow).where(ApprovalDecisionRow.project_id == project_id,
            ApprovalDecisionRow.entity_revision_id == inventory["entityRevisionId"],
            ApprovalDecisionRow.subject_type == "storyboard", ApprovalDecisionRow.subject_id == "storyboard")
            .order_by(ApprovalDecisionRow.created_at.desc(), ApprovalDecisionRow.id.desc()).limit(1))
        approval_origin = "created"
        if latest is not None and latest.decision == "approve":
            approval = repository._media.admission.approval_is_active_in_session(session, latest.id)
            approval_origin = "existing_human"
        else:
            approval = repository._approvals.decide_storyboard_approval(project_id,
                expected_revision=inventory["storyboardRevision"], expected_content_hash=inventory["storyboardHash"],
                decision="approve", reviewer=request.reviewer, gate_set_version=STORYBOARD_GATE_SET_VERSION, note=request.notes)
        facts = []
        intents = {}
        for observation, frame in zip(request.frames, expected, strict=True):
            if frame["assetId"] not in intents:
                intents[frame["assetId"]] = repository._media.intents.create_visual_intent(project_id, frame["assetId"], authored_intents[frame["assetId"]])
            intent = intents[frame["assetId"]]
            selection = session.get(VisualSelectionStateRow, project_id)
            presentation = repository._media.shot_presentations.current(session, project_id, frame["shotId"])
            binding = repository._media.keyframes.select_reviewed_keyframe(project_id, asset_id=frame["assetId"],
                shot_id=frame["shotId"], scene_id=frame["sceneId"], expected_selection_revision=selection.revision if selection else 0,
                storyboard_revision=inventory["storyboardRevision"], approval_id=approval.id,
                compatibility_note=observation.compatibility_note, visual_intent_id=intent["id"], visual_intent_revision=intent["revision"],
                expected_presentation_revision=presentation["revision"] if presentation else 0)
            fact = {"shotId": frame["shotId"], "assetId": frame["assetId"], "intentId": intent["id"], "bindingId": binding["id"]}
            if observation.comparisons:
                state = session.get(SamePersonReviewStateRow, project_id)
                review = repository._media.same_person.record_same_person_review(project_id, binding_id=binding["id"],
                    expected_review_revision=state.revision if state else 0, reviewer=request.reviewer,
                    comparisons=[item.model_dump(mode="json", by_alias=True, exclude_none=True) for item in observation.comparisons],
                    notes=observation.compatibility_note)
                if not review["productionEligible"]:
                    raise InvalidTransitionError("identity observations are no longer current")
                fact["samePersonReviewId"] = review["id"]
            facts.append(fact)
        identifier = new_id()
        closure = material_closure(session, project_id)
        receipt = HumanHandoffReceipt(id=identifier, run_id=row.id, project_id=project_id, bundle_hash=request.bundle_hash,
            bundle=bundle, observation=request, approval_id=approval.id, approval_origin=approval_origin, bindings=facts, material_closure=closure)
        raw = receipt.model_dump(mode="json", by_alias=True)
        session.add(AutopilotHandoffRow(id=identifier, run_id=row.id, project_id=project_id, approval_id=approval.id,
            receipt=raw, receipt_hash=stable_hash(raw), created_at=utc_now()))
        row.handoff = {"receiptId": identifier, "receiptHash": stable_hash(raw), "bundleHash": request.bundle_hash, "materialClosure": closure}
        row.state, row.phase, row.blocker = "handed_off", "manual-video", None
        session.flush()
        if not handoff_is_current(session, repository, row):
            raise InvalidTransitionError("the complete human handoff failed current admission")
    return repository.autopilot.current(project_id)


def handoff_is_current(session, repository, run):
    pointer = run.handoff
    if run.state != "handed_off" or not isinstance(pointer, dict):
        return False
    retained = session.get(AutopilotHandoffRow, pointer.get("receiptId"))
    if (retained is None or retained.project_id != run.project_id or retained.run_id != run.id
            or retained.receipt_hash != stable_hash(retained.receipt) or retained.receipt_hash != pointer.get("receiptHash")):
        return False
    receipt = HumanHandoffReceipt.model_validate(retained.receipt)
    if receipt.material_closure != pointer.get("materialClosure") or receipt.material_closure != material_closure(session, run.project_id):
        return False
    for fact, frame in zip(receipt.bindings, receipt.bundle.frames, strict=True):
        binding = session.get(ReviewedShotBindingRow, fact["bindingId"])
        if binding is None or not repository._media.admission.reviewed_binding_admission_eligible_in_session(session, run.project_id, binding):
            return False
        if frame.character_ids:
            review = session.get(SamePersonReviewRow, fact.get("samePersonReviewId"))
            if review is None or not repository._media.same_person.same_person_review_is_production_eligible_in_session(session, run.project_id, review):
                return False
    return True
