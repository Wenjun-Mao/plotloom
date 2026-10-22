"""Exact native material authority and truthful atomic UI handoff."""
from contextlib import closing
from dataclasses import asdict, replace
import shutil

import pytest
from fastapi.testclient import TestClient

from plotloom import delegated_qa
from plotloom.api import create_project_folder_authoring_app
from plotloom.delegated_qa import NativeMaterialQaScope, QaMaterial, QaReference
from plotloom.domain import StageName
from plotloom.exceptions import InvalidTransitionError
from plotloom.project_storage.delegated_qa_grants import bind_original_qa_scope
from plotloom.project_storage.project_handle import ProjectStore
from tests.autopilot_handoff_seed_fixtures import copy_awaiting_handoff_seed
from tests.test_bulk_material_handoff import bulk_observation


def test_creator_completion_grant_freezes_only_the_actual_native_successor_materials():
    from plotloom.persistence.codec import stable_hash
    scope = delegated_qa.project_scope("6e70451f-e9fd-4460-a475-bce50fde6503")
    assert isinstance(scope, NativeMaterialQaScope)
    assert scope.id == "creator-completion-native-20261022"
    # Digest independently pins every exact reference/frame/original, run,
    # review bundle, closure, board, profile and prospective budget field.
    assert stable_hash(asdict(scope)) == "aec7a5acc8ed3ea81eca3a3e3a01a321a51d9ea29332452aa19c00b96a6ab1a1"
    assert scope.max_submissions is None and scope.max_requested_seconds is None
    assert len(scope.references) == 3 and len(scope.materials) == 2


def native_environment(seed, tmp_path, monkeypatch):
    from plotloom.persistence.project.autopilot_handoff import review_material
    storage, view, _ = copy_awaiting_handoff_seed(seed, tmp_path / "native-qa")
    with closing(storage.projects.open(view.project_id)) as store:
        review = review_material(store)
        bundle = review["bundle"]
        scope = NativeMaterialQaScope(id="synthetic-native-material-qa", project_id=view.project_id,
            storyboard_hash=store.authoring.get_stage_head(view.project_id, StageName.STORYBOARD).content_hash,
            materials=tuple(QaMaterial(frame["shotId"], frame["assetId"], frame["originalHash"]) for frame in bundle["frames"]),
            profile_id="minimax_h3_quality8_portrait_576x1024_v2", run_id=bundle["runId"],
            bundle_hash=review["bundleHash"], material_closure=bundle["materialClosure"],
            references=tuple(QaReference(item["owner"], item["subjectId"], item["decisionId"],
                tuple((asset["assetId"], asset["originalHash"]) for asset in item["assets"])) for item in bundle["references"]))
        monkeypatch.setattr(delegated_qa, "SCOPES", (scope,))
        bind_original_qa_scope(store, storage.application)
    client = TestClient(create_project_folder_authoring_app(storage))
    actor = {"kind": "agent_operated_qa", "scopeId": scope.id}
    return storage, client, view.project_id, review, scope, actor


def test_native_bundle_qa_handoff_is_atomic_attributed_and_portable(tmp_path, monkeypatch, awaiting_handoff_seed):
    from plotloom.persistence.project.autopilot_authority import video_eligible
    from plotloom.project_storage.current_schema import assert_current_project_database
    storage, client, project, review, scope, actor = native_environment(awaiting_handoff_seed, tmp_path, monkeypatch)
    path = f"/api/v2/projects/{project}"
    from plotloom.persistence.codec import stable_hash
    with closing(storage.projects.open(project)) as store:
        automatic = store.repository.autopilot.current(project)
        assert automatic.bundle["version"] == "pre-video.material.v1"
        assert stable_hash(automatic.bundle) == automatic.bundle_hash
        assert review["bundle"]["version"] == "pre-video.human-review.v2"
        assert stable_hash(review["bundle"]) == review["bundleHash"] != automatic.bundle_hash
        with pytest.raises(InvalidTransitionError, match="exact native material bundle"):
            delegated_qa.require_native_bundle(scope, review["bundle"], automatic.bundle_hash)
    wrong = bulk_observation(review) | {"attribution": actor, "bundleHash": automatic.bundle_hash}
    assert client.post(path + "/autopilot/handoff", json=wrong).status_code == 409
    assert client.get(path + "/qa-context").json() == {"eligible": True, "attribution": actor, "required": True, "reason": None}
    assert client.post(path + "/autopilot/handoff", json=bulk_observation(review)).status_code == 409
    body = bulk_observation(review) | {"attribution": actor}
    response = client.post(path + "/autopilot/handoff", json=body)
    assert response.status_code == 200, response.text
    assert response.json()["handoffAttribution"] == actor
    with closing(storage.projects.open(project)) as store:
        with store.repository._read() as session:
            assert video_eligible(session, project)
            raw = session.connection().exec_driver_sql("SELECT receipt FROM v2_autopilot_handoffs").scalar()
            import json
            receipt = json.loads(raw)
            assert receipt["version"] == "pre-video.handoff.v4" and receipt["attribution"] == actor
            assert receipt["observation"]["attribution"] == actor
            assert all(json.loads(row[0])["attribution"] == actor for row in session.connection().exec_driver_sql("SELECT intent FROM v2_visual_intents"))
            assert all(row[0] == delegated_qa.REVIEWER_PREFIX + scope.id for row in session.connection().exec_driver_sql("SELECT reviewer FROM v2_same_person_reviews"))
        # A controller claim/revision is not material identity. QA remains valid
        # only while the exact handed-off material closure stays unchanged.
        from plotloom.project_storage.delegated_qa_grants import qa_command
        from plotloom.delegated_qa import require_qa_write
        with qa_command(store, storage.application, actor), store.repository._read() as session:
            assert require_qa_write(session, project, actor) == scope
        assert_current_project_database(store.database_path, project)
        copied = tmp_path / "copied-native-qa"
        shutil.copytree(store.home, copied)
        manifest = store.manifest
    with closing(ProjectStore(copied, manifest, create_schema=False)) as store:
        from plotloom.project_storage.delegated_qa_grants import browser_qa_context
        context = browser_qa_context(store, storage.application)
        assert not context["eligible"] and context["required"] and context["attribution"] is None and context["reason"]
        assert_current_project_database(store.database_path, project)


