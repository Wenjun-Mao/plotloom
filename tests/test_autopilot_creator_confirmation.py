"""Unnamed creator confirmation, unchanged optional prose and retained v1 evidence."""

import json
from contextlib import closing
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError
from sqlalchemy import select

from plotloom.api.contracts import StoryboardApprovalRequest
from plotloom.api.models import _approval_decision_view
from plotloom.autopilot_contracts import OperationScope
from plotloom.autopilot_handoff_contracts import (
    HumanHandoffRequest,
    parse_handoff_receipt,
)
from plotloom.exceptions import InvalidTransitionError, RevisionConflictError
from plotloom.human_confirmation_contracts import UnnamedCreatorConfirmation
from plotloom.persistence.codec import stable_hash
from plotloom.persistence.project.autopilot_authority import video_eligible
from plotloom.persistence.project.autopilot_closure import material_closure
from plotloom.persistence.project.autopilot_handoff import (
    record_handoff,
    review_material,
)
from plotloom.persistence.project.human_attribution import stored_reviewer
from plotloom.persistence.schema import (
    ApprovalDecisionRow,
    AutopilotHandoffRow,
    SamePersonReviewRow,
)
from plotloom.project_storage.autopilot_validation import assert_autopilot_contracts
from plotloom.project_storage.format import ProjectStorageCorruptionError
from plotloom.same_person_review_contracts import SamePersonReviewRequest
from tests.autopilot_image_fixtures import handoff_image_environment, run_pack
from tests.test_autopilot_handoff import observation
from tests.test_autopilot_recovery import storage_at


@pytest.mark.parametrize("comment", [None, "", " \n\t", "  原样保留这段备注。\n"])
def test_optional_comment_is_absent_or_preserves_exact_authored_bytes(comment):
    raw = {"expectedRunRevision": 1, "bundleHash": "a" * 64, "endorsedReferenceIds": [], "frames": []}
    if comment is not None:
        raw["notes"] = comment
    request = HumanHandoffRequest.model_validate(raw)
    dumped = request.model_dump(mode="json", by_alias=True)
    assert "reviewer" not in dumped
    if comment is None or not comment.strip():
        assert "notes" not in dumped
    else:
        assert dumped["notes"] == comment
    for extra in ({"reviewer": "Invented actor"}, {"authority": "machine"}):
        with pytest.raises(ValidationError):
            HumanHandoffRequest.model_validate(raw | extra)


@pytest.mark.parametrize("scope", [None, OperationScope.TEXT, OperationScope.IMAGE, OperationScope.EVIDENCE])
def test_unnamed_attribution_requires_exact_handoff_scope(scope):
    access = SimpleNamespace(authority=lambda: SimpleNamespace(scope=scope) if scope else None)
    with pytest.raises(InvalidTransitionError, match="handoff authority"):
        stored_reviewer(access, UnnamedCreatorConfirmation())
    assert stored_reviewer(access, " Actual named reviewer ") == "Actual named reviewer"
    with pytest.raises(ValueError, match="manual reviewer"):
        stored_reviewer(access, "  ")


@pytest.mark.parametrize("reviewer", [None, "", " \t"])
def test_manual_approval_and_identity_requests_keep_their_named_review_contract(reviewer):
    board = {"expectedRevision": 1, "contentHash": "a" * 64, "decision": "approve", "gateSetVersion": "storyboard.v2"}
    identity = {"bindingId": "fixture", "expectedReviewRevision": 0, "notes": "Actual manual frame observation.",
        "comparisons": [{"characterId": "hero", "judgment": "pass", "identityNotes": "Visible face matches reference.", "stateNotes": "Visible wardrobe and action inspected."}]}
    for model, raw in ((StoryboardApprovalRequest, board), (SamePersonReviewRequest, identity)):
        if reviewer is not None:
            raw["reviewer"] = reviewer
        with pytest.raises(ValidationError):
            model.model_validate(raw)


