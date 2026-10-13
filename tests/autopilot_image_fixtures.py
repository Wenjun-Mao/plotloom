"""One deterministic bitmap per original native image ID, no ImageGen calls."""
import json
import re
import subprocess
from contextlib import closing
from copy import deepcopy
from hashlib import sha256
from io import BytesIO

from PIL import Image

from plotloom.autopilot_materials import initial_inventory
from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.image_commands import image_context
from tests import autopilot_controller_fixtures
from tests.autopilot_controller_fixtures import environment, run_text


def deliver_image(store, view, checkpoint, *, geometry=None, output_count=1, manifest_schema_version=3):
    evidence = checkpoint["evidence"]
    context = image_context(store, evidence["owner"], evidence["jobId"])
    request = context["request"]
    job_root = store.image_exchange_for(context)._root() / "jobs" / evidence["jobId"]
    assert (job_root / "package" / "request.json").is_file()
    delivery = job_root / "delivery"
    delivery.mkdir(exist_ok=True)
    (delivery / "outputs").mkdir(exist_ok=True)
    outputs = []
    size = geometry or (view.policy.image_width, view.policy.image_height)
    for index in range(output_count):
        buffer = BytesIO()
        Image.new("RGB", size, (110 + index, 80, 120)).save(buffer, format="PNG")
        content = buffer.getvalue()
        filename = f"fixture-{index}.png"
        (delivery / "outputs" / filename).write_bytes(content)
        outputs.append({"filename": filename, "sha256": sha256(content).hexdigest(), "role": request["kind"]})
    pin = view.policy.execution_pins["image"]
    provenance = {"codeRevision": pin["codeRevision"], "skillVersion": pin["skillVersion"], "skillHash": pin["skillHash"]}
    executor_pin = {"jobId": evidence["jobId"], "requestHash": context["requestHash"],
        "executionContract": pin["executionContract"], **provenance}
    if pin["executionContract"] == "codex_specialist.v3":
        executor_pin["nativeTaskId"] = view.policy.specialist_bindings["image"]
    (delivery / "executor-pin.json").write_text(json.dumps(executor_pin))
    tool_evidence = {"tool": "codex_imagegen", "available": True}
    if manifest_schema_version == 3:
        tool_evidence.update({"nativeTaskId": view.policy.specialist_bindings["image"],
            "imageGenExecutionId": f"exec-{evidence['jobId']}"})
    else:
        tool_evidence["taskId"] = view.policy.specialist_bindings["image"]
    manifest = {"schemaVersion": manifest_schema_version, "jobId": evidence["jobId"], "requestHash": context["requestHash"], "deliveryId": "fixture-image",
        "actualPrompt": "Deterministic bitmap fixture; no generation.", "outputs": outputs,
        "toolEvidence": tool_evidence,
        "executorProvenance": provenance, "limitations": ["Offline fixture, not product acceptance."]}
    identities = [item["originalHash"] for item in request["frozenSnapshot"].get("references", []) if item["role"] == "character_identity"]
    if identities:
        manifest["referenceUse"] = {"viewedReferenceHashes": list(dict.fromkeys(identities)), "identityNotes": "Fixture attestation; no visual identity judgment."}
    (delivery / "completion.json").write_text(json.dumps(manifest))


def image_environment(tmp_path, monkeypatch, *, auto_deliver=True, geometry=None, brief=None, limits=None):
    storage, registry, service, view, text_calls = environment(tmp_path, monkeypatch, brief=brief, limits=limits)
    view = run_text(service, view)
    calls = []
    queue = subprocess.run
    def image_queue(command, **kwargs):
        if len(command) > 1 and command[1] == "queue" and re.search(r"ij_[a-z0-9]{32}", command[-1]):
            job = re.search(r"ij_[a-z0-9]{32}", command[-1]).group()
            calls.append(job)
            if auto_deliver:
                with closing(storage.projects.open(view.project_id)) as store:
                    current = store.repository.autopilot.current(view.project_id)
                    checkpoint = next(item for item in current.checkpoints if item["evidence"]["jobId"] == job)
                    deliver_image(store, current, checkpoint, geometry=geometry(context=image_context(store, checkpoint["evidence"]["owner"], job)) if callable(geometry) else geometry)
            return subprocess.CompletedProcess(command, 0, "queued")
        return queue(command, **kwargs)
    monkeypatch.setattr(subprocess, "run", image_queue)
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
