from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

from plotloom.api import create_app
from plotloom.domain import (
    STAGE_ORDER,
    GateEvaluation,
    GateResult,
    GateSeverity,
    GateStatus,
    StageName,
)
from plotloom.exceptions import InvalidTransitionError
from plotloom.persistence import SQLiteRepository

from .conftest import all_stage_payloads


def _install_complete_project(repository: SQLiteRepository, brief):
    project = repository.create_project(brief)
    for stage, payload in zip(STAGE_ORDER, all_stage_payloads(), strict=True):
        repository.update_stage(project.id, stage, 0, payload)
    return repository.get_project(project.id)


def test_storyboard_install_records_gates_and_approval_is_append_only(
    repository: SQLiteRepository,
    brief,
) -> None:
    project = _install_complete_project(repository, brief)
    app = create_app(repository)

    with TestClient(app) as client:
        review = client.get(f"/api/v2/projects/{project.id}/storyboard-review")
        assert review.status_code == 200
        body = review.json()
        assert body["head"]["schemaVersion"] == 2
        assert body["gateEvaluation"]["gateSetVersion"] == "storyboard.v2"
        assert body["gateEvaluation"]["results"]
        assert all(result["status"] == "pass" for result in body["gateEvaluation"]["results"])
        assert body["decisions"] == []
        assert body["activeApproval"] is None

        decision_request = {
            "expectedRevision": body["head"]["revision"],
            "contentHash": body["head"]["contentHash"],
            "decision": "approve",
            "reviewer": "Wenjun",
            "gateSetVersion": body["gateEvaluation"]["gateSetVersion"],
            "note": "Alpha review",
        }
        approved = client.post(
            f"/api/v2/projects/{project.id}/storyboard-approval",
            json=decision_request,
        )
        assert approved.status_code == 201
        assert approved.json()["active"] is True
        assert approved.json()["decision"]["decision"] == "approve"

        duplicate = client.post(
            f"/api/v2/projects/{project.id}/storyboard-approval",
            json=decision_request,
        )
        assert duplicate.status_code == 409
        assert duplicate.json()["code"] == "invalid_transition"

        revoked = client.post(
            f"/api/v2/projects/{project.id}/storyboard-approval",
            json={**decision_request, "decision": "revoke", "note": "Needs another look"},
        )
        assert revoked.status_code == 201
        assert revoked.json()["active"] is False
        assert revoked.json()["decision"]["decision"] == "revoke"

        final_review = client.get(
            f"/api/v2/projects/{project.id}/storyboard-review"
        ).json()
        assert final_review["activeApproval"] is None
        assert len(final_review["decisions"]) == 2
        assert final_review["decisions"][0]["active"] is False


def test_upstream_edit_makes_approval_stale_and_exact_preconditions_are_enforced(
    repository: SQLiteRepository,
    brief,
) -> None:
    project = _install_complete_project(repository, brief)
    app = create_app(repository)

    with TestClient(app) as client:
        review = client.get(
            f"/api/v2/projects/{project.id}/storyboard-review"
        ).json()
        request = {
            "expectedRevision": review["head"]["revision"],
            "contentHash": review["head"]["contentHash"],
            "decision": "approve",
            "reviewer": "reviewer",
            "gateSetVersion": review["gateEvaluation"]["gateSetVersion"],
            "note": None,
        }

        wrong_hash = client.post(
            f"/api/v2/projects/{project.id}/storyboard-approval",
            json={**request, "contentHash": "0" * 64},
        )
        assert wrong_hash.status_code == 409
        assert wrong_hash.json()["code"] == "invalid_transition"

        assert client.post(
            f"/api/v2/projects/{project.id}/storyboard-approval", json=request
        ).status_code == 201

        bible = all_stage_payloads()[0].model_copy(
            update={"logline": "上游文本已经改变。"}
        )
        changed = client.patch(
            f"/api/v2/projects/{project.id}/stages/story_bible",
            json={"expectedRevision": 1, "payload": bible.model_dump(mode="json", by_alias=True)},
        )
        assert changed.status_code == 200

        stale = client.get(
            f"/api/v2/projects/{project.id}/storyboard-review"
        ).json()
        assert stale["head"]["status"] == "stale"
        assert stale["activeApproval"] is None
        assert stale["decisions"][0]["active"] is False
        assert any("upstream story_bible revision changed" in reason for reason in stale["decisions"][0]["staleReasons"])

        stale_decision = client.post(
            f"/api/v2/projects/{project.id}/storyboard-approval", json=request
        )
        assert stale_decision.status_code == 409


def test_gate_result_id_is_revision_scoped_across_identical_projects(
    repository: SQLiteRepository,
    brief,
) -> None:
    first = _install_complete_project(repository, brief)
    second = _install_complete_project(repository, brief)

    first_head = repository.get_stage_head(first.id, StageName.STORYBOARD)
    second_head = repository.get_stage_head(second.id, StageName.STORYBOARD)
    assert first_head.entity_revision_id != second_head.entity_revision_id

    first_gates = repository.get_gate_evaluation(
        first_head.entity_revision_id, "storyboard.v2"  # type: ignore[arg-type]
    )
    second_gates = repository.get_gate_evaluation(
        second_head.entity_revision_id, "storyboard.v2"  # type: ignore[arg-type]
    )
    assert {result.gate_id for result in first_gates.results} == {
        result.gate_id for result in second_gates.results
    }
    assert {result.id for result in first_gates.results}.isdisjoint(
        result.id for result in second_gates.results
    )


def test_forged_gate_receipt_cannot_authorize_approval(
    repository: SQLiteRepository,
    brief,
) -> None:
    project = _install_complete_project(repository, brief)
    head = repository.get_stage_head(project.id, StageName.STORYBOARD)
    assert head.entity_revision_id is not None
    forged_hash = "f" * 64
    forged = GateEvaluation(
        gate_set_version="storyboard.v2",
        evaluated_input_hash=forged_hash,
        results=(
            GateResult(
                id="forged",
                gate_set_version="storyboard.v2",
                gate_id="forged.pass",
                evaluated_input_hash=forged_hash,
                required=True,
                status=GateStatus.PASS,
                severity=GateSeverity.INFO,
            ),
        ),
    )

    with pytest.raises(InvalidTransitionError, match="canonical evaluator receipt"):
        repository.record_gate_evaluation(
            project.id,
            head.entity_revision_id,
            forged,
        )

    with pytest.raises(InvalidTransitionError, match="current canonical storyboard gate set"):
        repository.decide_storyboard_approval(
            project.id,
            expected_revision=head.revision,
            expected_content_hash=head.content_hash or "",
            decision="approve",
            reviewer="attacker",
            gate_set_version="forged",
        )
