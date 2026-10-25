"""Installation authority reads use real persistence without review projection."""

from contextlib import closing

import pytest
from sqlalchemy import inspect, text

from plotloom.autopilot_materials import initial_inventory
from plotloom.domain import StageName
from plotloom.exceptions import InvalidTransitionError, NotFoundError
from plotloom.persistence.schema import ProductionBridgeHeadRow, ProductionBridgeRevisionRow
from plotloom.script_contracts import ScriptReopenRequest
from tests.production_bridge_fixtures import _prepare_installable_bridge
from tests.production_rebuild_fixtures import _accept, _store


def _database_state(store):
    """Compare logical persisted rows; SQLite journal bookkeeping is not state."""
    with store.repository.engine.connect() as connection:
        return {
            table: sorted(map(repr, connection.execute(text(f'SELECT * FROM "{table}"')).all()))
            for table in inspect(connection).get_table_names()
        }


def _refuse_projection(*_args, **_kwargs):
    pytest.fail("installation read reached unrelated production review projection")


def test_persistent_inventory_journey_observes_upstream_drift(tmp_path, monkeypatch):
    storage, store = _store(tmp_path)
    with closing(store):
        assert store.production_bridge_installation() is store.production_bridge_state().installation is None
        proposal = _prepare_installable_bridge(store)
        assert store.production_bridge_installation() is store.production_bridge_state().installation is None
        with pytest.raises(InvalidTransitionError, match="current accepted text and installation"):
            initial_inventory(store, object(), enforce_limits=False)
        accepted = _accept(store, proposal)
        installed = accepted.installation
        assert installed.status == "current"
        with monkeypatch.context() as full_reader:
            full_reader.setattr(store, "production_bridge_installation", lambda: store.production_bridge_state().installation)
            expected = initial_inventory(store, object(), enforce_limits=False)
        assert expected.entity_revision_id
        assert len([item for item in expected.subjects if item.owner == "image"]) == len(proposal.cuts)
        assert store.production_bridge_installation() == installed
        owner = store.repository.production_bridge
        monkeypatch.setattr(owner, "get_state", _refuse_projection)
        before = _database_state(store)
        assert initial_inventory(store, object(), enforce_limits=False) == expected
        assert _database_state(store) == before
        project_id = store.manifest.project_id
    with closing(storage.projects.open(project_id)) as reopened:
        assert reopened.production_bridge_installation() == installed
        assert initial_inventory(reopened, object(), enforce_limits=False) == expected
        with closing(storage.projects.open(project_id)) as separate:
            separate.reopen_script(ScriptReopenRequest(expected_script_revision=1))
        before = _database_state(reopened)
        outdated = reopened.production_bridge_installation()
        assert outdated.status == "outdated"
        assert outdated.admission_id == installed.admission_id
        assert outdated.installed_stage_revisions == installed.installed_stage_revisions
        assert outdated.stale_reasons == ["the accepted F5 storyboard review is stale"]
        assert outdated == reopened.production_bridge_state().installation
        with pytest.raises(InvalidTransitionError, match="current accepted text and installation"):
            initial_inventory(reopened, object(), enforce_limits=False)
        assert _database_state(reopened) == before


def test_pending_rebuild_and_unrelated_review_corruption_do_not_hide_installation(tmp_path, monkeypatch):
    _, store = _store(tmp_path)
    with closing(store):
        accepted = _accept(store, _prepare_installable_bridge(store))
        installed = accepted.installation
        pending = store.prepare_production_bridge(accepted.preparation.request).proposal
        assert pending.revision > installed.proposal_revision
        assert store.production_bridge_installation() == store.production_bridge_state().installation == installed
        with store.repository._write() as session:
            row = session.query(ProductionBridgeRevisionRow).filter_by(
                project_id=store.manifest.project_id, revision=pending.revision,
            ).one()
            row.proposal = {key: value for key, value in row.proposal.items() if key != "presentation"}
        with pytest.raises(KeyError, match="presentation"):
            store.production_bridge_state()
        owner = store.repository.production_bridge
        monkeypatch.setattr(owner, "_intent_package", _refuse_projection)
        monkeypatch.setattr(owner, "_prepare_request", _refuse_projection)
        monkeypatch.setattr("plotloom.persistence.project.production_bridge.assert_production_quiescent", _refuse_projection)
        monkeypatch.setattr("plotloom.persistence.project.production_bridge.bridge_job_views", _refuse_projection)
        before = _database_state(store)
        assert store.production_bridge_installation() == installed
        assert initial_inventory(store, object(), enforce_limits=False).entity_revision_id
        assert _database_state(store) == before


