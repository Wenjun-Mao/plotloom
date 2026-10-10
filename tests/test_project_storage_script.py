"""F4 script delivery and currentness contracts."""

from __future__ import annotations

from pathlib import Path

import pytest

from plotloom.art_contracts import (
    ArtAcceptRequest,
)
from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.project_storage.composition import ProjectFolderStorage
from plotloom.project_storage.operational_state import ProjectBusyError, close_blockers
from plotloom.script_contracts import (
    ScriptAcceptRequest,
    ScriptReopenRequest,
    ScriptSectionSaveRequest,
)
from tests.art_delivery_fixtures import _deliver
from tests.creative_delivery_fixtures import (
    _deliver_stage,
    _pilot_script,
    _prepare_art_context,
)


def test_f4_script_accepts_whole_pilot_preserves_scoped_edits_and_rejects_late_delivery(
    tmp_path: Path,
) -> None:
    storage = ProjectFolderStorage(
        outputs_root=tmp_path / "outputs",
        application_data_root=tmp_path / "application",
    )
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    project_id = store.manifest.project_id
    try:
        binding = _prepare_art_context(store)
        art_candidate, art_request = store.prepare_art_candidate(
            "ch_" + "q" * 32, render_style="realistic"
        )
        art_ready = store.admit_art_delivery(_deliver(store, art_request))
        store.accept_art_candidate(
            ArtAcceptRequest(
                job_id=art_candidate.job_id,
                expected_art_revision=0,
                binding=binding,
                art=art_ready.art,
            )
        )
        candidate, request = store.prepare_script_candidate("ch_" + "w" * 32)
        assert "script_publication_active" in close_blockers(store)
        ready = store.admit_script_delivery(
            _deliver_stage(
                store, request, "script.json", _pilot_script(), "script-fixture"
            )
        )
        accepted = store.accept_script_candidate(
            ScriptAcceptRequest(
                job_id=candidate.job_id,
                expected_script_revision=0,
                binding=ready.binding,
                script=ready.script,
            )
        )
        assert accepted.accepted_script and accepted.accepted_script.revision == 1
        original_ending = accepted.accepted_script.script["episodes"][2]
        store.reopen_script(ScriptReopenRequest(expected_script_revision=1))
        opening = dict(accepted.accepted_script.script["episodes"][0])
        opening["cliff"] = "Opening edit keeps its own consequence"
        saved = store.save_script_section(
            ScriptSectionSaveRequest(
                expected_script_revision=1,
                binding=accepted.accepted_script.binding,
                section_id="opening",
                episode=opening,
            )
        )
        assert (
            saved.accepted_script
            and saved.accepted_script.script["episodes"][2] == original_ending
        )
        pending, pending_request = store.prepare_script_candidate("ch_" + "v" * 32)
        store.cancel_script_candidate(pending.job_id)
        with pytest.raises(Exception, match="current prepared|unavailable|cancelled"):
            store.admit_script_delivery(
                _deliver_stage(
                    store,
                    pending_request,
                    "script.json",
                    _pilot_script(),
                    "late-script",
                )
            )
    finally:
        store.close()
    restarted = storage.projects.open(project_id)
    try:
        assert (
            restarted.script_state().accepted_script
            and restarted.script_state().accepted_script.revision == 2
        )
    finally:
        restarted.close()
    final_store = storage.projects.open(project_id)
    try:
        assert "art_reference_publication_active" not in close_blockers(final_store)
    finally:
        final_store.close()


def test_f4_script_admission_freezes_exact_mapping_route_budget_and_target_currentness(
    tmp_path: Path,
) -> None:
    """F4 timing constrains routes, not an equal split or three-episode total."""

    storage = ProjectFolderStorage(
        outputs_root=tmp_path / "outputs",
        application_data_root=tmp_path / "application",
    )
    store = storage.projects.create(
        FIXED_CHINESE_BRIEF.model_copy(update={"target_playthrough_seconds": 180})
    )
    try:
        binding = _prepare_art_context(store)
        art_candidate, art_request = store.prepare_art_candidate(
            "ch_" + "t" * 32, render_style="realistic"
        )
        art_ready = store.admit_art_delivery(_deliver(store, art_request))
        store.accept_art_candidate(
            ArtAcceptRequest(
                job_id=art_candidate.job_id,
                expected_art_revision=0,
                binding=binding,
                art=art_ready.art,
            )
        )
        candidate, request = store.prepare_script_candidate("ch_" + "x" * 32)
        assert len(candidate.binding.route_budget_hash) == 64
        assert (
            "sectionDurationCaps"
            not in request.input_artifacts["script-admission.json"]
        )
        assert (
            request.input_artifacts["script-admission.json"]["routeBudgetHash"]
            == candidate.binding.route_budget_hash
        )
        assert candidate.binding.complete_route_section_ids == [
            ["opening", "choose", "ending-a"],
            ["opening", "choose", "ending-b"],
        ]
        assert (
            request.input_artifacts["script-admission.json"]["targetPlaythroughSeconds"]
            == 180
        )
        assert (
            "aggregate duration across mutually exclusive endings as product-inapplicable"
            in request.creative_brief
        )
        assert (
            "frozen complete-route maximum remains applicable" in request.creative_brief
        )

        swapped = _pilot_script()
        swapped["sectionBindings"] = [
            {"sectionId": "opening", "episode": 2},
            {"sectionId": "ending-a", "episode": 1},
            {"sectionId": "ending-b", "episode": 3},
        ]
        with pytest.raises(ValueError, match="exactly match the frozen"):
            store.admit_script_delivery(
                _deliver_stage(store, request, "script.json", swapped, "swapped-script")
            )
    finally:
        store.close()


