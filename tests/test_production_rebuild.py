"""One current installation, exact rebuild CAS, and transactional recovery."""

from contextlib import closing
from copy import deepcopy
from pathlib import Path

import pytest
from sqlalchemy import select

from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.domain import StageName
from plotloom.exceptions import InvalidTransitionError
from plotloom.persistence.schema import EntityRevisionRow, ProductionBridgeAdmissionRow
from plotloom.persistence.schema.project_source_outline import SourceGraphIdentityRow
from plotloom.project_storage import ProjectFolderStorage
from plotloom.script_contracts import ScriptReopenRequest, ScriptSectionSaveRequest
from tests.production_bridge_fixtures import _prepare_installable_bridge
from tests.production_rebuild_fixtures import _accept, _heads, _review, _store


def test_prepare_preserves_own_installed_authority_and_requires_fresh_reviews(tmp_path):
    storage, store = _store(tmp_path)
    with closing(store):
        installed = _accept(store, _prepare_installable_bridge(store))
        original = installed.installation
        board_head = store.authoring.get_stage_head(
            store.manifest.project_id, StageName.STORYBOARD
        )
        approval = store.repository._approvals.decide_storyboard_approval(
            store.manifest.project_id,
            expected_revision=board_head.revision,
            expected_content_hash=board_head.content_hash,
            decision="approve",
            reviewer="rebuild fixture",
            gate_set_version="storyboard.v2",
        )
        prepared = store.prepare_production_bridge(installed.preparation.request)
        assert prepared.status == "ready"
        assert prepared.installation == original
        assert prepared.installation.status == "current"
        assert prepared.installation.runtime_choice == original.runtime_choice
        assert (
            prepared.proposal.replacement_target.installed_admission_id
            == original.admission_id
        )
        assert prepared.proposal.intent_package.review_state == "pending"
        assert not prepared.proposal.presentation.reviewed
        with pytest.raises(InvalidTransitionError, match="not installable"):
            _accept(store, prepared.proposal)
        accepted = _accept(store, _review(store, prepared.proposal))
        assert accepted.installation.admission_id != original.admission_id
        assert accepted.installation.status == "current"
        assert accepted.installation.installed_stage_revisions["storyboard"] == 2
        assert not store.repository._approvals.get_approval_closure(approval.id).active
        assert store.repository._approvals.list_approval_decisions(
            project_id=store.manifest.project_id
        ) == [approval]
        project_id = store.manifest.project_id
    with closing(storage.projects.open(project_id)) as reopened:
        assert reopened.production_bridge_state().installation == accepted.installation


def test_populated_late_failure_rolls_back_revisions_admissions_and_installed_authority(
    tmp_path, monkeypatch
):
    _, store = _store(tmp_path)
    with closing(store):
        installed = _accept(store, _prepare_installable_bridge(store))
        fresh = store.prepare_production_bridge(installed.preparation.request)
        proposal = _review(store, fresh.proposal)
        heads = _heads(store)
        with store.repository._read() as session:
            counts = [
                len(session.scalars(select(owner)).all())
                for owner in (
                    EntityRevisionRow,
                    ProductionBridgeAdmissionRow,
                    SourceGraphIdentityRow,
                )
            ]
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
            assert counts == [
                len(session.scalars(select(owner)).all())
                for owner in (
                    EntityRevisionRow,
                    ProductionBridgeAdmissionRow,
                    SourceGraphIdentityRow,
                )
            ]


