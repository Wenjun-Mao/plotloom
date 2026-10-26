"""Reuse resolved inputs locally while preserving diagnostics and fresh authority."""
from contextlib import closing
from importlib import import_module
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from plotloom.art_contracts import ArtBinding, ArtReopenRequest
from plotloom.story_workloads import FIXED_CHINESE_BRIEF
from plotloom.exceptions import NotFoundError
from plotloom.persistence.project.art import ProjectArtPersistence
from plotloom.persistence.project.script import ProjectScriptPersistence
from plotloom.project_storage import ProjectFolderStorage
from plotloom.review_context_diagnostics import ReviewContextDiagnostic, ReviewContextError
from tests.specialist_reconciliation_seed import open_accepted_script_copy


FIELDS = {
    "cast": ("source_revision", "outline_revision", "section_map_revision", "graph_revision",
        "source_content_hash", "outline_content_hash", "section_map_content_hash", "graph_content_hash"),
    "art": ("source_revision", "outline_revision", "section_map_revision", "graph_revision", "cast_revision",
        "source_content_hash", "outline_content_hash", "section_map_content_hash", "graph_content_hash", "cast_content_hash"),
}
LABELS = {"source": "source", "outline": "accepted outline", "section_map": "section map",
    "graph": "installed graph", "cast": "accepted cast"}


@pytest.fixture(params=["cast", "art"])
def comparison(request, monkeypatch):
    name = request.param
    module = import_module(f"plotloom.persistence.project.{name}")
    owner = getattr(module, f"Project{name.title()}Persistence").__new__(getattr(module, f"Project{name.title()}Persistence"))
    events = []

    def project(*_):
        events.append("brief")
        return SimpleNamespace(brief=FIXED_CHINESE_BRIEF.model_dump(mode="python"))

    owner._access = SimpleNamespace(rows=SimpleNamespace(project=project))
    real_compare = module.binding_diagnostics

    def compare(*args):
        events.append("fields")
        return real_compare(*args)

    monkeypatch.setattr(module, "binding_diagnostics", compare)
    monkeypatch.setattr(owner, "_context", lambda *_: pytest.fail("comparison resolved upstream context"))
    return owner, name, module, events


def _different_bindings(name):
    frozen = SimpleNamespace(**dict.fromkeys(FIELDS[name], "before"), section_ids=["before"], render_contract=None)
    current = SimpleNamespace(**dict.fromkeys(FIELDS[name], "after"), section_ids=["after"])
    return current, frozen


def test_comparison_keeps_field_then_style_then_section_order_and_exact_diagnostics(comparison, monkeypatch):
    owner, name, module, events = comparison
    current, frozen = _different_bindings(name)

    def style(contract, _direction):
        assert contract is frozen.render_contract
        events.append("style")
        return False

    monkeypatch.setattr(module, f"{name}_style_current", style)
    reasons = owner._stale_against(object(), "project", current, frozen)
    assert events == ["fields", "brief", "style"]
    assert [reason.field for reason in reasons[:-2]] == list(FIELDS[name])
    for field, reason in zip(FIELDS[name], reasons):
        revision = field.endswith("_revision")
        prefix = field.removesuffix("_revision").removesuffix("_content_hash")
        assert reason == ReviewContextDiagnostic(
            code="binding_revision_changed" if revision else "binding_content_changed",
            owner="characters" if field.startswith("cast_") else "source", field=field,
            technical_message=f"{LABELS[prefix]} {'revision' if revision else 'content'} changed",
        )
    assert reasons[-2] == ReviewContextDiagnostic(code=f"{name}_render_contract_changed",
        owner="characters" if name == "cast" else "art",
        technical_message=f"{name} render contract is not current; prepare a new {name} task")
    assert reasons[-1] == ReviewContextDiagnostic(code="section_context_changed", owner="source",
        technical_message="section context changed")


@pytest.mark.parametrize("error", [ValueError("invalid style"), OSError("unreadable style"),
    ReviewContextError(ReviewContextDiagnostic(code="binding_value_changed", owner="art", technical_message="style marker"))])
def test_stale_does_not_swallow_comparison_style_errors_even_with_field_differences(comparison, monkeypatch, error):
    owner, name, module, events = comparison
    current, frozen = _different_bindings(name)
    monkeypatch.setattr(owner, "_context", lambda *_: (current,))

    def style(*_):
        events.append("style")
        raise error

    monkeypatch.setattr(module, f"{name}_style_current", style)
    with pytest.raises(type(error)) as caught:
        owner._stale(object(), "project", frozen)
    assert caught.value is error and events == ["fields", "brief", "style"]


