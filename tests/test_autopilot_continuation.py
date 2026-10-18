"""Real partial material continuation retains immutable origin authority."""
import json
from contextlib import closing

import pytest

from plotloom.autopilot_contracts import ContinueRequest, RunControlRequest
from plotloom.autopilot_handoff_contracts import HumanHandoffRequest
from plotloom.exceptions import InvalidTransitionError, RevisionConflictError
from plotloom.persistence.project.autopilot_authority import video_eligible
from plotloom.persistence.project.autopilot_handoff import (
    record_handoff,
    review_material,
)
from plotloom.project_storage import ProjectStorageCorruptionError
from tests.autopilot_compact_text_fixtures import compact_safety_image_environment
from tests.autopilot_image_fixtures import run_pack
from tests.test_autopilot_handoff import observation
from tests.test_autopilot_image_safety import reach


def request_for(store, current, **changes):
    context = store.repository.autopilot.continuation_context(current.project_id)
    return ContinueRequest(expected_brief_revision=store.project().revision,
        expected_run_id=context["runId"], expected_run_revision=context["runRevision"], expected_material_closure=context["materialClosure"],
        style_authority=current.policy.effective_style_authority, render_style=current.policy.render_style,
        art_render_style=current.policy.art_render_style, max_images=current.policy.max_images,
        max_jobs=current.policy.max_jobs, **changes)


def origin_rows(store, run_id):
    with store.repository.engine.connect() as connection:
        return {table: connection.exec_driver_sql(f"SELECT * FROM {table} WHERE run_id=? ORDER BY id", (run_id,)).all()
            for table in ("v2_autopilot_checkpoints", "v2_autopilot_exec_attempts", "v2_autopilot_decisions", "v2_autopilot_frames")}


def test_partial_pack_continues_missing_only_and_handoff_keeps_frame_origins(tmp_path, monkeypatch, compact_two_cut_text_prefix):
    storage, _registry, service, view, image_calls, text_calls = compact_safety_image_environment(tmp_path, monkeypatch, compact_two_cut_text_prefix)
    try:
        partial, _checkpoint = reach(storage, service, view, "image", "adopted")
        stopped = service.control(view.project_id, RunControlRequest(expected_revision=partial.revision, action="cancel"))
        assert stopped.frames and stopped.state == "cancelled"
        with closing(storage.projects.open(view.project_id)) as store:
            before = origin_rows(store, view.id)
            policy_before = store.repository.autopilot.current(view.project_id).policy
            request = request_for(store, stopped)
            assert store.repository.autopilot.continuation_context(view.project_id)["eligible"]
        # A changed source/profile may grant future work without rebasing history.
        from plotloom.creative_handoff_exchange import CreativeHandoffExchange
        from tests.autopilot_controller_fixtures import PIN, UPSTREAM_PIN
        monkeypatch.setattr(CreativeHandoffExchange, "current_execution_pin", lambda _self, stage:
            (PIN if stage.startswith("bridge-") else UPSTREAM_PIN) | {"upstreamRevision": "b" * 40})
        child = service.continue_material(view.project_id, request)
        assert child.id != view.id and child.predecessor_run_id == view.id
        assert child.policy.code_revision != policy_before.code_revision
        old_images = list(image_calls)
        complete = run_pack(storage, service, child)
        assert complete.state == "awaiting_review" and len(complete.frames) == 6
        assert len(image_calls) == 8 and len(set(image_calls)) == 8 and not text_calls
        assert image_calls[:len(old_images)] == old_images
        assert all(frame in complete.frames for frame in stopped.frames)
        with closing(storage.projects.open(view.project_id)) as store:
            assert origin_rows(store, view.id) == before
            with store.repository.engine.connect() as connection:
                assert json.loads(connection.exec_driver_sql("SELECT policy FROM v2_autopilot_runs WHERE id=?", (view.id,)).scalar()) == policy_before.model_dump(mode="json", by_alias=True)
            handoff = record_handoff(store, HumanHandoffRequest.model_validate(observation(review_material(store))))
            assert handoff.state == "handed_off"
            with store.repository._read() as session:
                assert video_eligible(session, view.project_id)
        with closing(storage.projects.open(view.project_id)):
            pass
    finally:
        service.close()


