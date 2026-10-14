"""One deterministic bitmap per original native image ID, no ImageGen calls."""
from contextlib import closing
from copy import deepcopy

from plotloom.autopilot_materials import initial_inventory
from plotloom.autopilot_contracts import POLICY_VERSION
from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.image_commands import image_context
from tests import autopilot_controller_fixtures
from tests.autopilot_controller_fixtures import environment, run_text


def deliver_image(store, view, checkpoint, *, geometry=None, output_count=1, host=None):
    evidence = checkpoint["evidence"]
    if view.policy.version != POLICY_VERSION:
        raise AssertionError("fresh autopilot fixtures require the current Codex Exec launch policy")
    if host is None:
        raise AssertionError("Codex Exec image fixture requires its exact fake host")
    context = image_context(store, evidence["owner"], evidence["jobId"])
    attempt, _receipt = store.repository.autopilot.exec_attempt_evidence_for_operation(
        view.id, checkpoint["operationKey"]
    )
    if attempt is None:
        raise AssertionError("Codex Exec image fixture requires its persisted project attempt")
    host.complete_image(store, context, attempt, output_count=output_count, geometry=geometry)


def image_environment(tmp_path, monkeypatch, *, auto_deliver=True, geometry=None, brief=None, limits=None):
    storage, registry, service, view, text_calls = environment(tmp_path, monkeypatch, brief=brief, limits=limits)
    view = run_text(service, view)
    host = registry._codex_exec_test_host
    host.auto_deliver = auto_deliver
    host.image_geometry = geometry
    calls = host.image_calls
    return storage, registry, service, view, calls, text_calls


def handoff_image_environment(tmp_path, monkeypatch, *, auto_deliver=True, geometry=None, limits=None):
    """Build a real two-route review with the smallest useful filmed package."""
    brief = FIXED_CHINESE_BRIEF.model_copy(update={
        "decision_points_per_path": 1,
        "ending_count": 2,
        "desired_join_count": 0,
        "target_playthrough_seconds": 30,
    })
    original_candidate = autopilot_controller_fixtures.candidate

    def compact_candidate(store, request):
        if request.stage == "script":
            value = original_candidate(store, request)
            for episode in value["episodes"]:
                episode["targetSeconds"] = 10
                for scene in episode["scenes"]:
                    scene["flow"] = scene["flow"][:4]
            return value
        if request.stage == "storyboard":
            binding = store.storyboard_review_state().candidate.binding
            return _compact_handoff_storyboard(
                [item.episode for item in binding.section_bindings]
            )
        return original_candidate(store, request)

    monkeypatch.setattr(autopilot_controller_fixtures, "candidate", compact_candidate)
    return image_environment(
        tmp_path,
        monkeypatch,
        auto_deliver=auto_deliver,
        geometry=geometry,
        brief=brief,
        limits=limits,
    )


def _compact_handoff_storyboard(episodes):
    cuts = [
        {
            "seconds": 2.5,
            "beats": [index, index],
            "size": "medium",
            "camera": "Static Shot",
            "characters": ["keeper"],
            "props": [],
            "frame": "medium shot of the keeper in the beacon room at dawn, cinematic film still, cool gray palette, 16:9",
        }
        for index in range(1, 5)
    ]
    alignments = "; ".join(
        f"Picture {index} (from Shot {index}) aligns with the {2.5 * (index - 1):.2f}-second mark of the target video"
        for index in range(1, len(cuts) + 1)
    )
    shot_descriptions = "\n".join(
        (
            f"[Shot {index}] Cinematic, live-action, cool gray palette. The beacon room holds on <Picture {index}> with a static shot."
            if index == 1
            else f"[Shot {index}] At 00:{2.5 * (index - 1):06.3f}, the camera cuts to <Picture {index}> and holds a static shot in the beacon room."
        )
        for index in range(1, len(cuts) + 1)
    )
    return {
        "source": "Tide Light",
        "params": {"minCutSeconds": 2, "maxCutSeconds": 8, "maxSegmentSeconds": 15},
        "episodes": [
            {
                "ep": episode,
                "segments": [
                    {
                        "id": f"E{episode:02}-01",
                        "sceneIndex": 1,
                        "cuts": deepcopy(cuts),
                        "h3Prompt": (
                            "How the reference pictures align with the target video — "
                            f"{alignments}.\n\nintegrated_multimodal_description:\n"
                            f"{shot_descriptions}\n\noverall_soundscape: Quiet wind around an empty beacon room."
                            "\n\nnon_diegetic_music: N/A"
                        ),
                    }
                ],
            }
            for episode in episodes
        ],
    }


def assert_compact_handoff_pack(storage, view, complete, calls):
    """Prove the small pack still covers both routes and every unique shot."""
    with closing(storage.projects.open(view.project_id)) as store:
        inventory = initial_inventory(store, view.policy)
    image_subjects = {item.id for item in inventory.subjects if item.owner == "image"}
    reference_count = sum(item.owner != "image" for item in inventory.subjects)
    assert inventory.route_count == 2
    assert {frame.shot_id for frame in complete.frames} == image_subjects
    assert len(complete.frames) == len(image_subjects) < 27
    assert len(calls) == len(set(calls)) == len(image_subjects) + reference_count


def run_pack(storage, service, view, *, steps=400):
    for _ in range(steps):
        service.step(view.project_id)
        with closing(storage.projects.open(view.project_id)) as store:
            current = store.repository.autopilot.current(view.project_id)
        if current.state == "awaiting_review":
            return current
        assert current.state in {"running", "waiting"}, current.blocker
    raise AssertionError("bounded image pack did not reach review")
