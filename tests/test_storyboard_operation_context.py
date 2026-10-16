"""One owner read shares inputs, never authority across reads or frozen modes."""

from contextlib import contextmanager
from types import MethodType, SimpleNamespace

import pytest
from sqlalchemy import select

from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.creative_handoff_contracts import CreativeHandoffError
from plotloom.domain import utc_now
from plotloom.persistence.project.script import ProjectScriptPersistence
from plotloom.persistence.project.storyboard_review import (
    ProjectStoryboardReviewPersistence,
)
from plotloom.persistence.schema.project_storyboard_review import (
    StoryboardReviewRevisionRow,
)
from plotloom.project_storage.composition import ProjectFolderStorage
from plotloom.review_context_diagnostics import (
    ReviewContextDiagnostic,
    ReviewContextError,
)
from plotloom.script_contracts import ScriptBinding, ScriptReopenRequest
from plotloom.script_dialogue_compatibility import freeze_planned_storyboard_dialogue
from plotloom.storyboard_review_contracts import StoryboardReviewAcceptRequest
from tests.creative_delivery_fixtures import _accepted_f4_script, _deliver_stage
from tests.storyboard_brief_fixtures import real_example_request


@pytest.fixture
def bindings():
    _request, _board, storyboard = real_example_request("paper collage")
    script = ScriptBinding.model_validate({
        field: getattr(storyboard, field) for field in ScriptBinding.model_fields
    })
    return script, storyboard


def test_script_binding_diagnostics_keep_exact_field_order_and_section_reason(bindings):
    frozen, _ = bindings
    fields = (
        "source_revision", "source_content_hash", "outline_revision", "outline_content_hash",
        "section_map_revision", "section_map_content_hash", "graph_revision", "graph_content_hash",
        "cast_revision", "cast_content_hash", "art_revision", "art_content_hash",
        "target_playthrough_seconds", "route_budget_hash", "section_bindings",
        "complete_route_section_ids", "route_only_section_ids",
        "planned_storyboard_dialogue",
    )
    # Comparison is deliberately pure: no persistence or upstream validity is
    # needed to establish the exact existing diagnostic sequence.
    current = frozen.model_copy(update={
        **{field: object() for field in fields}, "section_ids": ["changed"],
    })
    reasons = ProjectScriptPersistence._binding_diagnostics(current, frozen)
    assert [reason.field for reason in reasons[:-1]] == list(fields)
    assert reasons[-1] == ReviewContextDiagnostic(
        code="section_context_changed", owner="source", technical_message="section context changed",
    )
    assert ProjectScriptPersistence._binding_diagnostics(frozen, frozen) == []


def _context_owner(monkeypatch, binding, *, status="accepted", row_exists=True, resolve=None):
    row = SimpleNamespace(
        revision=1, candidate_job_id="ch_" + "s" * 32, content_hash="a" * 64,
        binding=binding, script={"episodes": []}, accepted_at=utc_now(),
    )
    calls = []

    def context(*_args, **kwargs):
        calls.append(kwargs)
        if isinstance(resolve, Exception):
            raise resolve
        return resolve or (binding, {}, {}, {}, {}, {})

    script = SimpleNamespace(
        _head=lambda *_: SimpleNamespace(status=status, revision=1),
        _context=context,
        _binding_diagnostics=ProjectScriptPersistence._binding_diagnostics,
    )
    script._context_for_binding = MethodType(ProjectScriptPersistence._context_for_binding, script)
    monkeypatch.setattr(
        "plotloom.persistence.project.storyboard_review._upstream_script_outline",
        lambda *_: {},
    )
    return (
        ProjectStoryboardReviewPersistence(SimpleNamespace(rows=SimpleNamespace(
            project=lambda *_: SimpleNamespace(brief={"language": "zh-CN"}),
        )), script),
        SimpleNamespace(scalar=lambda *_: row if row_exists else None),
        calls,
    )


