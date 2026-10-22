"""Current-shaped 42-frame/5-reference pack through real native validators."""
from copy import deepcopy
import json
from pathlib import Path

from plotloom.conformance import FIXED_CHINESE_BRIEF
from tests import autopilot_controller_fixtures
from tests.autopilot_image_fixtures import image_environment


def realistic_pack_environment(tmp_path, monkeypatch):
    original = autopilot_controller_fixtures.candidate
    prop = json.loads((Path(__file__).resolve().parents[1] /
        "third_party/shuohao-skills/skills/novel-art/examples/渡口-art.json").read_text())["props"][0]

    def candidate(store, request):
        value = original(store, request)
        if request.stage == "characters":
            for identifier in ("observer", "witness"):
                person = deepcopy(value["characters"][0])
                person.update(id=identifier, name=identifier.title())
                value["characters"].append(person)
        elif request.stage == "art":
            value["props"] = [deepcopy(prop)]
            value["props"][0]["image"]["prompt"] = request.input_artifacts["art-style-contract.json"]["preset"]["render"] + " " + value["props"][0]["image"]["prompt"]
        elif request.stage == "script":
            for episode in value["episodes"]:
                episode["targetSeconds"] = 35
                scene = episode["scenes"][0]
                scene["characters"] = ["keeper", "observer"]
                scene["flow"] = [{"action": f"The keeper and observer inspect the beacon, action {index}."} for index in range(1, 15)]
        elif request.stage == "storyboard":
            for episode in value["episodes"]:
                episode["segments"].append(deepcopy(episode["segments"][-1]))
                for slot, segment in enumerate(episode["segments"]):
                    segment["id"] = f"E{episode['ep']:02}-{slot + 1:02}"
                    count = 4 if slot == 2 else 5
                    segment["cuts"] = [{"seconds": 2.5, "beats": [slot * 5 + index, slot * 5 + index],
                        "size": "medium", "camera": "Static Shot", "characters": [] if index == 1 else ["keeper", "observer"], "props": [],
                        "frame": "medium shot of the beacon room at dawn, cinematic film still, cool gray palette, 16:9"}
                        for index in range(1, count + 1)]
                    alignments = "; ".join(f"Picture {index} (from Shot {index}) aligns with the {2.5 * (index - 1):.2f}-second mark of the target video" for index in range(1, count + 1))
                    shots = "\n".join(f"[Shot {index}] " + ("Cinematic, live-action, cool gray palette. " if index == 1 else f"At 00:{2.5 * (index - 1):06.3f}, the camera cuts to ") +
                        f"<Picture {index}> and holds a static shot in the beacon room." for index in range(1, count + 1))
                    segment["h3Prompt"] = f"How the reference pictures align with the target video — {alignments}.\n\nintegrated_multimodal_description:\n{shots}\n\noverall_soundscape: Quiet wind around the beacon room.\n\nnon_diegetic_music: N/A"
        return value

    monkeypatch.setattr(autopilot_controller_fixtures, "candidate", candidate)
    first = True

    def geometry(*, context):
        nonlocal first
        if first and "shot" in context["request"]["frozenSnapshot"]:
            first = False
            return 941, 1672
        return None

    brief = FIXED_CHINESE_BRIEF.model_copy(update={"decision_points_per_path": 1, "ending_count": 2,
        "desired_join_count": 0, "target_playthrough_seconds": 70})
    return image_environment(tmp_path, monkeypatch, geometry=geometry, brief=brief)