def _art_binding():
    return ArtBinding(**{field: 1 if field.endswith("_revision") else "a" * 64 for field in FIELDS["art"]},
        section_ids=["scene"], render_contract={"frozen": "accepted Art receipt"})


def _script_owner(*, status="accepted", row=True, invalid_binding=False, resolve_error=None, compare_error=None, compare_result=()):
    events = []
    inherited = _art_binding()

    def resolve(*_):
        events.append("resolve")
        if resolve_error is not None:
            raise resolve_error
        return inherited, {}, {}, {}, {}

    def compare(*_):
        events.append("compare")
        if compare_error is not None:
            raise compare_error
        return list(compare_result)

    def project(*_):
        events.append("target")
        return SimpleNamespace(brief={"target_playthrough_seconds": 0})

    art = SimpleNamespace(_head=lambda *_: SimpleNamespace(status=status, revision=1),
        _context=resolve, _stale_against=compare)
    accepted = SimpleNamespace(binding={} if invalid_binding else inherited.model_dump(by_alias=True))
    session = SimpleNamespace(scalar=lambda *_: accepted if row else None)
    owner = ProjectScriptPersistence(SimpleNamespace(rows=SimpleNamespace(project=project)), art)
    return owner, session, events


@pytest.mark.parametrize("status,row", [("missing", True), ("reopened", True), ("accepted", False)])
def test_script_missing_or_unaccepted_art_does_not_resolve_upstream(status, row):
    owner, session, events = _script_owner(status=status, row=row, invalid_binding=True)
    with pytest.raises(ReviewContextError) as caught:
        owner._context(session, "project")
    assert caught.value.diagnostic.code == "accepted_art_not_current" and events == []


def test_script_validates_accepted_binding_before_resolving_art():
    owner, session, events = _script_owner(invalid_binding=True)
    with pytest.raises(ValidationError):
        owner._context(session, "project")
    assert events == []


def test_script_maps_only_art_resolution_error_before_target_without_exception_chain():
    error = ReviewContextError(ReviewContextDiagnostic(code="installed_graph_not_current", owner="source", technical_message="source marker"))
    owner, session, events = _script_owner(resolve_error=error)
    with pytest.raises(ReviewContextError) as caught:
        owner._context(session, "project")
    assert caught.value.diagnostic == ReviewContextDiagnostic(code="accepted_art_not_current", owner="art",
        technical_message="a current accepted art revision is required before preparing script")
    assert caught.value.__cause__ is caught.value.__context__ is None
    assert events == ["resolve"]


@pytest.mark.parametrize("phase", ["resolve", "compare"])
@pytest.mark.parametrize("error", [ValueError("invalid model"), OSError("storage failure"), NotFoundError("missing owner")])
def test_script_unexpected_errors_propagate_before_target(phase, error):
    owner, session, events = _script_owner(**{f"{phase}_error": error})
    with pytest.raises(type(error)) as caught:
        owner._context(session, "project")
    assert caught.value is error and "target" not in events


def test_script_comparison_review_error_is_not_remapped():
    error = ReviewContextError(ReviewContextDiagnostic(code="art_render_contract_changed", owner="art", technical_message="style marker"))
    owner, session, events = _script_owner(compare_error=error)
    with pytest.raises(ReviewContextError) as caught:
        owner._context(session, "project")
    assert caught.value is error and events == ["resolve", "compare"]


def test_script_stale_art_binding_wins_over_missing_target():
    diagnostic = ReviewContextDiagnostic(code="binding_revision_changed", owner="source",
        field="source_revision", technical_message="source revision changed")
    owner, session, events = _script_owner(compare_result=[diagnostic])
    with pytest.raises(ReviewContextError) as caught:
        owner._context(session, "project")
    assert caught.value.diagnostic.code == "accepted_art_not_current"
    assert events == ["resolve", "compare"]


def test_script_checks_missing_target_after_one_successful_resolution_and_comparison():
    owner, session, events = _script_owner()
    with pytest.raises(ReviewContextError) as caught:
        owner._context(session, "project")
    assert caught.value.diagnostic.code == "playthrough_target_missing"
    assert events == ["resolve", "compare", "target"]