@pytest.mark.parametrize("status,row_exists", [("reopened", True), ("accepted", False)])
def test_missing_or_unaccepted_script_keeps_its_distinct_error(monkeypatch, bindings, status, row_exists):
    script, _ = bindings
    owner, session, calls = _context_owner(monkeypatch, script, status=status, row_exists=row_exists)
    with pytest.raises(ReviewContextError) as caught:
        owner._context(session, "project")
    assert caught.value.diagnostic == ReviewContextDiagnostic(
        code="accepted_script_not_current", owner="script",
        technical_message="a current accepted F4 script revision is required before preparing storyboard review",
    )
    assert calls == []


@pytest.mark.parametrize("failure", ["upstream", "compared-field", "full-binding"])
def test_script_context_error_mapping_is_preserved(monkeypatch, bindings, failure):
    script, _ = bindings
    if failure == "upstream":
        resolved = ReviewContextError(ReviewContextDiagnostic(
            code="accepted_art_not_current", owner="art", technical_message="upstream detail",
        ))
    else:
        changed = {"art_revision": 2} if failure == "compared-field" else {"render_contract": None}
        resolved = (script.model_copy(update=changed), {}, {}, {}, {}, {})
    owner, session, calls = _context_owner(monkeypatch, script, resolve=resolved)
    with pytest.raises(ReviewContextError) as caught:
        owner._context(session, "project")
    assert caught.value.diagnostic == ReviewContextDiagnostic(
        code="accepted_script_not_current", owner="script",
        technical_message=("the accepted F4 script binding is stale" if failure == "full-binding"
                           else "the accepted F4 script context is stale"),
    )
    assert len(calls) == 1


@pytest.mark.parametrize("error", [ValueError("invalid binding"), OSError("unreadable source")])
def test_unrelated_script_failures_are_not_converted(monkeypatch, bindings, error):
    script, _ = bindings
    owner, session, calls = _context_owner(monkeypatch, script, resolve=error)
    with pytest.raises(type(error), match=str(error)):
        owner._context(session, "project")
    assert len(calls) == 1


def test_context_and_each_binding_keep_independent_frozen_modes(monkeypatch, bindings):
    script, frozen = bindings
    owner, session, calls = _context_owner(monkeypatch, script)
    context = owner._context(session, "project")
    original = context[0].model_dump(mode="json", by_alias=True)
    historical = frozen.model_copy(update={"storyboard_render_contract": None})
    longer = frozen.model_copy(update={"review_max_cut_seconds": 12})
    old_projection, *_ = owner._project_context(context, historical)
    new_projection, *_ = owner._project_context(context, longer)
    assert old_projection.review_max_cut_seconds == 8
    assert "storyboardRenderContract" not in old_projection.model_dump(mode="json", by_alias=True)
    assert new_projection.review_max_cut_seconds == 12
    assert new_projection.storyboard_render_contract == frozen.storyboard_render_contract
    assert context[0].model_dump(mode="json", by_alias=True) == original
    assert len(calls) == 1


@pytest.mark.parametrize("maximum", [None, 8, 15])
def test_context_resolves_exact_inherited_script_selection(monkeypatch, bindings, maximum):
    script, _frozen = bindings
    planned = None if maximum is None else freeze_planned_storyboard_dialogue(max_cut_seconds=maximum, language="zh-CN")
    script = script.model_copy(update={"planned_storyboard_dialogue": planned})
    owner, session, calls = _context_owner(monkeypatch, script)
    context = owner._context(session, "project", max_cut_seconds=12)
    assert calls == [{"planned_storyboard_max_cut_seconds": maximum}]
    assert context[0].planned_storyboard_dialogue == planned
    assert context[0].review_max_cut_seconds == 12


