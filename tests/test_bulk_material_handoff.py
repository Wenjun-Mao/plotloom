"""Whole-pack structured evidence, atomicity and historical read admission."""
from contextlib import closing
from copy import deepcopy

import pytest
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from plotloom.autopilot_handoff_contracts import BulkHumanHandoffRequest, HumanHandoffRequest
from plotloom.exceptions import InvalidTransitionError
from plotloom.persistence.codec import stable_hash
from plotloom.persistence.project.autopilot_authority import video_eligible
from plotloom.persistence.project.autopilot_handoff import record_handoff, review_material
from plotloom.persistence.schema import AutopilotHandoffRow, SamePersonReviewRow
from plotloom.project_storage.autopilot_validation import assert_autopilot_contracts
from plotloom.project_storage.format import ProjectStorageCorruptionError
from tests.autopilot_handoff_seed_fixtures import copy_awaiting_handoff_seed


def bulk_observation(review):
    return {"basis": "whole-pack-material.v1", "expectedRunRevision": review["runRevision"], "bundleHash": review["bundleHash"],
        "endorsedReferenceIds": [item["decisionId"] for item in review["bundle"]["references"]],
        "frames": [{"shotId": frame["shotId"], "assetId": frame["assetId"], "intentContext": frame["intentContext"],
            "intent": deepcopy(frame["intentContext"]["intent"]), "compatibility": "pass",
            "comparisons": [{"characterId": identifier, "judgment": "pass"} for identifier in frame["characterIds"]]}
            for frame in review["bundle"]["frames"]]}


def test_bulk_confirmation_stores_truthful_evidence_and_reopens(tmp_path, awaiting_handoff_seed):
    from fastapi.testclient import TestClient
    from plotloom.api import create_project_folder_authoring_app
    storage, view, _ = copy_awaiting_handoff_seed(awaiting_handoff_seed, tmp_path / "bulk")
    with closing(storage.projects.open(view.project_id)) as store:
        request = BulkHumanHandoffRequest.model_validate(bulk_observation(review_material(store)))
        client = TestClient(create_project_folder_authoring_app(storage))
        response = client.post(f"/api/v2/projects/{view.project_id}/autopilot/handoff", json=request.model_dump(mode="json", by_alias=True))
        assert response.status_code == 200, response.text
        result = store.repository.autopilot.current(view.project_id)
        with store.repository._read() as session:
            assert video_eligible(session, view.project_id)
            retained = session.get(AutopilotHandoffRow, result.handoff["receiptId"])
            assert retained.receipt["version"] == "pre-video.handoff.v3"
            assert retained.receipt["observation"]["basis"] == "whole-pack-material.v1"
            for row in session.scalars(select(SamePersonReviewRow)):
                assert row.reviewer == "" and row.notes == ""
                for item in row.comparisons:
                    assert "identityNotes" not in item and "stateNotes" not in item
                    assert item["confirmation"]["receiptId"] == retained.id
            before = deepcopy(retained.receipt)
        with store.repository.engine.connect() as connection:
            assert_autopilot_contracts(connection.connection.driver_connection)
            assert connection.exec_driver_sql("SELECT count(*) FROM v2_video_jobs").scalar() == 0
    with closing(storage.projects.open(view.project_id)) as store:
        with store.repository._read() as session:
            assert video_eligible(session, view.project_id)
            assert session.get(AutopilotHandoffRow, result.handoff["receiptId"]).receipt == before
        # Complete existing intent context is bound into subsequent review.
        fresh = review_material(store)
        assert all(frame["intentContext"]["kind"] == "reviewed_intent" for frame in fresh["bundle"]["frames"])
        assert record_handoff(store, BulkHumanHandoffRequest.model_validate(bulk_observation(fresh))).state == "handed_off"