def test_unknown_original_job_blocks_continue_without_new_dispatch(tmp_path, monkeypatch, compact_two_cut_text_prefix):
    storage, _registry, service, view, images, _text = compact_safety_image_environment(tmp_path, monkeypatch, compact_two_cut_text_prefix, auto_deliver=False)
    try:
        sent, checkpoint = reach(storage, service, view, "character-reference", "sent")
        stopped = service.control(view.project_id, RunControlRequest(expected_revision=sent.revision, action="cancel"))
        original_images = list(images)
        with closing(storage.projects.open(view.project_id)) as store:
            preview = store.repository.autopilot.continuation_context(view.project_id)
            assert not preview["eligible"] and checkpoint["evidence"]["jobId"] in " ".join(preview["blockers"])
            before = origin_rows(store, view.id)
            request = request_for(store, stopped)
            with pytest.raises(InvalidTransitionError, match="不会重复发送"):
                store.repository.autopilot.continue_material(view.project_id, request=request, policy=stopped.policy)
            assert origin_rows(store, view.id) == before and images == original_images
    finally:
        service.close()


@pytest.mark.parametrize("defect", ["evidence_hash", "origin", "frame"])
def test_inherited_provenance_cannot_be_rebound(tmp_path, awaiting_handoff_seed, defect):
    from tests.autopilot_handoff_seed_fixtures import copy_awaiting_handoff_seed
    storage, view, _calls = copy_awaiting_handoff_seed(awaiting_handoff_seed, tmp_path / "inheritance")
    with closing(storage.projects.open(view.project_id)) as store:
        stopped = store.repository.autopilot.control(view.project_id, expected_revision=view.revision, action="cancel")
        request = request_for(store, stopped)
        child = store.repository.autopilot.continue_material(view.project_id, request=request, policy=stopped.policy)
        with store.repository.engine.begin() as connection:
            if defect == "evidence_hash":
                connection.exec_driver_sql("UPDATE v2_autopilot_inheritance SET evidence_hash=? WHERE run_id=?", ("0" * 64, child.id))
            elif defect == "origin":
                connection.exec_driver_sql("UPDATE v2_autopilot_inheritance SET origin_checkpoint_id=(SELECT id FROM v2_autopilot_checkpoints WHERE run_id=? AND operation_key='outline') WHERE run_id=? AND operation_key='characters'", (view.id, child.id))
            else:
                frame = child.frames[0].model_dump(mode="json", by_alias=True) | {"originalHash": "0" * 64}
                connection.exec_driver_sql("UPDATE v2_autopilot_frames SET frame=? WHERE run_id=? AND shot_id=?", (json.dumps(frame), child.id, frame["shotId"]))
    with pytest.raises(ProjectStorageCorruptionError):
        storage.projects.open(view.project_id)


def test_continuation_cas_and_lifetime_cap_are_transactional(tmp_path, awaiting_handoff_seed):
    from tests.autopilot_handoff_seed_fixtures import copy_awaiting_handoff_seed
    storage, view, _calls = copy_awaiting_handoff_seed(awaiting_handoff_seed, tmp_path / "cas")
    with closing(storage.projects.open(view.project_id)) as store:
        stopped = store.repository.autopilot.control(view.project_id, expected_revision=view.revision, action="cancel")
        request = request_for(store, stopped)
        for changed, policy, error in (
            (request.model_copy(update={"expected_run_revision": 1}), stopped.policy, RevisionConflictError),
            (request.model_copy(update={"expected_material_closure": "0" * 64}), stopped.policy, InvalidTransitionError),
            (request, stopped.policy.model_copy(update={"max_images": 1}), InvalidTransitionError),
        ):
            with pytest.raises(error):
                store.repository.autopilot.continue_material(view.project_id, request=changed, policy=policy)
        assert store.repository.autopilot.current(view.project_id).id == view.id


