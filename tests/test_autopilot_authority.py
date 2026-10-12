"""Run admission, atomic authority and negative human/video boundaries."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing

import pytest

from plotloom.autopilot_contracts import CheckpointEvidence, OperationScope
from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.exceptions import InvalidTransitionError, RevisionConflictError
from plotloom.persistence.schema import ApprovalDecisionRow, AutopilotDecisionRow
from plotloom.project_storage import ProjectFolderStorage
from plotloom.project_storage.project_video import ProjectVideoRepository
from plotloom.source_outline_contracts import SourceMaterial
from plotloom.video_jobs import VideoJobService
from tests.autopilot_fixtures import authority, exact_source, policy_for, start_run


def storage_at(root):
    return ProjectFolderStorage(outputs_root=root / "outputs", application_data_root=root / "application")


def test_double_start_has_one_admitted_policy_and_run(tmp_path):
    storage = storage_at(tmp_path)
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    project = store.project()
    policy = policy_for(store)
    store.close()
    def start():
        with closing(storage.projects.open(project.id)) as owned:
            return owned.repository.autopilot.start(project.id, expected_brief_revision=project.revision, policy=policy)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first, second = list(pool.map(lambda _: start(), range(2)))
    assert first.id == second.id and first.policy == second.policy


def test_exact_source_and_checkpoint_commit_or_rollback_together(tmp_path):
    storage = storage_at(tmp_path)
    brief = FIXED_CHINESE_BRIEF.model_copy(update={"title": "  保留标题  ", "synopsis": "\n保留原始简报。 \n"})
    store = storage.projects.create(brief)
    run = start_run(store)
    with pytest.raises(RuntimeError, match="injected"):
        with store.repository.autopilot_command(authority(run)):
            state = store.save_source_material(expected_source_revision=0, material=exact_source(store))
            assert state.source.material.title == brief.title
            checkpoint = store.repository.autopilot.checkpoint("source", state="adopted",
                evidence=CheckpointEvidence(owner="source", subject_id="source", result={"revision": 1}))
            store.repository.autopilot.decide(checkpoint, subject={"revision": 1}, rationale="exact Brief source")
            raise RuntimeError("injected after adoption")
    assert store.source_outline_state().source is None
    assert store.repository.autopilot.current(store.manifest.project_id).checkpoints == []
    with store.repository.autopilot_command(authority(run)):
        state = store.save_source_material(expected_source_revision=0, material=exact_source(store))
        checkpoint = store.repository.autopilot.checkpoint("source", state="adopted",
            evidence=CheckpointEvidence(owner="source", subject_id="source", result={"revision": 1}))
        store.repository.autopilot.decide(checkpoint, subject={"revision": 1}, rationale="exact Brief source")
    project_id = store.manifest.project_id
    store.close()
    with closing(storage.projects.open(project_id)) as reopened:
        source = reopened.source_outline_state().source
        assert (source.material.title, source.material.text) == (brief.title, brief.synopsis)
        assert source.material.attribution is None and source.material.rights_declaration is None
        assert reopened.repository.autopilot.current(project_id).state == "running"
        with reopened.repository._read() as session:
            assert len(session.query(AutopilotDecisionRow).all()) == 1
            assert session.query(ApprovalDecisionRow).count() == 0


def test_brief_origin_cannot_be_claimed_by_manual_save(tmp_path):
    with closing(storage_at(tmp_path).projects.create(FIXED_CHINESE_BRIEF)) as store:
        with pytest.raises(InvalidTransitionError, match="trusted"):
            store.save_source_material(expected_source_revision=0, material=exact_source(store))
        assert store.source_outline_state().source is None


def test_manual_edit_takes_over_and_old_claim_cannot_overwrite(tmp_path):
    with closing(storage_at(tmp_path).projects.create(FIXED_CHINESE_BRIEF)) as store:
        run = start_run(store)
        # Takeover is explicit before changing upstream material while a run
        # still owns production admission.
        current = store.repository.autopilot.current(store.manifest.project_id)
        store.repository.autopilot.control(store.manifest.project_id, expected_revision=current.revision, action="takeover")
        store.save_source_material(expected_source_revision=0,
            material=SourceMaterial(kind="synopsis", title="作者修改", text="作者接管后的新来源。"))
        with pytest.raises(InvalidTransitionError):
            with store.repository.autopilot_command(authority(run)):
                pytest.fail("stale controller admitted")
        assert store.source_outline_state().source.material.title == "作者修改"


@pytest.mark.parametrize("scope", [OperationScope.SOURCE, OperationScope.TEXT, OperationScope.IMAGE, OperationScope.SELECT, OperationScope.EVIDENCE])
def test_machine_scope_cannot_create_human_review_or_touch_video_transport(tmp_path, scope):
    storage = storage_at(tmp_path)
    with closing(storage.projects.create(FIXED_CHINESE_BRIEF)) as store:
        run = start_run(store)
        repository = ProjectVideoRepository(store, storage.application)
        class NoTransport:
            def preflight(self):
                pytest.fail("pre-video command contacted video provider")
        class NoAdapter:
            def production_contract(self, **_values):
                pytest.fail("pre-video command compiled a video request")
        service = VideoJobService(repository, store.artifacts, NoTransport(), adapter=NoAdapter())
        with store.repository.autopilot_command(authority(run, scope)):
            with pytest.raises(InvalidTransitionError, match="pre-video"):
                service.submit(store.manifest.project_id, "unknown-video-job")
            with pytest.raises(InvalidTransitionError, match="pre-video"):
                service.prepare(store.manifest.project_id, approval_id="forged", shot_id="absent",
                    storyboard_revision=1, expected_selection_revision=0, idempotency_key="negative",
                    requested_seconds=None, resolution=None, audio=None, aspect_policy=None,
                    allow_letterbox=False, allow_center_crop=False, seed=None, profile_id=None, preview_only=True)
            with pytest.raises(InvalidTransitionError, match="human"):
                store.media.create_visual_intent(store.manifest.project_id, "missing-asset", {})
            with pytest.raises(InvalidTransitionError, match="human"):
                store.repository.production_bridge.update_intent_package(store.manifest.project_id, None)
            with pytest.raises(InvalidTransitionError, match="human"):
                store.repository.production_bridge.update_presentation(store.manifest.project_id, None)
            with pytest.raises(InvalidTransitionError, match="author-owned"):
                store.repository._drafts.update_project(store.manifest.project_id, 1, FIXED_CHINESE_BRIEF)
        with store.repository.engine.connect() as connection:
            assert connection.exec_driver_sql("SELECT count(*) FROM v2_video_jobs").scalar() == 0
            assert connection.exec_driver_sql("SELECT count(*) FROM v2_approval_decisions").scalar() == 0


def test_human_video_requires_current_bundle_even_without_machine_context(tmp_path):
    storage = storage_at(tmp_path)
    with closing(storage.projects.create(FIXED_CHINESE_BRIEF)) as store:
        start_run(store)
        repository = ProjectVideoRepository(store, storage.application)
        with pytest.raises(InvalidTransitionError, match="human material handoff"):
            repository.claim_video_dispatch(store.manifest.project_id, "missing-video")


def test_manual_work_is_not_a_fresh_autopilot_project(tmp_path):
    with closing(storage_at(tmp_path).projects.create(FIXED_CHINESE_BRIEF)) as store:
        store.save_source_material(expected_source_revision=0,
            material=SourceMaterial(kind="synopsis", title="已有来源", text="保留已有工作。"))
        with pytest.raises(InvalidTransitionError, match="Brief-only"):
            start_run(store)


def prepared_outline(store, run):
    from tests.source_outline_fixtures import _request
    from plotloom.creative_handoff_exchange import request_hash
    with store.repository.autopilot_command(authority(run)):
        source = exact_source(store)
        store.save_source_material(expected_source_revision=0, material=source)
    with store.repository.autopilot_command(authority(run, OperationScope.TEXT)):
        request = _request(store.manifest.project_id, source)
        store.prepare_outline_candidate(request)
        evidence = CheckpointEvidence(owner="outline", subject_id=request.job_id, job_id=request.job_id,
            request_hash=request_hash(request), execution_pin=store.creative_handoff_execution_pin(request))
        store.repository.autopilot.checkpoint("outline", state="prepared", evidence=evidence)
    return evidence


def test_checkpoint_cas_never_erases_uncertain_dispatch_or_delivery(tmp_path):
    with closing(storage_at(tmp_path).projects.create(FIXED_CHINESE_BRIEF)) as store:
        run = start_run(store)
        evidence = prepared_outline(store, run)
        with store.repository.autopilot_command(authority(run, OperationScope.EVIDENCE)):
            store.repository.autopilot.checkpoint("outline", state="sent", evidence=evidence, expected_revision=1)
            store.repository.autopilot.checkpoint("outline", state="outcome_unknown", evidence=evidence, expected_revision=2)
        for state, revision, exception in [("prepared", 3, InvalidTransitionError), ("sent", 1, RevisionConflictError), ("delivered", 3, InvalidTransitionError)]:
            with pytest.raises(exception):
                with store.repository.autopilot_command(authority(run, OperationScope.EVIDENCE)):
                    store.repository.autopilot.checkpoint("outline", state=state, evidence=evidence, expected_revision=revision)
        assert store.repository.autopilot.current(store.manifest.project_id).checkpoints[0]["state"] == "outcome_unknown"


def test_checkpoint_cannot_claim_missing_native_owner_and_open_checks_retained_binding(tmp_path):
    from plotloom.project_storage import ProjectStorageCorruptionError
    import json
    storage = storage_at(tmp_path)
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    run = start_run(store)
    evidence = prepared_outline(store, run)
    with pytest.raises(InvalidTransitionError, match="native owner"):
        with store.repository.autopilot_command(authority(run, OperationScope.TEXT)):
            store.repository.autopilot.checkpoint("nonexistent", state="prepared",
                evidence=evidence.model_copy(update={"job_id": "missing", "subject_id": "missing"}))
    project_id = store.manifest.project_id
    with store.repository.engine.begin() as connection:
        altered = evidence.model_copy(update={"request_hash": "0" * 64}).model_dump(mode="json", by_alias=True)
        connection.exec_driver_sql("UPDATE v2_autopilot_checkpoints SET evidence=?", (json.dumps(altered),))
    store.close()
    with pytest.raises(ProjectStorageCorruptionError, match="autopilot"):
        storage.projects.open(project_id)


def test_receipt_only_outline_ingestion_is_atomic_without_material_adoption(tmp_path):
    from tests.source_outline_fixtures import _deliver
    with closing(storage_at(tmp_path).projects.create(FIXED_CHINESE_BRIEF)) as store:
        run = start_run(store)
        evidence = prepared_outline(store, run)
        request = store.outline_candidate_request(evidence.job_id)
        delivery = _deliver(store, request)
        with store.repository.autopilot_command(authority(run, OperationScope.EVIDENCE)):
            store.admit_outline_delivery(delivery)
            store.repository.autopilot.checkpoint("outline", state="delivered", expected_revision=1,
                evidence=evidence.model_copy(update={"delivery_hash": delivery.manifest_hash}))
        assert store.source_outline_state().candidate.status == "ready"
        assert store.source_outline_state().accepted_outline is None
        assert store.repository.autopilot.current(store.manifest.project_id).state == "running"


@pytest.mark.parametrize("mutation", ["text", "origin"])
def test_retained_source_exact_frozen_brief_binding_is_verified_on_open(tmp_path, mutation):
    import json
    from plotloom.persistence.codec import stable_hash
    from plotloom.project_storage import ProjectStorageCorruptionError
    storage = storage_at(tmp_path)
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    run = start_run(store)
    with store.repository.autopilot_command(authority(run)):
        store.save_source_material(expected_source_revision=0, material=exact_source(store))
        store.repository.autopilot.checkpoint("source", state="adopted",
            evidence=CheckpointEvidence(owner="source", subject_id="source", result={"revision": 1}))
    with store.repository.engine.begin() as connection:
        material = json.loads(connection.exec_driver_sql("SELECT material FROM v2_source_outline_source_revisions").scalar())
        if mutation == "text":
            material["text"] = "foreign altered source"
        else:
            material["briefOrigin"] = {"origin": "forged"}
        connection.exec_driver_sql("UPDATE v2_source_outline_source_revisions SET material=?,content_hash=?", (json.dumps(material), stable_hash(material)))
    project_id = store.manifest.project_id
    store.close()
    with pytest.raises(ProjectStorageCorruptionError, match="autopilot"):
        storage.projects.open(project_id)