@pytest.mark.parametrize("defect", ["missing", "references", "flag", "fail", "hold", "context", "asset", "stale", "source_text", "source_revision"])
def test_bulk_rejects_partial_or_changed_scope_without_writes(tmp_path, awaiting_handoff_seed, defect):
    storage, view, _ = copy_awaiting_handoff_seed(awaiting_handoff_seed, tmp_path / "bulk")
    with closing(storage.projects.open(view.project_id)) as store:
        body = deepcopy(bulk_observation(review_material(store)))
        if defect == "missing": body["frames"].pop()
        elif defect == "references": body["endorsedReferenceIds"].pop()
        elif defect == "flag": body["frames"][0].update(compatibility="hold", comment="Needs review")
        elif defect == "fail": body["frames"][0]["comparisons"][0].update(judgment="fail", comment="Different identity")
        elif defect == "hold": body["frames"][0]["comparisons"][0].update(judgment="unassessable", productionDecision="hold", uncertaintyReason="Back view")
        elif defect == "context": body["frames"][0]["intentContext"]["contentHash"] = "f" * 64
        elif defect == "asset": body["frames"][0]["assetId"] = "foreign"
        elif defect == "source_text": body["frames"][0]["intent"]["compositionIntent"] += " Forged source text."
        elif defect == "source_revision": body["frames"][0]["intent"]["sourceEndorsement"]["revision"] += 1
        else: body["bundleHash"] = "a" * 64
        with pytest.raises(InvalidTransitionError):
            record_handoff(store, BulkHumanHandoffRequest.model_validate(body))
        with store.repository.engine.connect() as connection:
            for table in ("v2_approval_decisions", "v2_visual_intents", "v2_reviewed_shot_bindings", "v2_same_person_reviews", "v2_autopilot_handoffs"):
                assert connection.exec_driver_sql(f'SELECT count(*) FROM "{table}"').scalar() == 0


def test_bulk_uncertainty_is_explicit_and_manual_inputs_stay_strict(tmp_path, awaiting_handoff_seed):
    storage, view, _ = copy_awaiting_handoff_seed(awaiting_handoff_seed, tmp_path / "bulk")
    with closing(storage.projects.open(view.project_id)) as store:
        body = bulk_observation(review_material(store))
        with pytest.raises(ValidationError): HumanHandoffRequest.model_validate(body)
        item = body["frames"][0]["comparisons"][0]
        item["judgment"] = "unassessable"
        with pytest.raises(ValidationError): BulkHumanHandoffRequest.model_validate(body)
        item.update(productionDecision="authorize", uncertaintyReason="Intentional back view; accept uncertainty.")
        result = record_handoff(store, BulkHumanHandoffRequest.model_validate(body))
        with store.repository._read() as session:
            row = session.get(AutopilotHandoffRow, result.handoff["receiptId"])
            assert row.receipt["observation"]["frames"][0]["comparisons"][0]["judgment"] == "unassessable"
            assert video_eligible(session, view.project_id)


@pytest.mark.parametrize("defect", ["receipt", "comparison", "binding", "context"])
def test_forged_bulk_links_grant_no_eligibility(tmp_path, awaiting_handoff_seed, defect):
    storage, view, _ = copy_awaiting_handoff_seed(awaiting_handoff_seed, tmp_path / "bulk")
    with closing(storage.projects.open(view.project_id)) as store:
        result = record_handoff(store, BulkHumanHandoffRequest.model_validate(bulk_observation(review_material(store))))
        with store.repository.engine.connect() as connection:
            with connection.begin():
                raw_connection = connection.connection.driver_connection
                if defect == "receipt":
                    connection.exec_driver_sql("DELETE FROM v2_autopilot_handoffs")
                elif defect == "comparison":
                    connection.exec_driver_sql("UPDATE v2_same_person_reviews SET comparisons=json_set(comparisons,'$[0].confirmation.receiptId','forged')")
                else:
                    import json
                    raw, = connection.exec_driver_sql("SELECT receipt FROM v2_autopilot_handoffs").one()
                    value = json.loads(raw)
                    if defect == "binding": value["bindings"][0]["bindingId"] = value["bindings"][1]["bindingId"]
                    else: value["bundle"]["frames"][0]["intentContext"]["contentHash"] = "e" * 64
                    connection.exec_driver_sql("UPDATE v2_autopilot_handoffs SET receipt=?,receipt_hash=?", (json.dumps(value), stable_hash(value)))
                with pytest.raises(ProjectStorageCorruptionError): assert_autopilot_contracts(raw_connection)
                with Session(bind=connection) as session:
                    assert not video_eligible(session, view.project_id)
                    review = session.scalar(select(SamePersonReviewRow))
                    assert not store.repository._media.same_person.same_person_review_is_production_eligible_in_session(session, view.project_id, review)
                connection.rollback()


