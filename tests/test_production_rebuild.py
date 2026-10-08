"""One current installation, exact rebuild CAS and transactional recovery."""
from contextlib import closing
from copy import deepcopy

import pytest
from sqlalchemy import select

from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.domain import StageName
from plotloom.exceptions import InvalidTransitionError
from plotloom.persistence.schema import EntityRevisionRow, ProductionBridgeAdmissionRow
from plotloom.persistence.schema.project_source_outline import SourceGraphIdentityRow
from plotloom.production_bridge_contracts import (
    ProductionBridgeAcceptRequest,
    ProductionBridgeIntentUpdateRequest,
)
from plotloom.project_storage import ProjectFolderStorage
from tests.test_production_bridge import (
    _prepare_installable_bridge,
    _review_fixture_presentation,
)


def _accept(store, proposal):
    return store.accept_production_bridge(ProductionBridgeAcceptRequest(
        expected_proposal_revision=proposal.revision, expected_content_hash=proposal.content_hash,
    ))


def _review(store, proposal):
    target = proposal.replacement_target
    proposal = _review_fixture_presentation(store, proposal)
    assert proposal.replacement_target == target
    saved = store.update_production_bridge_intent_package(ProductionBridgeIntentUpdateRequest(
        expected_proposal_revision=proposal.revision, expected_content_hash=proposal.content_hash,
        entries=[{"id": entry.id, "text": "New author purpose " + entry.id} for entry in proposal.intent_package.entries],
    )).proposal
    assert saved.replacement_target == target
    return saved