@pytest.mark.parametrize("field,value", [
    ("revision", 99), ("content_hash", "0" * 64),
    ("entity_revision_id", "unbound"), ("status", "stale"),
])
def test_canonical_binding_drift_and_rollback_are_seen_by_successive_reads(tmp_path, field, value):
    _, store = _store(tmp_path)
    with closing(store):
        installed = _accept(store, _prepare_installable_bridge(store)).installation
        project_id = store.manifest.project_id
        with store.repository._write() as session:
            head = store.repository._project_access.rows.stage(session, project_id, StageName.STORYBOARD)
            original = getattr(head, field)
            setattr(head, field, value)
        before = _database_state(store)
        outdated = store.production_bridge_installation()
        assert outdated.status == "outdated"
        assert "installed storyboard canonical binding changed" in outdated.stale_reasons
        assert outdated == store.production_bridge_state().installation
        with pytest.raises(InvalidTransitionError, match="current accepted text and installation"):
            initial_inventory(store, object(), enforce_limits=False)
        assert _database_state(store) == before
        with store.repository._write() as session:
            head = store.repository._project_access.rows.stage(session, project_id, StageName.STORYBOARD)
            setattr(head, field, original)
        assert store.production_bridge_installation() == installed


@pytest.mark.parametrize("defect,expected", [
    ("missing", "proposal evidence is missing or inconsistent"),
    ("hash", "proposal evidence is missing or inconsistent"),
    ("inputs", "proposal evidence is missing or inconsistent"),
    ("identities", "canonical identities are incomplete"),
])
def test_corrupt_installation_evidence_is_a_hard_failure(tmp_path, defect, expected):
    _, store = _store(tmp_path)
    with closing(store):
        proposal = _prepare_installable_bridge(store)
        _accept(store, proposal)
        owner, project_id = store.repository.production_bridge, store.manifest.project_id
        with store.repository._write() as session:
            admission = owner._latest_admission(session, project_id)
            if defect == "identities":
                admission.installed_stage_revisions = {}
            else:
                row = session.query(ProductionBridgeRevisionRow).filter_by(
                    project_id=project_id, revision=proposal.revision,
                ).one()
                if defect == "missing":
                    session.delete(row)
                elif defect == "hash":
                    row.content_hash = "0" * 64
                else:
                    row.inputs = {}
        before = _database_state(store)
        with pytest.raises(InvalidTransitionError, match=expected):
            store.production_bridge_installation()
        assert _database_state(store) == before


def test_project_and_bridge_head_admission_are_required(tmp_path):
    _, store = _store(tmp_path)
    with closing(store):
        owner, project_id = store.repository.production_bridge, store.manifest.project_id
        with pytest.raises(NotFoundError):
            owner.get_installation("missing-project")
        with store.repository._write() as session:
            session.delete(session.get(ProductionBridgeHeadRow, project_id))
        with pytest.raises(InvalidTransitionError, match="production bridge state is unavailable"):
            store.production_bridge_installation()


@pytest.mark.parametrize("failure", [OSError("storage unavailable"), ValueError("invalid model"), NotFoundError("owner state missing")])
def test_unexpected_context_failure_propagates(tmp_path, monkeypatch, failure):
    _, store = _store(tmp_path)
    with closing(store):
        _accept(store, _prepare_installable_bridge(store))

        def fail(*_args):
            raise failure

        monkeypatch.setattr(store.repository.production_bridge, "_context", fail)
        with pytest.raises(type(failure), match=str(failure)):
            store.production_bridge_installation()


def test_supported_canonical_edit_invalidates_inventory(tmp_path):
    _, store = _store(tmp_path)
    with closing(store):
        installed = _accept(store, _prepare_installable_bridge(store)).installation
        project_id = store.manifest.project_id
        head = store.authoring.get_stage_head(project_id, StageName.STORYBOARD)
        board = store.authoring.get_stage_payload(project_id, StageName.STORYBOARD).model_dump(mode="json", by_alias=True)
        board["shots"][0]["title"] += " revised after installation"
        store.authoring.update_stage(project_id, StageName.STORYBOARD, head.revision, board)
        before = _database_state(store)
        outdated = store.production_bridge_installation()
        assert outdated.status == "outdated"
        assert outdated.admission_id == installed.admission_id
        assert outdated == store.production_bridge_state().installation
        with pytest.raises(InvalidTransitionError, match="current accepted text and installation"):
            initial_inventory(store, object(), enforce_limits=False)
        assert _database_state(store) == before
