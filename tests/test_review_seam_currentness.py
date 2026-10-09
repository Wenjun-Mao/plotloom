"""Review status follows the active candidate, otherwise retained acceptance."""

from pathlib import Path
from functools import partial

import pytest

from plotloom.art_contracts import ArtAcceptRequest
from plotloom.cast_contracts import CastAcceptRequest, CastBinding, CastConsumerMapping
from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.creative_handoff_contracts import CreativeHandoffError
from plotloom.project_storage.composition import ProjectFolderStorage
from plotloom.script_contracts import ScriptAcceptRequest
from tests.test_project_storage_art import (
    _deliver as deliver_art,
)
from tests.test_project_storage_art import (
    _deliver_stage,
    _pilot_script,
    _prepare_art_context,
)
from tests.test_project_storage_cast import _context
from tests.test_project_storage_cast import _deliver as deliver_cast


@pytest.fixture(params=["cast", "script"])
def seam(request, tmp_path: Path):
    store = ProjectFolderStorage(
        outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application",
    ).projects.create(FIXED_CHINESE_BRIEF.model_copy(update={"target_playthrough_seconds": 180}))
    stage = request.param
    context = [_context()]
    if stage == "cast":
        def bound_context(_session, _project_id):
            current = context[0]
            binding = CastBinding(
                source_revision=current.source.revision, source_content_hash=current.source.content_hash,
                outline_revision=1, outline_content_hash=current.accepted_outline.content_hash,
                section_map_revision=1, section_map_content_hash=current.accepted_section_map.content_hash,
                graph_revision=1, graph_content_hash="d" * 64, section_ids=["opening", "beacon", "dock"],
            )
            return binding, current.source.material.model_dump(mode="json", by_alias=True), current.accepted_outline.outline, current.accepted_section_map.mapping.model_dump(mode="json", by_alias=True)

        store.repository.cast._context = bound_context
    else:
        binding = _prepare_art_context(store)
        candidate, package = store.prepare_art_candidate("ch_" + "u" * 32, render_style="realistic")
        ready = store.admit_art_delivery(deliver_art(store, package))
        store.accept_art_candidate(ArtAcceptRequest(job_id=candidate.job_id, expected_art_revision=0, binding=binding, art=ready.art))

    def invalidate():
        if stage == "cast":
            context[0] = _context(2)
        else:
            current = store.project()
            store.update_brief(current.brief.model_copy(update={"target_playthrough_seconds": 181}), expected_revision=current.revision)

    def deliver(package):
        return deliver_cast(store, package) if stage == "cast" else _deliver_stage(store, package, "script.json", _pilot_script(), package.job_id)

    def accept(candidate):
        if stage == "cast":
            return store.accept_cast_candidate(CastAcceptRequest(
                job_id=candidate.job_id, expected_cast_revision=candidate.expected_cast_revision,
                binding=candidate.binding, consumer_mappings=[CastConsumerMapping(cast_character_id="lin", consumer_character_id="lin")],
            ))
        return store.accept_script_candidate(ScriptAcceptRequest(
            job_id=candidate.job_id, expected_script_revision=candidate.expected_script_revision,
            binding=candidate.binding, script=candidate.script,
        ))

    try:
        yield {
            "state": getattr(store, f"{stage}_state"),
            "prepare": partial(store.prepare_cast_candidate, render_style="realistic") if stage == "cast" else store.prepare_script_candidate,
            "admit": getattr(store, f"admit_{stage}_delivery"),
            "cancel": getattr(store, f"cancel_{stage}_candidate"),
            "accepted": lambda state: getattr(state, f"accepted_{stage}"),
            "invalidate": invalidate, "deliver": deliver, "accept": accept,
        }
    finally:
        store.close()


@pytest.mark.parametrize("ready", [False, True])
def test_first_candidate_reports_stale_without_any_accepted_revision(seam, ready):
    candidate, package = seam["prepare"]("ch_" + "v" * 32)
    delivery = seam["deliver"](package)
    if ready:
        candidate = seam["admit"](delivery)
    seam["invalidate"]()
    state = seam["state"]()
    assert seam["accepted"](state) is None
    assert state.status == "stale" and state.stale_reasons
    assert state.candidate.job_id == candidate.job_id
    with pytest.raises(CreativeHandoffError, match="stale|changed"):
        seam["accept"](candidate) if ready else seam["admit"](delivery)
    cancelled = seam["cancel"](candidate.job_id)
    assert cancelled.candidate is None
    assert cancelled.status == "missing"


@pytest.mark.parametrize("ready", [False, True])
def test_current_replacement_owns_status_over_stale_retained_acceptance(seam, ready):
    candidate, package = seam["prepare"]("ch_" + "w" * 32)
    accepted = seam["accept"](seam["admit"](seam["deliver"](package)))
    retained = seam["accepted"](accepted)
    seam["invalidate"]()
    assert seam["state"]().status == "stale"
    candidate, package = seam["prepare"]("ch_" + "x" * 32)
    if ready:
        candidate = seam["admit"](seam["deliver"](package))
    current = seam["state"]()
    assert current.status == ("candidate_ready" if ready else "prepared")
    assert not current.stale_reasons
    assert seam["accepted"](current) == retained
    if ready:
        assert seam["accepted"](seam["accept"](candidate)).revision == 2
    else:
        cancelled = seam["cancel"](candidate.job_id)
        assert cancelled.status == "stale"
        assert seam["accepted"](cancelled) == retained