def test_render_projection_failure_is_local_to_the_binding(monkeypatch, bindings):
    script, frozen = bindings
    owner, session, _ = _context_owner(monkeypatch, script)
    context = owner._context(session, "project")
    historical = context[0].model_copy(update={"storyboard_render_contract": None})
    frozen = historical.model_copy(update={"storyboard_render_contract": frozen.storyboard_render_contract})

    def unavailable(_contract):
        raise OSError("adapter unavailable")

    monkeypatch.setattr("plotloom.persistence.project.storyboard_review.freeze_storyboard_brief_style", unavailable)
    assert owner._binding_diagnostics(context, historical) == []
    assert owner._binding_diagnostics(context, frozen) == [ReviewContextDiagnostic(
        code="binding_value_changed", owner="storyboard-review", field="storyboard_render_contract",
        technical_message="storyboard render contract is unavailable or changed",
    )]


@contextmanager
def _store(tmp_path):
    store = ProjectFolderStorage(
        outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application",
    ).projects.create(FIXED_CHINESE_BRIEF)
    try:
        yield store
    finally:
        store.close()


def test_empty_review_does_not_resolve_upstream_context(tmp_path, monkeypatch):
    with _store(tmp_path) as store:
        monkeypatch.setattr(store.repository.script, "_context", lambda *_: pytest.fail("empty read resolved Script"))
        state = store.repository.storyboard_review.get_state(store.manifest.project_id)
        assert state.status == "missing" and state.stale_reasons == []


def test_dual_review_resolves_once_and_separate_reads_and_writes_stay_fresh(tmp_path, monkeypatch):
    with _store(tmp_path) as store:
        _accepted_f4_script(store, render_style="brief")
        owner = store.repository.storyboard_review
        project_id = store.manifest.project_id
        # This test owns read/currentness boundaries, not the upstream validator.
        monkeypatch.setattr(owner, "_validate", lambda *_: None)
        first, request = store.prepare_storyboard_review_candidate("ch_" + "a" * 32)
        ready = store.admit_storyboard_review_delivery(
            _deliver_stage(store, request, "storyboard.json", {"episodes": []}, "first"),
        )
        store.accept_storyboard_review_candidate(StoryboardReviewAcceptRequest(
            job_id=first.job_id, expected_review_revision=0, binding=ready.binding,
        ))
        # Explicit retained historical fixture: F5 render contracts were absent
        # on earlier accepted bindings, while replacements freeze their own.
        with owner._access.leases.lifecycle_write() as session:
            row = session.scalar(select(StoryboardReviewRevisionRow).where(
                StoryboardReviewRevisionRow.project_id == project_id,
                StoryboardReviewRevisionRow.revision == 1,
            ))
            row.binding = {key: value for key, value in row.binding.items() if key != "storyboardRenderContract"}
        candidate, request = store.prepare_storyboard_review_candidate("ch_" + "b" * 32, max_cut_seconds=12)
        delivery = _deliver_stage(store, request, "storyboard.json", {"episodes": []}, "second")
        original = store.repository.script._context
        calls = []

        def context(*args, **kwargs):
            calls.append(True)
            return original(*args, **kwargs)

        monkeypatch.setattr(store.repository.script, "_context", context)
        state = owner.get_state(project_id)
        assert len(calls) == 1
        assert state.stale_reasons == state.accepted_review_state.stale_reasons == []
        assert state.accepted_review.binding.review_max_cut_seconds == 8
        assert state.accepted_review.binding.storyboard_render_contract is None
        assert state.candidate.binding.review_max_cut_seconds == 12
        assert state.candidate.binding.storyboard_render_contract is not None
        assert owner.get_state(project_id) == state
        assert len(calls) == 2

        # A normal mutation between reads invalidates both retained bindings.
        store.reopen_script(ScriptReopenRequest(expected_script_revision=1))
        stale = owner.get_state(project_id)
        assert stale.status == "stale"
        assert stale.stale_reasons == stale.accepted_review_state.stale_reasons
        assert stale.stale_reasons[0].code == "accepted_script_not_current"
        with pytest.raises(CreativeHandoffError, match="stale"):
            store.admit_storyboard_review_delivery(delivery)
        assert owner.get_state(project_id) == stale
        assert stale.candidate.job_id == candidate.job_id