def test_f4_script_target_change_stales_prepared_delivery(tmp_path: Path) -> None:
    storage = ProjectFolderStorage(
        outputs_root=tmp_path / "outputs",
        application_data_root=tmp_path / "application",
    )
    store = storage.projects.create(
        FIXED_CHINESE_BRIEF.model_copy(update={"target_playthrough_seconds": 180})
    )
    try:
        binding = _prepare_art_context(store)
        art_candidate, art_request = store.prepare_art_candidate(
            "ch_" + "n" * 32, render_style="realistic"
        )
        art_ready = store.admit_art_delivery(_deliver(store, art_request))
        store.accept_art_candidate(
            ArtAcceptRequest(
                job_id=art_candidate.job_id,
                expected_art_revision=0,
                binding=binding,
                art=art_ready.art,
            )
        )
        _candidate, request = store.prepare_script_candidate("ch_" + "m" * 32)
        current = store.project()
        store.update_brief(
            current.brief.model_copy(update={"target_playthrough_seconds": 181}),
            expected_revision=current.revision,
        )
        with pytest.raises(Exception, match="stale"):
            store.admit_script_delivery(
                _deliver_stage(
                    store, request, "script.json", _pilot_script(), "stale-target"
                )
            )
    finally:
        store.close()


def test_f4_script_target_change_stales_ready_candidate_acceptance(
    tmp_path: Path,
) -> None:
    storage = ProjectFolderStorage(
        outputs_root=tmp_path / "outputs",
        application_data_root=tmp_path / "application",
    )
    store = storage.projects.create(
        FIXED_CHINESE_BRIEF.model_copy(update={"target_playthrough_seconds": 180})
    )
    try:
        binding = _prepare_art_context(store)
        art_candidate, art_request = store.prepare_art_candidate(
            "ch_" + "g" * 32, render_style="realistic"
        )
        art_ready = store.admit_art_delivery(_deliver(store, art_request))
        store.accept_art_candidate(
            ArtAcceptRequest(
                job_id=art_candidate.job_id,
                expected_art_revision=0,
                binding=binding,
                art=art_ready.art,
            )
        )
        candidate, script_request = store.prepare_script_candidate("ch_" + "h" * 32)
        ready = store.admit_script_delivery(
            _deliver_stage(
                store,
                script_request,
                "script.json",
                _pilot_script(),
                "ready-before-target-change",
            )
        )
        current = store.project()
        store.update_brief(
            current.brief.model_copy(update={"target_playthrough_seconds": 181}),
            expected_revision=current.revision,
        )
        with pytest.raises(Exception, match="changed before acceptance"):
            store.accept_script_candidate(
                ScriptAcceptRequest(
                    job_id=candidate.job_id,
                    expected_script_revision=0,
                    binding=ready.binding,
                    script=ready.script,
                )
            )
    finally:
        store.close()


def test_f4_prepared_script_blocks_snapshot_until_cancel_and_late_delivery_stays_refused(
    tmp_path: Path,
) -> None:
    storage = ProjectFolderStorage(
        outputs_root=tmp_path / "outputs",
        application_data_root=tmp_path / "application",
    )
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    project_id = store.manifest.project_id
    try:
        binding = _prepare_art_context(store)
        art_candidate, art_request = store.prepare_art_candidate(
            "ch_" + "p" * 32, render_style="realistic"
        )
        art_ready = store.admit_art_delivery(_deliver(store, art_request))
        store.accept_art_candidate(
            ArtAcceptRequest(
                job_id=art_candidate.job_id,
                expected_art_revision=0,
                binding=binding,
                art=art_ready.art,
            )
        )
        candidate, request = store.prepare_script_candidate("ch_" + "y" * 32)
    finally:
        store.close()

    with pytest.raises(ProjectBusyError, match="script_publication_active"):
        storage.recovery.create_snapshot(project_id)
    opened = storage.projects.open(project_id)
    try:
        opened.cancel_script_candidate(candidate.job_id)
        with pytest.raises(Exception, match="current prepared|unavailable|cancelled"):
            opened.admit_script_delivery(
                _deliver_stage(
                    opened, request, "script.json", _pilot_script(), "late-script"
                )
            )
    finally:
        opened.close()
    assert storage.recovery.create_snapshot(project_id).status == "complete"