@pytest.mark.parametrize("comment", [None, "  创作者的可选备注。\n"])
def test_exact_choices_succeed_without_a_name_and_store_no_invented_actor_or_comment(tmp_path, monkeypatch, comment):
    storage, _registry, service, view, calls, _text = handoff_image_environment(tmp_path, monkeypatch)
    try:
        complete = run_pack(storage, service, view)
        with closing(storage.projects.open(view.project_id)) as store:
            body = observation(review_material(store))
            if comment is not None:
                body["notes"] = comment
            request = HumanHandoffRequest.model_validate(body)
            with pytest.raises(RevisionConflictError):
                record_handoff(store, request.model_copy(update={"expected_run_revision": complete.revision + 1}))
            with pytest.raises(InvalidTransitionError, match="material changed"):
                record_handoff(store, request.model_copy(update={"bundle_hash": "a" * 64}))
            result = record_handoff(store, request)
            assert result.state == "handed_off"
            with store.repository._read() as session:
                retained = session.get(AutopilotHandoffRow, result.handoff["receiptId"])
                raw = retained.receipt
                assert raw["version"] == "pre-video.handoff.v2"
                assert raw["attribution"] == {"kind": "unnamed_creator"}
                assert "reviewer" not in raw["observation"]
                assert raw["observation"].get("notes") == comment
                assert ("notes" in raw["observation"]) == (comment is not None)
                assert stable_hash(parse_handoff_receipt(raw).model_dump(mode="json", by_alias=True)) == retained.receipt_hash
                approval = session.get(ApprovalDecisionRow, retained.approval_id)
                assert approval.reviewer == "" and approval.note == comment
                assert all(row.reviewer == "" for row in session.scalars(select(SamePersonReviewRow)))
                assert video_eligible(session, view.project_id)
            approval = store.repository._approvals.list_approval_decisions(view.project_id)[0]
            projection = _approval_decision_view(approval).model_dump(mode="json", by_alias=True)
            assert projection["reviewer"] == "" and projection["attribution"] == {"kind": "unnamed_creator"}
            reviews = store.repository._media.same_person.list_same_person_reviews(view.project_id)["reviews"]
            assert all(row["reviewer"] == "" and row["attribution"] == {"kind": "unnamed_creator"} for row in reviews)
            assert all(row["notes"] == body["frames"][0]["compatibilityNote"] for row in reviews)
            with store.repository.engine.connect() as connection:
                assert connection.exec_driver_sql("SELECT count(*) FROM v2_video_jobs").scalar() == 0
        snapshot = storage.recovery.create_snapshot(view.project_id)
        restored = storage_at(tmp_path / "restored")
        restored.recovery.restore(Path(snapshot.location))
        restored.recovery.acknowledge_recovery(view.project_id)
        with closing(restored.projects.open(view.project_id)) as store:
            with store.repository._read() as session:
                copy = session.get(AutopilotHandoffRow, result.handoff["receiptId"])
                assert copy.receipt == raw and copy.receipt_hash == stable_hash(raw)
                assert video_eligible(session, view.project_id)
        assert len(calls) == len(complete.frames) + 2
    finally:
        service.close()


def _install_synthetic_retained_v1(store, result):
    """Disposable historical fixture setup; never convert production records."""
    with store.repository._write() as session:
        run = store.repository.autopilot.row(session, store.manifest.project_id)
        retained = session.get(AutopilotHandoffRow, result.handoff["receiptId"])
        raw = json.loads(json.dumps(retained.receipt))
        raw["version"] = "pre-video.handoff.v1"
        del raw["attribution"]
        raw["observation"].update(reviewer="Historical fixture human", notes="Retained historical fixture observation.")
        approval = session.get(ApprovalDecisionRow, retained.approval_id)
        approval.reviewer, approval.note = raw["observation"]["reviewer"], raw["observation"]["notes"]
        for row in session.scalars(select(SamePersonReviewRow)):
            row.reviewer = raw["observation"]["reviewer"]
        raw["materialClosure"] = material_closure(session, store.manifest.project_id)
        retained.receipt, retained.receipt_hash = raw, stable_hash(raw)
        run.handoff = run.handoff | {"receiptHash": retained.receipt_hash, "materialClosure": raw["materialClosure"]}
    return raw


