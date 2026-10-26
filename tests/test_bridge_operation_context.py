"""Bridge shares source resolution within one read, never later authority."""

from contextlib import closing
from types import SimpleNamespace

import pytest

from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.stage_contracts import StageName
from plotloom.exceptions import InvalidTransitionError, NotFoundError
from plotloom.persistence.project.production_bridge import ProductionBridgePersistence
from plotloom.persistence.project.storyboard_review import ProjectStoryboardReviewPersistence, _ResolvedStoryboardContext
from plotloom.persistence.schema import ProductionBridgeRevisionRow
from plotloom.production_bridge_contracts import ProductionBridgeAcceptRequest
from plotloom.project_storage import ProjectFolderStorage
from plotloom.review_context_diagnostics import ReviewContextDiagnostic, ReviewContextError
from plotloom.script_contracts import ScriptReopenRequest
from tests.production_bridge_fixtures import _prepare_installable_bridge
from tests.storyboard_brief_fixtures import real_example_request


@pytest.fixture
def store(tmp_path):
    storage = ProjectFolderStorage(outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application")
    with closing(storage.projects.create(FIXED_CHINESE_BRIEF)) as owned:
        yield owned


def _install(store, proposal):
    return store.accept_production_bridge(ProductionBridgeAcceptRequest(
        expected_proposal_revision=proposal.revision, expected_content_hash=proposal.content_hash,
    ))


def _count_contexts(store, monkeypatch):
    counts = {"bridge": 0, "script": 0}
    for label, owner in (("bridge", store.repository.production_bridge), ("script", store.repository.script)):
        original = owner._context

        def counted(*args, _label=label, _original=original, **kwargs):
            counts[_label] += 1
            return _original(*args, **kwargs)

        monkeypatch.setattr(owner, "_context", counted)
    return counts


def test_empty_bridge_resolves_preparation_once(store, monkeypatch):
    calls = _count_contexts(store, monkeypatch)
    state = store.production_bridge_state()
    assert state.proposal is state.installation is None
    assert state.stale_reasons == []
    assert state.preparation.status == "unavailable"
    assert state.preparation.reason == "a current accepted F5 storyboard review is required"
    assert calls == {"bridge": 1, "script": 0}


@pytest.mark.parametrize("phase", ["pending", "accepted", "replacement"])
def test_each_bridge_read_resolves_once_and_independent_installation_stays_fresh(store, monkeypatch, phase):
    proposal = _prepare_installable_bridge(store)
    owner, project_id = store.repository.production_bridge, store.manifest.project_id
    if phase != "pending":
        accepted = _install(store, proposal)
        if phase == "replacement":
            owner.prepare(project_id, accepted.preparation.request)
    calls = _count_contexts(store, monkeypatch)
    state = owner.get_state(project_id)
    assert calls == {"bridge": 1, "script": 1}
    assert state.stale_reasons == []
    assert state.preparation.status == "available"
    if phase == "pending":
        assert state.installation is None
    else:
        assert state.installation.status == "current"
    assert owner.get_state(project_id) == state
    assert calls == {"bridge": 2, "script": 2}
    if phase != "pending":
        with store.repository._read() as session:
            assert owner.installation_in_session(session, project_id) == state.installation
        assert calls == {"bridge": 3, "script": 3}


def test_pending_and_installation_reasons_are_ordered_and_independent(store, monkeypatch):
    proposal = _prepare_installable_bridge(store)
    accepted = _install(store, proposal)
    owner, project_id = store.repository.production_bridge, store.manifest.project_id
    owner.prepare(project_id, accepted.preparation.request)
    with store.repository._write() as session:
        store.repository._project_access.rows.stage(session, project_id, StageName.STORY_GRAPH).revision += 1
    calls = _count_contexts(store, monkeypatch)
    state = owner.get_state(project_id)
    source_reason = "the accepted F5 storyboard review is stale"
    assert state.stale_reasons == [source_reason, "production rebuild replacement target changed"]
    assert state.installation.stale_reasons == [source_reason, "installed story_graph canonical binding changed"]
    assert state.preparation.reason == source_reason
    assert calls == {"bridge": 1, "script": 1}
    state.stale_reasons.append("consumer-owned")
    assert "consumer-owned" not in state.installation.stale_reasons


def test_separate_reads_prepare_and_accept_refuse_newly_stale_source(store):
    proposal = _prepare_installable_bridge(store)
    owner, project_id = store.repository.production_bridge, store.manifest.project_id
    original = owner.get_state(project_id)
    store.reopen_script(ScriptReopenRequest(expected_script_revision=1))
    changed = owner.get_state(project_id)
    assert changed.status == "stale"
    assert changed.stale_reasons == ["the accepted F5 storyboard review is stale"]
    assert changed.preparation.status == "unavailable"
    with pytest.raises(InvalidTransitionError, match="accepted F5 storyboard review is stale"):
        owner.prepare(project_id, original.preparation.request)
    with pytest.raises(InvalidTransitionError, match="proposal is stale"):
        owner.accept(project_id, ProductionBridgeAcceptRequest(
            expected_proposal_revision=proposal.revision, expected_content_hash=proposal.content_hash,
        ))


@pytest.mark.parametrize("defect,expected", [
    ("missing", "proposal evidence is missing or inconsistent"),
    ("hash", "proposal evidence is missing or inconsistent"),
    ("identities", "canonical identities are incomplete"),
])
def test_corrupt_installation_remains_a_hard_failure(store, defect, expected):
    proposal = _prepare_installable_bridge(store)
    _install(store, proposal)
    owner, project_id = store.repository.production_bridge, store.manifest.project_id
    with store.repository._write() as session:
        admission = owner._latest_admission(session, project_id)
        if defect == "identities":
            admission.installed_stage_revisions = {}
        else:
            row = session.query(ProductionBridgeRevisionRow).filter_by(project_id=project_id, revision=proposal.revision).one()
            if defect == "missing":
                session.delete(row)
            else:
                row.content_hash = "0" * 64
    with pytest.raises(InvalidTransitionError, match=expected):
        owner.get_state(project_id)


@pytest.mark.parametrize("failure", [OSError("storage unavailable"), ValueError("invalid model"), NotFoundError("owner state missing")])
def test_unexpected_context_failures_are_not_converted_to_unavailable(store, monkeypatch, failure):
    def unavailable(*_args):
        raise failure
    monkeypatch.setattr(store.repository.production_bridge, "_context", unavailable)
    with pytest.raises(type(failure), match=str(failure)):
        store.production_bridge_state()


def test_invalid_proposal_is_not_hidden_by_later_read_work(store, monkeypatch):
    proposal = _prepare_installable_bridge(store)
    owner, project_id = store.repository.production_bridge, store.manifest.project_id
    with store.repository._write() as session:
        row = session.query(ProductionBridgeRevisionRow).filter_by(project_id=project_id, revision=proposal.revision).one()
        row.proposal = {key: value for key, value in row.proposal.items() if key != "presentation"}
    monkeypatch.setattr(owner, "_installation_state", lambda *_: pytest.fail("corrupt proposal reached installation"))
    with pytest.raises(KeyError, match="presentation"):
        owner.get_state(project_id)


def _context_owner(monkeypatch, *, seconds=8, render_contract=True):
    _request, board, frozen = real_example_request("paper collage")
    frozen = frozen.model_copy(update={"review_max_cut_seconds": seconds})
    if not render_contract:
        frozen = frozen.model_copy(update={"storyboard_render_contract": None})
    base = frozen.model_copy(update={"review_max_cut_seconds": 8, "storyboard_render_contract": None})
    mapping = {"exact": "mapping from the same Script resolution"}
    resolved = _ResolvedStoryboardContext(context=(base, {"script": "same"}, {}, {"cast": "same"}, {"art": "same"}), section_map=mapping)
    review, calls = ProjectStoryboardReviewPersistence(None, None), []

    def resolve(*_args):
        calls.append(True)
        return resolved

    monkeypatch.setattr(review, "_head", lambda *_: SimpleNamespace(status="accepted", revision=1))
    monkeypatch.setattr(review, "_resolve_context", resolve)
    row = SimpleNamespace(binding=frozen.model_dump(mode="json", by_alias=True), revision=1, content_hash="c" * 64, storyboard=board)
    session = SimpleNamespace(scalar=lambda *_: row)
    access = SimpleNamespace(rows=SimpleNamespace(project=lambda *_: SimpleNamespace(revision=1, brief={"title": "fixture"})))
    owner = ProductionBridgePersistence(access, None, review, None)
    return owner, session, row, resolved, calls


@pytest.mark.parametrize("seconds,render_contract", [(8, False), (12, False), (8, True), (12, True)])
def test_bridge_uses_one_resolved_section_map_and_preserves_frozen_modes(monkeypatch, seconds, render_contract):
    owner, session, row, resolved, calls = _context_owner(monkeypatch, seconds=seconds, render_contract=render_contract)
    inputs, board, script, cast_art = owner._context(session, "project")
    assert len(calls) == 1
    assert board is row.storyboard and script is resolved.context[1]
    assert cast_art["__section_map__"] is resolved.section_map
    assert inputs["scriptRevision"] == resolved.context[0].script_revision
    assert resolved.context[0].review_max_cut_seconds == 8
    assert resolved.context[0].storyboard_render_contract is None


@pytest.mark.parametrize("failure", ["upstream", "binding", "full-equality"])
def test_bridge_keeps_generic_stale_mapping_and_full_equality_fallback(monkeypatch, failure):
    owner, session, row, resolved, _calls = _context_owner(monkeypatch)
    if failure == "upstream":
        def unavailable(*_args):
            raise ReviewContextError(ReviewContextDiagnostic(code="accepted_script_not_current", owner="script", technical_message="upstream detail must remain private"))
        monkeypatch.setattr(owner._review, "_resolve_context", unavailable)
    else:
        row.binding = row.binding | {"scriptRevision": resolved.context[0].script_revision + 1}
        if failure == "full-equality":
            monkeypatch.setattr(owner._review, "_binding_diagnostics", lambda *_: [])
    expected = "binding differs from current source" if failure == "full-equality" else "accepted F5 storyboard review is stale"
    with pytest.raises(InvalidTransitionError, match=expected):
        owner._context(session, "project")


def test_input_reasons_follow_frozen_order_and_return_independent_lists():
    frozen = {"scriptRevision": 1, "graphRevision": 1, "reviewRevision": 1}
    expected = ["scriptRevision changed", "graphRevision changed", "reviewRevision changed"]
    first = ProductionBridgePersistence._input_stale({}, frozen)
    second = ProductionBridgePersistence._input_stale({}, frozen)
    assert first == second == expected
    first.append("private")
    assert second == expected
