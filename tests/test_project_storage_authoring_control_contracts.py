"""Current project-folder authoring/control contracts.

These cases intentionally retain the failure boundaries from the retired
shared-runtime tests.  They use only the manifest-bound store and its public
routes, so a passing happy-path replacement cannot hide a lost CAS, stale-head,
or approval guard.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from plotloom.api import create_project_folder_authoring_app
from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.domain import STAGE_ORDER, StageName
from plotloom.project_storage import ProjectFolderStorage

from tests.backend_core.conftest import all_stage_payloads


def _client(tmp_path: Path) -> TestClient:
    storage = ProjectFolderStorage(
        outputs_root=tmp_path / "outputs",
        application_data_root=tmp_path / "application",
    )
    return TestClient(create_project_folder_authoring_app(storage))


def _complete_project(client: TestClient) -> dict:
    response = client.post(
        "/api/v2/projects",
        json={
            "brief": FIXED_CHINESE_BRIEF.model_dump(mode="json", by_alias=True),
            "initialStages": [
                {"stage": stage.value, "payload": payload.model_dump(mode="json", by_alias=True)}
                for stage, payload in zip(STAGE_ORDER, all_stage_payloads(), strict=True)
            ],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.parametrize("save_with_draft", [False, True])
@pytest.mark.parametrize(
    ("change", "expected_statuses"),
    [
        ({"shotCountPolicy": "advisory"}, ["ready", "ready", "ready", "stale"]),
        ({"targetPlaythroughSeconds": 181}, ["ready", "ready", "stale", "stale"]),
        ({"nodeBudget": 10}, ["ready", "stale", "stale", "stale"]),
    ],
)
def test_brief_saves_invalidate_only_evidenced_stage_dependencies(
    tmp_path: Path, save_with_draft: bool, change: dict, expected_statuses: list[str],
) -> None:
    client = _client(tmp_path)
    project = _complete_project(client)
    project_id = project["id"]
    brief = {**project["brief"], **change}
    if save_with_draft:
        draft = client.put(
            f"/api/v2/projects/{project_id}/authoring-drafts",
            json={"editorScope": "brief", "entityId": "root", "baseCanonicalRevision": 1,
                  "expectedDraftRevision": 0, "payload": brief},
        )
        assert draft.status_code == 200, draft.text
    payload = {"expectedRevision": 1, "brief": brief}
    if save_with_draft:
        payload["consumedDraft"] = {"editorScope": "brief", "entityId": "root", "draftRevision": 1}
    saved = client.patch(f"/api/v2/projects/{project_id}", json=payload)
    assert saved.status_code == 200, saved.text
    stages = client.get(f"/api/v2/projects/{project_id}/stages").json()["stages"]
    assert [stage["head"]["status"] for stage in stages] == expected_statuses


def test_canonical_conflicts_stale_downstream_and_consume_only_the_exact_draft(
    tmp_path: Path,
) -> None:
    client = _client(tmp_path)
    project = _complete_project(client)
    project_id = project["id"]

    # A stale project/stage CAS must not overwrite canonical content.
    project_conflict = client.patch(
        f"/api/v2/projects/{project_id}",
        json={"expectedRevision": 99, "brief": project["brief"]},
    )
    assert project_conflict.status_code == 409
    assert client.get(f"/api/v2/projects/{project_id}").json()["brief"] == project["brief"]

    original_bible = project["stages"][0]
    stage_conflict = client.patch(
        f"/api/v2/projects/{project_id}/stages/story_bible",
        json={"expectedRevision": 0, "payload": original_bible["payload"]},
    )
    assert stage_conflict.status_code == 409
    unchanged = client.get(f"/api/v2/projects/{project_id}/stages").json()["stages"][0]
    assert unchanged["head"]["revision"] == 1
    assert unchanged["payload"] == original_bible["payload"]

    changed_bible = {**original_bible["payload"], "themes": ["新的上游主题"]}
    updated = client.patch(
        f"/api/v2/projects/{project_id}/stages/story_bible",
        json={"expectedRevision": 1, "payload": changed_bible},
    )
    assert updated.status_code == 200
    stages = client.get(f"/api/v2/projects/{project_id}/stages").json()["stages"]
    assert stages[0]["head"]["status"] == "ready"
    assert stages[0]["head"]["revision"] == 2
    assert [stage["head"]["status"] for stage in stages[1:]] == ["stale"] * 3

    duplicate = client.post(
        f"/api/v2/projects/{project_id}/duplicate",
        headers={"Idempotency-Key": "copy-ready-prefix-after-upstream-edit"},
        json={"expectedLifecycleRevision": 1, "title": "Ready prefix only"},
    )
    assert duplicate.status_code == 200
    assert duplicate.json()["copiedThrough"] == "story_bible"
    assert duplicate.json()["omittedStages"] == ["story_graph", "scene_beats", "storyboard"]
    assert [stage["head"]["status"] for stage in duplicate.json()["project"]["stages"]] == [
        "ready",
        "missing",
        "missing",
        "missing",
    ]

    draft_brief = {**project["brief"], "title": "Only the acknowledged draft may save"}
    saved = client.put(
        f"/api/v2/projects/{project_id}/authoring-drafts",
        json={
            "editorScope": "brief",
            "entityId": "root",
            "baseCanonicalRevision": 1,
            "expectedDraftRevision": 0,
            "payload": draft_brief,
        },
    )
    assert saved.status_code == 200

    wrong_payload = {**draft_brief, "title": "A matching draft revision is insufficient"}
    rejected_consumption = client.patch(
        f"/api/v2/projects/{project_id}",
        json={
            "expectedRevision": 1,
            "brief": wrong_payload,
            "consumedDraft": {"editorScope": "brief", "entityId": "root", "draftRevision": 1},
        },
    )
    assert rejected_consumption.status_code == 409
    assert client.get(f"/api/v2/projects/{project_id}/authoring-drafts").json()[0]["payload"] == draft_brief

    consumed = client.patch(
        f"/api/v2/projects/{project_id}",
        json={
            "expectedRevision": 1,
            "brief": draft_brief,
            "consumedDraft": {"editorScope": "brief", "entityId": "root", "draftRevision": 1},
        },
    )
    assert consumed.status_code == 200
    assert consumed.headers["X-Plotloom-Draft-Consumed-Revision"] == "1"
    assert client.get(f"/api/v2/projects/{project_id}/authoring-drafts").json() == []


def test_storyboard_approval_is_gate_bound_append_only_and_stales_with_its_inputs(
    tmp_path: Path,
) -> None:
    client = _client(tmp_path)
    project = _complete_project(client)
    project_id = project["id"]
    review = client.get(f"/api/v2/projects/{project_id}/storyboard-review")
    assert review.status_code == 200
    review_body = review.json()
    assert review_body["gateEvaluation"]["gateSetVersion"] == "storyboard.v2"
    assert review_body["gateEvaluation"]["results"]
    assert all(result["status"] == "pass" for result in review_body["gateEvaluation"]["results"])

    request = {
        "expectedRevision": review_body["head"]["revision"],
        "contentHash": review_body["head"]["contentHash"],
        "decision": "approve",
        "reviewer": "current storage fixture",
        "gateSetVersion": "storyboard.v2",
    }
    wrong_hash = client.post(
        f"/api/v2/projects/{project_id}/storyboard-approval",
        json={**request, "contentHash": "0" * 64},
    )
    assert wrong_hash.status_code == 409
    forged_gate_set = client.post(
        f"/api/v2/projects/{project_id}/storyboard-approval",
        json={**request, "gateSetVersion": "forged.v1"},
    )
    assert forged_gate_set.status_code == 409

    approved = client.post(f"/api/v2/projects/{project_id}/storyboard-approval", json=request)
    assert approved.status_code == 201
    assert approved.json()["active"] is True
    duplicate = client.post(f"/api/v2/projects/{project_id}/storyboard-approval", json=request)
    assert duplicate.status_code == 409

    revoked = client.post(
        f"/api/v2/projects/{project_id}/storyboard-approval",
        json={**request, "decision": "revoke", "note": "Recheck the authored cut."},
    )
    assert revoked.status_code == 201
    assert revoked.json()["active"] is False
    reapproved = client.post(f"/api/v2/projects/{project_id}/storyboard-approval", json=request)
    assert reapproved.status_code == 201
    assert reapproved.json()["active"] is True

    bible = project["stages"][0]["payload"]
    changed = client.patch(
        f"/api/v2/projects/{project_id}/stages/{StageName.STORY_BIBLE.value}",
        json={"expectedRevision": 1, "payload": {**bible, "themes": ["changed upstream"]}},
    )
    assert changed.status_code == 200
    stale = client.get(f"/api/v2/projects/{project_id}/storyboard-review").json()
    assert stale["head"]["status"] == "stale"
    assert stale["activeApproval"] is None
    assert any("upstream story_bible revision changed" in reason for reason in stale["decisions"][-1]["staleReasons"])
    assert client.post(f"/api/v2/projects/{project_id}/storyboard-approval", json=request).status_code == 409


def test_gate_result_identity_is_scoped_to_the_project_revision(tmp_path: Path) -> None:
    storage = ProjectFolderStorage(
        outputs_root=tmp_path / "outputs",
        application_data_root=tmp_path / "application",
    )
    first = storage.projects.create(FIXED_CHINESE_BRIEF)
    second = storage.projects.create(
        FIXED_CHINESE_BRIEF.model_copy(update={"title": "A second revision scope"})
    )
    try:
        for store in (first, second):
            for stage, payload in zip(STAGE_ORDER, all_stage_payloads(), strict=True):
                store.update_stage(
                    stage,
                    payload.model_dump(mode="json", by_alias=True),
                    expected_revision=0,
                )
        first_head = first.authoring.get_stage_head(first.project().id, StageName.STORYBOARD)
        second_head = second.authoring.get_stage_head(second.project().id, StageName.STORYBOARD)
        assert first_head.entity_revision_id is not None
        assert second_head.entity_revision_id is not None
        first_gates = first.authoring.get_gate_evaluation(
            first_head.entity_revision_id, "storyboard.v2"
        )
        second_gates = second.authoring.get_gate_evaluation(
            second_head.entity_revision_id, "storyboard.v2"
        )
        assert {item.gate_id for item in first_gates.results} == {
            item.gate_id for item in second_gates.results
        }
        assert {item.id for item in first_gates.results}.isdisjoint(
            item.id for item in second_gates.results
        )
    finally:
        first.close()
        second.close()