@pytest.mark.parametrize("error", [ReviewContextError(ReviewContextDiagnostic(code="source_context_not_ready", owner="source", technical_message="source marker")), OSError("source unreadable")])
def test_art_resolves_source_before_checking_missing_accepted_cast(error):
    events = []

    def resolve(*_):
        events.append("resolve")
        raise error

    cast = SimpleNamespace(_context=resolve, _head=lambda *_: pytest.fail("head read before source resolution"))
    owner = ProjectArtPersistence(SimpleNamespace(), cast)
    with pytest.raises(type(error)) as caught:
        owner._context(object(), "project")
    assert caught.value is error and events == ["resolve"]


@pytest.mark.parametrize("status,row", [("missing", True), ("reopened", True), ("accepted", False)])
def test_art_reads_source_once_then_refuses_missing_or_unaccepted_cast(status, row):
    events = []
    cast = SimpleNamespace(_context=lambda *_: events.append("resolve") or (None, {}, {}, {}),
        _head=lambda *_: SimpleNamespace(status=status, revision=1),
        _stale_against=lambda *_: pytest.fail("unaccepted Cast was compared"))
    session = SimpleNamespace(scalar=lambda *_: SimpleNamespace(binding={}) if row else None)
    owner = ProjectArtPersistence(SimpleNamespace(), cast)
    with pytest.raises(ReviewContextError) as caught:
        owner._context(session, "project")
    assert caught.value.diagnostic.code == "accepted_cast_not_current" and events == ["resolve"]


@pytest.mark.parametrize("name", ["cast", "art", "script"])
def test_empty_state_does_not_resolve_upstream(tmp_path, monkeypatch, name):
    storage = ProjectFolderStorage(outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application")
    with closing(storage.projects.create(FIXED_CHINESE_BRIEF)) as store:
        owner = getattr(store.repository, name)
        monkeypatch.setattr(owner, "_context", lambda *_: pytest.fail("empty state resolved upstream"))
        state = owner.get_state(store.manifest.project_id)
        assert state.status == "missing" and state.stale_reasons == []


def test_real_art_script_calls_resolve_cast_once_each_and_stay_fresh_in_one_session(
    tmp_path, monkeypatch, accepted_script_reconciliation_seed,
):
    storage = ProjectFolderStorage(outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application")
    with closing(open_accepted_script_copy(storage, accepted_script_reconciliation_seed)) as store:
        project = store.manifest.project_id
        cast, art, script = store.repository.cast, store.repository.art, store.repository.script
        accepted = store.script_state().accepted_script
        frozen = accepted.binding.model_dump(mode="json", by_alias=True)
        resolve = cast._context
        calls = []

        def counted(*args):
            calls.append(True)
            return resolve(*args)

        monkeypatch.setattr(cast, "_context", counted)
        with script._access.leases.read() as session:
            art._context(session, project)
            assert len(calls) == 1
            first = script._context(session, project)
            assert len(calls) == 2
            assert first[0].model_dump(mode="json", by_alias=True) == frozen
            assert script._context(session, project) == first and len(calls) == 3
        store.reopen_art(ArtReopenRequest(expected_art_revision=1))
        calls.clear()
        with script._access.leases.read() as session:
            with pytest.raises(ReviewContextError) as caught:
                script._context(session, project)
            assert caught.value.diagnostic.code == "accepted_art_not_current" and calls == []
        assert store.script_state().accepted_review_state.status == "retained"
        assert accepted.binding.model_dump(mode="json", by_alias=True) == frozen


def test_dual_art_state_keeps_two_independent_comparisons_and_separate_reads(
    tmp_path, monkeypatch, accepted_script_reconciliation_seed,
):
    storage = ProjectFolderStorage(outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application")
    with closing(open_accepted_script_copy(storage, accepted_script_reconciliation_seed)) as store:
        store.prepare_art_candidate("ch_" + "q" * 32, render_style="ghibli")
        cast = store.repository.cast
        resolve, calls = cast._context, []

        def counted(*args):
            calls.append(True)
            return resolve(*args)

        monkeypatch.setattr(cast, "_context", counted)
        state = store.art_state()
        assert state.accepted_art is not None and state.candidate is not None
        assert state.accepted_art.binding.render_contract != state.candidate.binding.render_contract
        assert len(calls) == 2
        assert store.art_state() == state and len(calls) == 4
