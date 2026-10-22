"""Finite compact30s/two-cut text-only prefix for the eleven image-safety cases."""
from contextlib import closing
from dataclasses import dataclass

import pytest

from plotloom.autopilot_materials import initial_inventory
from tests.autopilot_controller_fixtures import default_brief, runtime
from tests.autopilot_image_fixtures import handoff_image_environment
from tests.autopilot_installed_text_core import (
    InstalledTextPrefix,
    claim_installed_text_copy,
    focused_installation_policy,
    installed_text_history,
    installed_text_view,
)
from tests.autopilot_seed_fixtures import (
    copy_closed_autopilot_seed,
    freeze_closed_autopilot_seed,
    run_facts,
)


@dataclass(frozen=True)
class CompactTwoCutTextPrefix(InstalledTextPrefix):
    """One named contract; the default prefix and completed packs are ineligible."""


def assert_compact_two_cut_text_boundary(store, registry):
    view = installed_text_view(store)
    if store.project().brief != default_brief().model_copy(update={"target_playthrough_seconds": 30}):
        raise ValueError("compact two-cut text prefix requires the exact compact30s Brief")
    if view.policy != focused_installation_policy(store, registry):
        raise ValueError("compact two-cut text prefix requires the unchanged compact policy")
    result = installed_text_history(store, view)
    source = store.source_outline_state()
    script = store.script_state()
    board = store.storyboard_review_state()
    installation = store.production_bridge_state().installation
    if (source.outline_status != "accepted" or source.section_map_status != "current"
            or source.section_map_stale_reasons or source.graph_admission is None
            or script.status != "accepted" or script.stale_reasons
            or board.status != "accepted" or board.stale_reasons
            or installation is None or installation.status != "current"):
        raise ValueError("compact two-cut text prefix requires current source/text/installation")
    accepted_script, accepted_board = script.accepted_script, board.accepted_review
    if accepted_script is None or accepted_board is None:
        raise ValueError("compact two-cut text prefix lacks accepted Script/Storyboard")
    binding = accepted_script.binding
    episodes = [item.episode for item in binding.section_bindings]
    if (episodes != [1, 2, 3] or binding.target_playthrough_seconds != 30
            or len(binding.complete_route_section_ids) != 2
            or accepted_board.binding.section_bindings != binding.section_bindings
            or accepted_board.binding.script_content_hash != accepted_script.content_hash):
        raise ValueError("compact two-cut text prefix requires exact source-bound topology")
    script_episodes = accepted_script.script["episodes"]
    if ([item["ep"] for item in script_episodes] != episodes
            or any(item["targetSeconds"] != 10 or len(item["scenes"]) != 1
                or len(item["scenes"][0]["flow"]) != 4 for item in script_episodes)):
        raise ValueError("compact two-cut text prefix requires Script10s/four beats")
    storyboard = accepted_board.storyboard
    if storyboard["params"] != {"minCutSeconds": 2, "maxCutSeconds": 8, "maxSegmentSeconds": 15}:
        raise ValueError("compact two-cut text prefix requires unchanged storyboard parameters")
    if [item["ep"] for item in storyboard["episodes"]] != episodes:
        raise ValueError("compact two-cut text prefix requires the exact storyboard episodes")
    for episode in storyboard["episodes"]:
        segments = episode["segments"]
        if len(segments) != 1 or segments[0]["sceneIndex"] != 1:
            raise ValueError("compact two-cut text prefix requires one filmed scene per episode")
        cuts = segments[0]["cuts"]
        if (len(cuts) != 2 or [cut["seconds"] for cut in cuts] != [5, 5]
                or [cut["beats"] for cut in cuts] != [[1, 2], [3, 4]]):
            raise ValueError("compact two-cut text prefix requires exactly two5s cuts/four beats")
    inventory = initial_inventory(store, view.policy)
    if (inventory.route_count != 2 or sum(item.owner == "image" for item in inventory.subjects) != 6
            or len(inventory.subjects) != 8):
        raise ValueError("compact two-cut text prefix requires two routes/six images/two references")
    return result


def _assert_no_image_or_live_reservations(storage):
    with storage.application._read() as connection:
        if connection.execute(
            "SELECT count(*) FROM global_accounting WHERE resource='images' OR status='reserved'"
        ).fetchone()[0]:
            raise ValueError("compact text prefix cannot retain image or live reservations")


def build_compact_two_cut_text_prefix(root):
    # This helper's existing candidate monkeypatch must never escape construction.
    with pytest.MonkeyPatch.context() as patch:
        storage, registry, service, view, images, text = handoff_image_environment(root, patch, cuts_per_scene=2)
        try:
            with closing(storage.projects.open(view.project_id)) as store:
                view, policy_text, records = assert_compact_two_cut_text_boundary(store, registry)
                home_name = store.home.name
            host = registry._codex_exec_test_host
            if (len(text) != 8 or len(set(text)) != 8 or images or host.pending
                    or host.admissions != 8 or len(host.statuses) != 8 or registry.view()["busy"]
                    or any(item.state not in {"completed", "settled"} for item in host.statuses.values())):
                raise ValueError("compact text prefix requires eight completed natural host deliveries")
            _assert_no_image_or_live_reservations(storage)
        finally:
            service.close()
        assert service._thread is None and service._descriptor is None
    project = freeze_closed_autopilot_seed(root, view.project_id, home_name)
    return CompactTwoCutTextPrefix(project, str(view.id), policy_text, records)


def copy_compact_two_cut_text_prefix(seed, destination, monkeypatch):
    storage, before = copy_closed_autopilot_seed(seed.project, destination)
    registry, service, host = runtime(storage, monkeypatch)
    try:
        with closing(storage.projects.open(seed.project.project_id)) as store:
            checked, policy_text, records = assert_compact_two_cut_text_boundary(store, registry)
            if (str(checked.id), policy_text, records) != (seed.run_id, seed.policy_text, seed.text_records):
                raise ValueError("compact two-cut text prefix immutable history changed")
            assert run_facts(checked) == run_facts(before)
        _assert_no_image_or_live_reservations(storage)
        return claim_installed_text_copy(storage, registry, service, host, before)
    except BaseException:
        service.close()
        raise


def compact_safety_image_environment(tmp_path, monkeypatch, compact_two_cut_text_prefix, *, auto_deliver=True):
    copied = copy_compact_two_cut_text_prefix(
        compact_two_cut_text_prefix, tmp_path / "compact-text-copy", monkeypatch)
    host = copied.registry._codex_exec_test_host
    # The two admission cases opt out only after validation and fresh claim/current.
    host.auto_deliver = auto_deliver
    assert len(compact_two_cut_text_prefix.text_records) == 8 and not copied.text_calls
    return copied.storage, copied.registry, copied.service, copied.view, copied.image_calls, copied.text_calls