def test_stale_prepare_request_and_concurrent_canonical_target_refuse_without_writes(
    tmp_path,
):
    _, store = _store(tmp_path)
    with closing(store):
        installed = _accept(store, _prepare_installable_bridge(store))
        frozen = installed.preparation.request
        fresh = store.prepare_production_bridge(frozen)
        with pytest.raises(InvalidTransitionError, match="target changed"):
            store.prepare_production_bridge(frozen)
        proposal = _review(store, fresh.proposal)
        board = store.authoring.get_stage_payload(
            store.manifest.project_id, StageName.STORYBOARD
        )
        store.authoring.update_stage(
            store.manifest.project_id, StageName.STORYBOARD, 1, board
        )
        # A real new canonical revision is required; allow-noop public writes
        # intentionally retain identical content, so install a distinct title.
        board_data = board.model_dump(mode="json", by_alias=True)
        board_data["shots"][0]["title"] += " changed"
        store.authoring.update_stage(
            store.manifest.project_id, StageName.STORYBOARD, 1, board_data
        )
        before = _heads(store)
        with pytest.raises(InvalidTransitionError, match="target changed"):
            _accept(store, proposal)
        assert _heads(store) == before


def test_same_hash_unowned_graph_cannot_borrow_authored_identity(tmp_path):
    _, store = _store(tmp_path)
    with closing(store):
        _prepare_installable_bridge(store)
        graph = store.authoring.get_stage_payload(
            store.manifest.project_id, StageName.STORY_GRAPH
        )
        with store.repository._lifecycle_write() as session:
            project = store.repository._project_row(session, store.manifest.project_id)
            from plotloom.domain import utc_now

            store.repository.production_bridge._canonical.install_source_map_graph_in_session(
                session,
                project,
                graph,
                expected_revision=1,
                now=utc_now(),
            )
        assert store.cast_state().status == "stale"
        assert store.production_bridge_state().preparation.status == "unavailable"


def test_new_proposal_cannot_restore_outdated_installation_or_borrow_its_choices(
    tmp_path,
):
    _, store = _store(tmp_path)
    with closing(store):
        installed = _accept(store, _prepare_installable_bridge(store))
        board = store.authoring.get_stage_payload(
            store.manifest.project_id, StageName.STORYBOARD
        ).model_dump(mode="json", by_alias=True)
        board["shots"][0]["title"] += " revised"
        store.authoring.update_stage(
            store.manifest.project_id, StageName.STORYBOARD, 1, board
        )
        outdated = store.production_bridge_state()
        assert outdated.installation.status == "outdated"
        assert (
            outdated.installation.runtime_choice
            == installed.installation.runtime_choice
        )
        prepared = store.prepare_production_bridge(outdated.preparation.request)
        assert prepared.installation == outdated.installation
        assert prepared.status == "ready"
        assert prepared.installation.inputs == outdated.installation.inputs


def test_fresh_prepare_cannot_launder_stale_accepted_f5(tmp_path: Path):
    storage = ProjectFolderStorage(
        outputs_root=tmp_path / "outputs",
        application_data_root=tmp_path / "application",
    )
    with closing(
        storage.projects.create(
            FIXED_CHINESE_BRIEF.model_copy(
                update={"shots_per_scene_min": 9, "shots_per_scene_max": 9}
            )
        )
    ) as store:
        before = _prepare_installable_bridge(store)
        prepare_request = store.production_bridge_state().preparation.request
        script = store.script_state().accepted_script
        store.reopen_script(
            ScriptReopenRequest(expected_script_revision=script.revision)
        )
        with pytest.raises(InvalidTransitionError):
            store.prepare_production_bridge(prepare_request)
        episode = deepcopy(script.script["episodes"][0])
        episode["cliff"] = "Changed accepted authority"
        store.save_script_section(
            ScriptSectionSaveRequest(
                expected_script_revision=script.revision,
                binding=script.binding,
                section_id="opening",
                episode=episode,
            )
        )
        assert store.storyboard_review_state().status == "stale"
        with pytest.raises(InvalidTransitionError, match="stale"):
            store.prepare_production_bridge(prepare_request)
        after = store.production_bridge_state().proposal
        assert (
            after.revision == before.revision
            and after.content_hash == before.content_hash
        )
        assert (
            store.authoring.get_stage_head(
                store.manifest.project_id, StageName.STORYBOARD
            ).revision
            == 0
        )
