"""Real review reads/admission separate retained heads from fresh candidates."""

from pathlib import Path

import pytest

from plotloom.art_contracts import ArtAcceptRequest, ArtReopenRequest
from plotloom.cast_contracts import CastReopenRequest, CastSaveRequest
from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.project_storage.composition import ProjectFolderStorage
from plotloom.review_context_diagnostics import ReviewContextError
from plotloom.script_contracts import ScriptReopenRequest, ScriptSectionSaveRequest
from plotloom.storyboard_review_contracts import StoryboardReviewAcceptRequest
from tests.art_delivery_fixtures import _deliver
from tests.creative_delivery_fixtures import (
    _accepted_f4_script,
    _deliver_stage,
    _prepare_art_context,
)


@pytest.mark.parametrize("stage", ["art", "storyboard"])
@pytest.mark.parametrize("ready", [False, True])
@pytest.mark.parametrize("changed", [False, True])
def test_retained_read_diagnostics_do_not_block_current_replacement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    stage: str,
    ready: bool,
    changed: bool,
):
    store = ProjectFolderStorage(
        outputs_root=tmp_path / "outputs",
        application_data_root=tmp_path / "application",
    ).projects.create(FIXED_CHINESE_BRIEF)
    try:
        if stage == "art":
            _prepare_art_context(store)
            prepare = lambda job: store.prepare_art_candidate(
                job, render_style="realistic"
            )
            deliver = lambda request: store.admit_art_delivery(_deliver(store, request))
            accept = lambda candidate: store.accept_art_candidate(
                ArtAcceptRequest(
                    job_id=candidate.job_id,
                    expected_art_revision=candidate.expected_art_revision,
                    binding=candidate.binding,
                    art=candidate.art,
                )
            )
            state, cancel = store.art_state, store.cancel_art_candidate
            accepted = lambda value: value.accepted_art
        else:
            _accepted_f4_script(store)
            # Lifecycle/read projection qualification, not upstream content validation.
            monkeypatch.setattr(
                "plotloom.persistence.project.storyboard_review.ProjectStoryboardReviewPersistence._validate",
                staticmethod(lambda *_: None),
            )
            prepare = store.prepare_storyboard_review_candidate
            deliver = lambda request: store.admit_storyboard_review_delivery(
                _deliver_stage(
                    store, request, "storyboard.json", {"episodes": []}, request.job_id
                )
            )
            accept = lambda candidate: store.accept_storyboard_review_candidate(
                StoryboardReviewAcceptRequest(
                    job_id=candidate.job_id,
                    expected_review_revision=candidate.expected_review_revision,
                    binding=candidate.binding,
                )
            )
            state, cancel = (
                store.storyboard_review_state,
                store.cancel_storyboard_review_candidate,
            )
            accepted = lambda value: value.accepted_review
        _, request = prepare("ch_" + "a" * 32)
        first = accept(deliver(request))
        assert first.accepted_review_state.status == "current"
        retained = accepted(first)
        if changed and stage == "art":
            cast = store.cast_state().accepted_cast
            store.reopen_cast(CastReopenRequest(expected_cast_revision=cast.revision))
            store.save_reopened_cast(
                CastSaveRequest(
                    expected_cast_revision=cast.revision,
                    binding=cast.binding,
                    cast=cast.cast,
                    consumer_mappings=cast.consumer_mappings,
                )
            )
        elif changed:
            script = store.script_state().accepted_script
            store.reopen_script(
                ScriptReopenRequest(expected_script_revision=script.revision)
            )
            section = script.binding.section_bindings[0]
            store.save_script_section(
                ScriptSectionSaveRequest(
                    expected_script_revision=script.revision,
                    binding=script.binding,
                    section_id=section.section_id,
                    episode=script.script["episodes"][0],
                )
            )
        candidate, request = prepare("ch_" + "b" * 32)
        if ready:
            candidate = deliver(request)
        current = state()
        assert current.status == ("candidate_ready" if ready else "prepared")
        assert not current.stale_reasons
        assert accepted(current) == retained
        assert current.accepted_review_state.status == "retained"
        assert bool(current.accepted_review_state.stale_reasons) is changed
        if ready:
            replacement = accept(candidate)
            assert replacement.accepted_review_state.status == "current"
            assert accepted(replacement).revision == 2
        else:
            restored = cancel(candidate.job_id)
            assert restored.accepted_review_state.status == (
                "retained" if changed else "current"
            )
            assert accepted(restored) == retained
    finally:
        store.close()


@pytest.mark.parametrize("stage", ["art", "script"])
def test_stale_reopen_refuses_before_changing_the_accepted_head(
    tmp_path: Path, stage: str
):
    store = ProjectFolderStorage(
        outputs_root=tmp_path / "outputs",
        application_data_root=tmp_path / "application",
    ).projects.create(FIXED_CHINESE_BRIEF)
    try:
        _accepted_f4_script(store)
        if stage == "art":
            cast = store.cast_state().accepted_cast
            store.reopen_cast(CastReopenRequest(expected_cast_revision=cast.revision))
            read = store.art_state
            reopen = lambda: store.reopen_art(ArtReopenRequest(expected_art_revision=1))
        else:
            store.reopen_art(ArtReopenRequest(expected_art_revision=1))
            read = store.script_state
            reopen = lambda: store.reopen_script(
                ScriptReopenRequest(expected_script_revision=1)
            )
        before = read()
        assert before.accepted_review_state.status == "retained"
        with pytest.raises(ReviewContextError):
            reopen()
        assert read() == before
        owner = getattr(store.repository, stage)
        with owner._access.leases.read() as session:
            assert owner._head(session, store.manifest.project_id).status == "accepted"
    finally:
        store.close()