def _retained_bytes(store, identifier):
    with store.repository.engine.connect() as connection:
        return tuple(connection.exec_driver_sql("SELECT receipt,receipt_hash FROM v2_autopilot_handoffs WHERE id=?", (identifier,)).one())


def test_retained_named_v1_receipt_bytes_hash_and_recovery_stay_exact(tmp_path, monkeypatch):
    storage, _registry, service, view, _calls, _text = handoff_image_environment(tmp_path, monkeypatch)
    try:
        run_pack(storage, service, view)
        with closing(storage.projects.open(view.project_id)) as store:
            result = record_handoff(store, HumanHandoffRequest.model_validate(observation(review_material(store))))
            raw = _install_synthetic_retained_v1(store, result)
            identifier = result.handoff["receiptId"]
            before = _retained_bytes(store, identifier)
            assert stable_hash(parse_handoff_receipt(raw).model_dump(mode="json", by_alias=True)) == before[1]
            approval = store.repository._approvals.list_approval_decisions(view.project_id)[0]
            projection = _approval_decision_view(approval).model_dump(mode="json", by_alias=True)
            assert projection["reviewer"] == "Historical fixture human" and "attribution" not in projection
        with closing(storage.projects.open(view.project_id)) as store:
            assert _retained_bytes(store, identifier) == before
            with store.repository._read() as session:
                assert video_eligible(session, view.project_id)
        snapshot = storage.recovery.create_snapshot(view.project_id)
        restored = storage_at(tmp_path / "legacy-restored")
        restored.recovery.restore(Path(snapshot.location))
        restored.recovery.acknowledge_recovery(view.project_id)
        with closing(restored.projects.open(view.project_id)) as store:
            assert _retained_bytes(store, identifier) == before
            with store.repository._read() as session:
                assert video_eligible(session, view.project_id)
            # A new local creator action on the recovered copy preserves the
            # old named receipt and approval; it creates only a fresh v2 receipt.
            fresh = record_handoff(store, HumanHandoffRequest.model_validate(observation(review_material(store))))
            assert _retained_bytes(store, identifier) == before
            with store.repository._read() as session:
                receipt = session.get(AutopilotHandoffRow, fresh.handoff["receiptId"])
                assert receipt.receipt["version"] == "pre-video.handoff.v2"
                assert receipt.receipt["approvalOrigin"] == "existing_human"
                approval = session.get(ApprovalDecisionRow, receipt.approval_id)
                assert approval.reviewer == "Historical fixture human"
                assert approval.note == "Retained historical fixture observation."
                assert video_eligible(session, view.project_id)
    finally:
        service.close()


@pytest.mark.parametrize("table", ["v2_approval_decisions", "v2_same_person_reviews"])
def test_ordinary_validation_refuses_unnamed_fact_without_its_receipt(tmp_path, monkeypatch, table):
    storage, _registry, service, view, _calls, _text = handoff_image_environment(tmp_path, monkeypatch)
    try:
        run_pack(storage, service, view)
        with closing(storage.projects.open(view.project_id)) as store:
            record_handoff(store, HumanHandoffRequest.model_validate(observation(review_material(store))))
            with store.repository.engine.connect() as connection:
                with connection.begin():
                    # Clone a valid fact with a distinct unlinked identity in this
                    # disposable transaction; the genuine receipt stays intact.
                    columns = [row[1] for row in connection.exec_driver_sql(f'PRAGMA table_info("{table}")')]
                    projection = ["?" if column == "id" else f'"{column}"' for column in columns]
                    connection.exec_driver_sql(f'INSERT INTO "{table}" SELECT {",".join(projection)} FROM "{table}" LIMIT 1', ("00000000-0000-4000-8000-000000000099",))
                    with pytest.raises(ProjectStorageCorruptionError, match="autopilot authority"):
                        assert_autopilot_contracts(connection.connection.driver_connection)
                    connection.rollback()
    finally:
        service.close()