def test_original_continuation_consent_cannot_replay_against_same_revision_descendant(tmp_path):
    from pydantic import ValidationError

    from plotloom.conformance import FIXED_CHINESE_BRIEF
    from tests.autopilot_fixtures import policy_for
    from tests.test_autopilot_recovery import storage_at
    storage = storage_at(tmp_path)
    with closing(storage.projects.create(FIXED_CHINESE_BRIEF)) as store:
        project_id = store.manifest.project_id
        policy = policy_for(store)
        original = store.repository.autopilot.start(project_id, expected_brief_revision=1, policy=policy)
        stopped = store.repository.autopilot.control(project_id, expected_revision=original.revision, action="cancel")
        consent = request_for(store, stopped)
        child = store.repository.autopilot.continue_material(project_id, request=consent, policy=policy)
        stopped_child = store.repository.autopilot.control(project_id, expected_revision=child.revision, action="cancel")
        fresh = store.repository.autopilot.continuation_context(project_id)
        assert stopped_child.revision == consent.expected_run_revision
        assert fresh["materialClosure"] == consent.expected_material_closure
        with pytest.raises(InvalidTransitionError, match="身份已变化"):
            store.repository.autopilot.continue_material(project_id, request=consent, policy=policy)
        with store.repository.engine.connect() as connection:
            assert connection.exec_driver_sql("SELECT COUNT(*) FROM v2_autopilot_runs").scalar_one() == 2
        without_identity = consent.model_dump(mode="json", by_alias=True)
        without_identity.pop("expectedRunId")
        with pytest.raises(ValidationError):
            ContinueRequest.model_validate(without_identity)


@pytest.mark.parametrize("clock", ["equal", "rollback"])
def test_lineage_leaf_and_original_frame_owner_survive_equal_or_backward_clocks(tmp_path, monkeypatch, awaiting_handoff_seed, clock):
    from datetime import timedelta

    from plotloom.autopilot_contracts import CommandAuthority, OperationScope
    from plotloom.autopilot_image_selection import publish_bundle
    from plotloom.autopilot_materials import initial_inventory
    from tests.autopilot_handoff_seed_fixtures import copy_awaiting_handoff_seed
    storage, original, _calls = copy_awaiting_handoff_seed(awaiting_handoff_seed, tmp_path / clock)
    with closing(storage.projects.open(original.project_id)) as store:
        stopped = store.repository.autopilot.control(original.project_id, expected_revision=original.revision, action="cancel")
        parent = stopped
        for depth in (1, 2):
            consent = request_for(store, parent)
            timestamp = original.created_at if clock == "equal" else original.created_at - timedelta(days=depth)
            monkeypatch.setattr("plotloom.persistence.project.autopilot_continuation.utc_now", lambda value=timestamp: value)
            child = store.repository.autopilot.continue_material(original.project_id, request=consent, policy=original.policy)
            assert store.repository.autopilot.current(original.project_id).id == child.id
            assert child.frames == original.frames
            if depth == 1:
                parent = store.repository.autopilot.control(original.project_id, expected_revision=child.revision, action="cancel")
        claimed = store.repository.autopilot.claim(original.project_id, "clock-fixture")
        with store.repository.autopilot_command(CommandAuthority(claimed.id, "clock-fixture", OperationScope.SELECT)):
            publish_bundle(store, claimed, initial_inventory(store, claimed.policy))
        review = review_material(store)
        assert review["runRevision"] == store.repository.autopilot.current(original.project_id).revision
        handoff = record_handoff(store, HumanHandoffRequest.model_validate(observation(review)))
        assert handoff.id == child.id and handoff.state == "handed_off"
        with store.repository._read() as session:
            assert video_eligible(session, original.project_id)
    with closing(storage.projects.open(original.project_id)) as reopened:
        assert reopened.repository.autopilot.current(original.project_id).id == child.id


@pytest.mark.parametrize("links", [
    [("a", None), ("b", None)], [("a", "b"), ("b", "a")],
    [("a", None), ("b", "missing")], [("a", None), ("b", "a"), ("c", "a")],
])
def test_current_run_rejects_ambiguous_or_disconnected_lineage(links):
    from plotloom.persistence.project.autopilot_lineage import current_run_id
    with pytest.raises(ValueError):
        current_run_id(links)