@pytest.mark.parametrize("change_source", [False, True])
def test_bulk_preserves_cross_shot_source_authority_and_rejects_source_edits(tmp_path, awaiting_handoff_seed, change_source):
    from tests.test_cross_shot_handoff import shared_frames
    from plotloom.persistence.schema import ReviewedShotBindingRow, VisualIntentRow
    storage, project_id = shared_frames(tmp_path, awaiting_handoff_seed)
    with closing(storage.projects.open(project_id)) as store:
        material = review_material(store)
        body = bulk_observation(material)
        source, target = material["bundle"]["frames"][:2]
        with store.repository._read() as session:
            source_intent_id = session.get(ReviewedShotBindingRow, source["sourceId"]).visual_intent_id
        if change_source:
            body["frames"][0]["intent"]["compositionIntent"] += " Changed source intent."
            with pytest.raises(InvalidTransitionError, match="required source intent"):
                record_handoff(store, BulkHumanHandoffRequest.model_validate(body))
        else:
            record_handoff(store, BulkHumanHandoffRequest.model_validate(body))
            current = review_material(store)
            assert current["bundle"]["frames"][1]["targetUse"] == target["targetUse"]
            with store.repository._read() as session:
                binding = session.get(ReviewedShotBindingRow, current["bundle"]["frames"][0]["sourceId"])
                assert binding.visual_intent_id == source_intent_id
                assert session.get(VisualIntentRow, binding.visual_intent_id).intent["compositionIntent"] == body["frames"][0]["intent"]["compositionIntent"]


def test_later_named_failure_blocks_bulk_pass_without_falling_back(tmp_path, awaiting_handoff_seed):
    from plotloom.persistence.schema import SamePersonReviewStateRow
    storage, view, _ = copy_awaiting_handoff_seed(awaiting_handoff_seed, tmp_path / "latest")
    with closing(storage.projects.open(view.project_id)) as store:
        record_handoff(store, BulkHumanHandoffRequest.model_validate(bulk_observation(review_material(store))))
        owner = store.repository._media.same_person
        with store.repository._read() as session:
            old = session.scalar(select(SamePersonReviewRow))
            revision = session.get(SamePersonReviewStateRow, view.project_id).revision
        owner.record_same_person_review(view.project_id, binding_id=old.binding_id, expected_review_revision=revision,
            reviewer="Disposable fixture human", notes="Later explicit identity refusal.",
            comparisons=[{"characterId": item["characterId"], "judgment": "fail", "identityNotes": "Different face.", "stateNotes": "Wrong visible state."} for item in old.comparisons])
        with store.repository._read() as session:
            assert not owner.same_person_review_is_production_eligible_in_session(session, view.project_id, session.get(SamePersonReviewRow, old.id))
            assert not video_eligible(session, view.project_id)


def test_exact_long_canonical_direction_is_source_endorsed_not_authored_input(tmp_path, monkeypatch):
    from tests import autopilot_image_fixtures
    from plotloom.managed_media import VisualIntentInput
    from plotloom.persistence.schema import VisualIntentRow
    original = autopilot_image_fixtures._compact_handoff_storyboard
    exact_suffix = "Exact saved source direction preserved without author attribution. " * 40

    def long_board(*args, **kwargs):
        value = original(*args, **kwargs)
        value["episodes"][0]["segments"][0]["cuts"][0]["frame"] += exact_suffix
        return value

    monkeypatch.setattr(autopilot_image_fixtures, "_compact_handoff_storyboard", long_board)
    storage, _registry, service, view, _calls, _text = autopilot_image_fixtures.handoff_image_environment(tmp_path, monkeypatch, cuts_per_scene=2)
    try:
        autopilot_image_fixtures.run_pack(storage, service, view)
        with closing(storage.projects.open(view.project_id)) as store:
            current = review_material(store)
            context = current["bundle"]["frames"][0]["intentContext"]
            direction = context["intent"]["compositionIntent"]
            assert len(direction) > 2000 and exact_suffix.rstrip() in direction
            assert context["intent"]["sourceEndorsement"]["entityRevisionId"] == current["bundle"]["inventory"]["entityRevisionId"]
            with pytest.raises(ValidationError):
                VisualIntentInput(role="shot_keyframe", composition_intent=direction, source_refs=["authored"])
            with pytest.raises(InvalidTransitionError, match="handoff authority"):
                store.media.create_visual_intent(view.project_id, current["bundle"]["frames"][0]["assetId"], context["intent"])
            result = record_handoff(store, BulkHumanHandoffRequest.model_validate(bulk_observation(current)))
            with store.repository._read() as session:
                receipt = session.get(AutopilotHandoffRow, result.handoff["receiptId"])
                intent = session.get(VisualIntentRow, receipt.receipt["bindings"][0]["intentId"])
                assert intent.intent["compositionIntent"] == direction
                assert "sourceEndorsement" in intent.intent
        with closing(storage.projects.open(view.project_id)) as store:
            fresh = review_material(store)
            assert fresh["bundle"]["frames"][0]["intentContext"]["intent"]["compositionIntent"] == direction
            assert record_handoff(store, BulkHumanHandoffRequest.model_validate(bulk_observation(fresh))).state == "handed_off"
    finally:
        service.close()