@pytest.mark.parametrize("handed_off", [False, True])
def test_native_context_refuses_changed_material_closure_even_with_same_board_and_originals(tmp_path, monkeypatch, awaiting_handoff_seed, handed_off):
    storage, client, project, review, _scope, actor = native_environment(awaiting_handoff_seed, tmp_path, monkeypatch)
    path = f"/api/v2/projects/{project}"
    if handed_off:
        response = client.post(path + "/autopilot/handoff", json=bulk_observation(review) | {"attribution": actor})
        assert response.status_code == 200, response.text
    with closing(storage.projects.open(project)) as store:
        with store.repository.manual_command() as session:
            row = store.repository._project_access.rows.project(session, project)
            row.brief = row.brief | {"title": "Changed after exact native QA grant"}
            row.revision += 1
        from plotloom.project_storage.delegated_qa_grants import browser_qa_context
        context = browser_qa_context(store, storage.application)
        assert context["required"] and not context["eligible"] and context["attribution"] is None


@pytest.mark.parametrize("change", ["run", "bundle", "closure", "reference", "frame"])
def test_native_bundle_source_grant_cannot_widen(tmp_path, monkeypatch, awaiting_handoff_seed, change):
    storage, client, project, review, scope, actor = native_environment(awaiting_handoff_seed, tmp_path, monkeypatch)
    changed = {"run": {"run_id": "other-run"}, "bundle": {"bundle_hash": "f" * 64},
        "closure": {"material_closure": "f" * 64}, "reference": {"references": ()}, "frame": {"materials": ()}}[change]
    monkeypatch.setattr(delegated_qa, "SCOPES", (replace(scope, **changed),))
    with closing(storage.projects.open(project)) as store, pytest.raises(InvalidTransitionError):
        bind_original_qa_scope(store, storage.application)
    response = client.post(f"/api/v2/projects/{project}/autopilot/handoff", json=bulk_observation(review) | {"attribution": actor})
    assert response.status_code == 409, response.text
    with closing(storage.projects.open(project)) as store, store.repository._read() as session:
        assert session.connection().exec_driver_sql("SELECT count(*) FROM v2_autopilot_handoffs").scalar() == 0


def test_native_qa_missing_runtime_context_or_forged_actor_cannot_fall_back(tmp_path, monkeypatch, awaiting_handoff_seed):
    from plotloom.autopilot_handoff_contracts import BulkHumanHandoffRequest
    from plotloom.persistence.project.autopilot_handoff import record_handoff
    storage, client, project, review, _scope, actor = native_environment(awaiting_handoff_seed, tmp_path, monkeypatch)
    body = bulk_observation(review) | {"attribution": actor}
    with closing(storage.projects.open(project)) as store, pytest.raises(InvalidTransitionError, match="runtime incarnation"):
        record_handoff(store, BulkHumanHandoffRequest.model_validate(body))
    body["attribution"] = actor | {"scopeId": "forged"}
    assert client.post(f"/api/v2/projects/{project}/autopilot/handoff", json=body).status_code == 409