def _store(tmp_path):
    storage = ProjectFolderStorage(outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application")
    return storage, storage.projects.create(FIXED_CHINESE_BRIEF.model_copy(update={"shot_count_policy": "advisory"}))


def _heads(store):
    return {stage.value: store.authoring.get_stage_head(store.manifest.project_id, stage).model_dump(mode="json") for stage in StageName}


def test_prepare_preserves_own_installed_authority_and_requires_fresh_reviews(tmp_path):
    storage, store = _store(tmp_path)
    with closing(store):
        installed = _accept(store, _prepare_installable_bridge(store))
        original = installed.installation
        board_head = store.authoring.get_stage_head(store.manifest.project_id, StageName.STORYBOARD)
        approval = store.repository._approvals.decide_storyboard_approval(
            store.manifest.project_id, expected_revision=board_head.revision,
            expected_content_hash=board_head.content_hash, decision="approve",
            reviewer="rebuild fixture", gate_set_version="storyboard.v2",
        )
        prepared = store.prepare_production_bridge(installed.preparation.request)
        assert prepared.status == "ready"
        assert prepared.installation == original
        assert prepared.installation.status == "current"
        assert prepared.installation.runtime_choice == original.runtime_choice
        assert prepared.proposal.replacement_target.installed_admission_id == original.admission_id
        assert prepared.proposal.intent_package.review_state == "pending"
        assert not prepared.proposal.presentation.reviewed
        with pytest.raises(InvalidTransitionError, match="not installable"):
            _accept(store, prepared.proposal)
        accepted = _accept(store, _review(store, prepared.proposal))
        assert accepted.installation.admission_id != original.admission_id
        assert accepted.installation.status == "current"
        assert accepted.installation.installed_stage_revisions["storyboard"] == 2
        assert not store.repository._approvals.get_approval_closure(approval.id).active
        assert store.repository._approvals.list_approval_decisions(project_id=store.manifest.project_id) == [approval]
        project_id = store.manifest.project_id
    with closing(storage.projects.open(project_id)) as reopened:
        assert reopened.production_bridge_state().installation == accepted.installation


def test_populated_late_failure_rolls_back_revisions_admissions_and_installed_authority(tmp_path, monkeypatch):
    _, store = _store(tmp_path)
    with closing(store):
        installed = _accept(store, _prepare_installable_bridge(store))
        fresh = store.prepare_production_bridge(installed.preparation.request)
        proposal = _review(store, fresh.proposal)
        heads = _heads(store)
        with store.repository._read() as session:
            counts = [len(session.scalars(select(owner)).all()) for owner in (EntityRevisionRow, ProductionBridgeAdmissionRow, SourceGraphIdentityRow)]
        canonical = store.repository.production_bridge._canonical
        install = canonical._install_stage_in_session

        def reject_board(*args, **kwargs):
            if args[2] == StageName.STORYBOARD:
                raise RuntimeError("late storyboard failure")
            return install(*args, **kwargs)

        monkeypatch.setattr(canonical, "_install_stage_in_session", reject_board)
        with pytest.raises(RuntimeError, match="late storyboard"):
            _accept(store, proposal)
        assert _heads(store) == heads
        assert store.production_bridge_state().installation == installed.installation
        with store.repository._read() as session:
            assert counts == [len(session.scalars(select(owner)).all()) for owner in (EntityRevisionRow, ProductionBridgeAdmissionRow, SourceGraphIdentityRow)]


def test_stale_prepare_request_and_concurrent_canonical_target_refuse_without_writes(tmp_path):
    _, store = _store(tmp_path)
    with closing(store):
        installed = _accept(store, _prepare_installable_bridge(store))
        frozen = installed.preparation.request
        fresh = store.prepare_production_bridge(frozen)
        with pytest.raises(InvalidTransitionError, match="target changed"):
            store.prepare_production_bridge(frozen)
        proposal = _review(store, fresh.proposal)
        board = store.authoring.get_stage_payload(store.manifest.project_id, StageName.STORYBOARD)
        store.authoring.update_stage(store.manifest.project_id, StageName.STORYBOARD, 1, board)
        # A real new canonical revision is required; allow-noop public writes
        # intentionally retain identical content, so install a distinct title.
        board_data = board.model_dump(mode="json", by_alias=True)
        board_data["shots"][0]["title"] += " changed"
        store.authoring.update_stage(store.manifest.project_id, StageName.STORYBOARD, 1, board_data)
        before = _heads(store)
        with pytest.raises(InvalidTransitionError, match="target changed"):
            _accept(store, proposal)
        assert _heads(store) == before


def test_same_hash_unowned_graph_cannot_borrow_authored_identity(tmp_path):
    _, store = _store(tmp_path)
    with closing(store):
        _prepare_installable_bridge(store)
        graph = store.authoring.get_stage_payload(store.manifest.project_id, StageName.STORY_GRAPH)
        with store.repository._lifecycle_write() as session:
            project = store.repository._project_row(session, store.manifest.project_id)
            from plotloom.domain import utc_now
            store.repository.production_bridge._canonical.install_source_map_graph_in_session(
                session, project, graph, expected_revision=1, now=utc_now(),
            )
        assert store.cast_state().status == "stale"
        assert store.production_bridge_state().preparation.status == "unavailable"


def test_new_proposal_cannot_restore_outdated_installation_or_borrow_its_choices(tmp_path):
    _, store = _store(tmp_path)
    with closing(store):
        installed = _accept(store, _prepare_installable_bridge(store))
        board = store.authoring.get_stage_payload(store.manifest.project_id, StageName.STORYBOARD).model_dump(mode="json", by_alias=True)
        board["shots"][0]["title"] += " revised"
        store.authoring.update_stage(store.manifest.project_id, StageName.STORYBOARD, 1, board)
        outdated = store.production_bridge_state()
        assert outdated.installation.status == "outdated"
        assert outdated.installation.runtime_choice == installed.installation.runtime_choice
        prepared = store.prepare_production_bridge(outdated.preparation.request)
        assert prepared.installation == outdated.installation
        assert prepared.status == "ready"
        assert prepared.installation.inputs == outdated.installation.inputs


def _effects_mapping(store):
    from plotloom.source_outline_contracts import SectionMap
    from tests.source_graph_fixtures import letter_section_map
    data = letter_section_map(store.manifest.project_id, store.project().brief).model_dump(mode="json", by_alias=True)
    edge = next(item for item in data["topology"]["edges"] if item["targetNodeId"] == "ending-a")
    edge["entityStateEffects"] = [{"entityType": "location", "entityId": "S01", "state": "dawn"}]
    return SectionMap.model_validate(data)


def _effects_store(tmp_path):
    from plotloom.canonical_schema import StoryBibleV2
    from tests.backend_core.conftest import make_story_bible
    _, store = _store(tmp_path)
    project = store.project()
    store.update_brief(project.brief.model_copy(update={"decision_points_per_path": 1, "ending_count": 2, "desired_join_count": 0}), expected_revision=project.revision)
    data = make_story_bible().model_dump(mode="json", by_alias=True)
    data["locations"] = [{"id": "S01", "name": "Beacon", "description": "Room",
                          "visualAnchors": [], "soundAnchors": [], "allowedStates": ["dawn"], "continuityRules": []}]
    store.authoring.update_stage(store.manifest.project_id, StageName.STORY_BIBLE, 0, StoryBibleV2.model_validate(data))
    proposal = _prepare_installable_bridge(store, structure_factory=_effects_mapping)
    return store, proposal


@pytest.mark.parametrize("late_failure", [False, True])
def test_dependency_only_rebind_preserves_f2_f5_receipts_and_rolls_back_atomically(tmp_path, monkeypatch, late_failure):
    store, proposal = _effects_store(tmp_path)
    with closing(store):
        original_installation = _accept(store, proposal).installation
        prepared = store.prepare_production_bridge(store.production_bridge_state().preparation.request)
        proposal = _review(store, prepared.proposal)
        before_reviews = [reader().model_dump(mode="json") for reader in (store.cast_state, store.art_state, store.script_state, store.storyboard_review_state)]
        before_heads = _heads(store)
        with store.repository._read() as session:
            identities_before = len(session.scalars(select(SourceGraphIdentityRow)).all())
        if late_failure:
            canonical = store.repository.production_bridge._canonical
            install = canonical._install_stage_in_session

            def reject_board(*args, **kwargs):
                if args[2] == StageName.STORYBOARD:
                    raise RuntimeError("dependency bundle late failure")
                return install(*args, **kwargs)

            monkeypatch.setattr(canonical, "_install_stage_in_session", reject_board)
            with pytest.raises(RuntimeError, match="late failure"):
                _accept(store, proposal)
            assert _heads(store) == before_heads
            assert store.production_bridge_state().installation == original_installation
        else:
            accepted = _accept(store, proposal)
            assert accepted.installation.status == "current"
            assert accepted.installation.installed_stage_revisions["story_graph"] == 3
            assert store.cast_state().accepted_cast.binding.graph_revision == 1
        assert [reader().model_dump(mode="json") for reader in (store.cast_state, store.art_state, store.script_state, store.storyboard_review_state)] == before_reviews
        with store.repository._read() as session:
            assert len(session.scalars(select(SourceGraphIdentityRow)).all()) == identities_before + (0 if late_failure else 1)


def test_incompatible_proposed_bible_effects_refuse_without_any_bundle_writes(tmp_path):
    store, proposal = _effects_store(tmp_path)
    with closing(store):
        # Inject a source-owned proposed Bible change as a new exact proposal
        # fixture; acceptance must revalidate entity effects transactionally.
        from plotloom.persistence.schema import ProductionBridgeRevisionRow
        with store.repository._lifecycle_write() as session:
            row = session.scalar(select(ProductionBridgeRevisionRow).where(ProductionBridgeRevisionRow.project_id == store.manifest.project_id, ProductionBridgeRevisionRow.revision == proposal.revision))
            payload = deepcopy(row.proposal)
            payload["payload"]["bible"]["locations"][0]["allowedStates"] = ["night"]
            row.proposal = payload
            row.content_hash = store.repository.production_bridge._proposal_digest(row.inputs, payload, [])
            digest = row.content_hash
        before = _heads(store)
        with store.repository._read() as session:
            conflicts = store.repository.production_bridge._validate_payload(session, store.manifest.project_id, payload["payload"])
            assert len(conflicts) == 1
            assert conflicts[0].code == "canonical_validation"
        assert _heads(store) == before
        with pytest.raises(ValueError):
            store.accept_production_bridge(ProductionBridgeAcceptRequest(expected_proposal_revision=proposal.revision, expected_content_hash=digest))
        assert _heads(store) == before
        assert store.production_bridge_state().installation is None
        saved = store.update_production_bridge_intent_package(ProductionBridgeIntentUpdateRequest(
            expected_proposal_revision=proposal.revision, expected_content_hash=digest,
            entries=[{"id": entry.id, "text": entry.text} for entry in proposal.intent_package.entries],
        )).proposal
        assert not saved.installable
        assert any(item.code == "canonical_validation" for item in saved.conflicts)
        assert _heads(store) == before


@pytest.mark.parametrize("job_state", ["prepared", "dispatching", "submitted", "retrieve_needed", "outcome_unknown"])
def test_direct_video_job_blocks_preparation_and_acceptance_without_clearing_it(tmp_path, job_state):
    from plotloom.domain import utc_now
    from plotloom.persistence.schema import VideoJobRow
    _, store = _store(tmp_path)
    with closing(store):
        proposal = _prepare_installable_bridge(store)
        request = store.production_bridge_state().preparation.request
        with store.repository._lifecycle_write() as session:
            session.add(VideoJobRow(
                id="held-video", project_id=store.manifest.project_id, idempotency_key="held",
                request_hash="a" * 64, snapshot={}, snapshot_hash="b" * 64,
                requested_seconds=5, state=job_state, created_at=utc_now(), updated_at=utc_now(),
            ))
        before = _heads(store)
        with pytest.raises(InvalidTransitionError, match="unresolved"):
            store.prepare_production_bridge(request)
        assert store.production_bridge_state().preparation.status == "unavailable"
        with pytest.raises(InvalidTransitionError, match="unresolved"):
            _accept(store, proposal)
        assert _heads(store) == before
        with store.repository._read() as session:
            assert session.get(VideoJobRow, "held-video").state == job_state


def test_latest_only_timing_refuses_removed_and_reused_ids_and_retains_installation_during_prepare(tmp_path):
    from plotloom.persistence.project.media_video_source import VideoSourceTiming
    from plotloom.persistence.schema import ProductionBridgeRevisionRow
    _, store = _store(tmp_path)
    with closing(store):
        original = _accept(store, _prepare_installable_bridge(store))
        bridge = store.repository.production_bridge
        timing = VideoSourceTiming(bridge._access, bridge)
        cut = original.installation.cuts[0]
        shot_id = cut["shotId"]
        with store.repository._read() as session:
            first = timing.binding_in_session(session, store.manifest.project_id, shot_id, 3000)
        fresh = store.prepare_production_bridge(original.preparation.request)
        with store.repository._read() as session:
            assert timing.binding_in_session(session, store.manifest.project_id, shot_id, 3000) == first
        reviewed = _review(store, fresh.proposal)
        _accept(store, reviewed)
        with store.repository._read() as session:
            reused = timing.binding_in_session(session, store.manifest.project_id, shot_id, 3000)
            assert reused["admissionId"] != first["admissionId"]
            assert not timing.binding_is_current(session, store.manifest.project_id, shot_id, 3000, first)
        # Remove membership from the latest installed fixture, retaining the
        # historical admission and canonical shot; no historical/canonical
        # timing recovery is permitted even for the identical shot ID.
        with store.repository._lifecycle_write() as session:
            row = session.scalar(select(ProductionBridgeRevisionRow).where(ProductionBridgeRevisionRow.project_id == store.manifest.project_id, ProductionBridgeRevisionRow.revision == reviewed.revision))
            payload = deepcopy(row.proposal)
            payload["cuts"] = [item for item in payload["cuts"] if item["shotId"] != shot_id]
            row.proposal = payload
        with store.repository._read() as session, pytest.raises(InvalidTransitionError, match="not a member"):
            timing.binding_in_session(session, store.manifest.project_id, shot_id, 3000)


def test_projection_refuses_ambiguous_converging_typed_entry_states(tmp_path, monkeypatch):
    from plotloom.canonical_schema import StoryGraphV2
    from plotloom.edge_entry_states import EdgeEntryStateContractError
    _, store = _store(tmp_path)
    with closing(store):
        _prepare_installable_bridge(store)
        bridge = store.repository.production_bridge
        with store.repository._read() as session:
            inputs, board, script, cast_art = bridge._context(session, store.manifest.project_id)
            data = bridge._canonical._load_stage_payload(session, store.manifest.project_id, StageName.STORY_GRAPH).model_dump(mode="json", by_alias=True)
            edges = [edge for edge in data["edges"] if edge["sourceNodeId"] == "choose"]
            for edge, state in zip(edges, ("dawn", "night")):
                edge["targetNodeId"] = "ending-a"
                edge["entityStateEffects"] = [{"entityType": "location", "entityId": "S01", "state": state}]
            monkeypatch.setattr(bridge._canonical, "_load_stage_payload", lambda *_: StoryGraphV2.model_validate(data))
            with pytest.raises(EdgeEntryStateContractError, match="conflicting"):
                bridge._build(session, store.manifest.project_id, inputs=inputs, storyboard=board, script=script, cast_and_art=cast_art)


def test_prepare_api_requires_exact_typed_body_and_stale_body_performs_no_writes(tmp_path):
    from fastapi.testclient import TestClient

    from plotloom.api import create_project_folder_authoring_app
    storage, store = _store(tmp_path)
    with closing(store):
        _prepare_installable_bridge(store)
        project_id = store.manifest.project_id
        request = store.production_bridge_state().preparation.request.model_dump(mode="json", by_alias=True)
    client = TestClient(create_project_folder_authoring_app(storage))
    url = f"/api/v2/projects/{project_id}/production-bridge/proposals"
    assert client.post(url).status_code == 422
    assert client.post(url, json={}).status_code == 422
    valid = client.post(url, json=request)
    assert valid.status_code == 200, valid.text
    before = client.get(url.removesuffix("/proposals")).json()
    stale = client.post(url, json=request)
    assert stale.status_code == 409, stale.text
    assert client.get(url.removesuffix("/proposals")).json() == before
