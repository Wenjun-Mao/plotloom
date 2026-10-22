"""Real upstream examples and confined packages for F5A Brief authority checks."""
from __future__ import annotations

import json
import os
import re
import subprocess
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

from plotloom.authored_route_timing import route_budget_hash
from plotloom.autopilot_brief_style import freeze_brief_style
from plotloom.creative_handoff_contracts import CreativeHandoffRequest
from plotloom.creative_handoff_exchange import CreativeHandoffExchange, canonical_json
from plotloom.production_dialogue_timing import (
    TIMING_FILENAME,
    freeze_f5_dialogue_timing,
    projected_dialogue_timing,
)
from plotloom.storyboard_brief_style import (
    CONTRACT_FILENAME,
    freeze_storyboard_brief_style,
    storyboard_brief_instructions,
)
from plotloom.storyboard_review_contracts import StoryboardReviewBinding

ROOT = Path(__file__).parents[1]


def canonical_example_schedule(script, board):
    """Author a distinct valid fixture schedule; preserve vendor files and every line.

    The upstream example uses its 4.5 CPS estimate. This prospective fixture
    instead gives dialogue its existing canonical minimum and action-only cuts
    two seconds, regrouping at the unchanged 15-second segment cap. Its complete
    total still satisfies the original 120-second target and all upstream gates.
    """
    result = deepcopy(board)
    for episode in result["episodes"]:
        source = next(item for item in script["episodes"] if item["ep"] == episode["ep"])
        segments = []
        for segment in episode["segments"]:
            flow = source["scenes"][segment["sceneIndex"] - 1]["flow"]
            body = segment["h3Prompt"].split("integrated_multimodal_description:", 1)[1].split("overall_soundscape:", 1)[0]
            paragraphs = re.split(r"(?=\[Shot \d+\])", body)[1:]
            sound = "overall_soundscape:" + segment["h3Prompt"].split("overall_soundscape:", 1)[1]
            groups, current, total = [], [], 0
            for cut, paragraph in zip(segment["cuts"], paragraphs, strict=True):
                minimum = sum(projected_dialogue_timing(item, "zh-CN")["estimatedDurationUnits"]
                              for item in flow[cut["beats"][0]-1:cut["beats"][1]] if "line" in item)
                units = max(2000, minimum)
                if total + units > 15000:
                    groups.append(current)
                    current, total = [], 0
                current.append((cut | {"seconds": units / 1000}, paragraph))
                total += units
            groups.append(current)
            for group in groups:
                cuts = [cut for cut, _ in group]
                starts, total = [], 0
                for cut in cuts:
                    starts.append(((total + 50) // 100) / 10)
                    total += round(cut["seconds"] * 1000)
                if len(cuts) == 1:
                    alignment = "For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced."
                else:
                    alignment = "How the reference pictures align with the target video — " + "; ".join(
                        f"Picture {index} (from Shot {index}) aligns with the {start:.2f}-second mark of the target video"
                        for index, start in enumerate(starts, 1)) + "."
                shots = []
                for index, ((cut, paragraph), start) in enumerate(zip(group, starts, strict=True), 1):
                    text = re.sub(r"^\[Shot \d+\]\s*(?:At \d+:\d+\.\d+,\s*)?", "", paragraph.strip())
                    text = re.sub(r"<Picture \d+>", f"<Picture {index}>", text)
                    prefix = f"[Shot {index}] " if index == 1 else f"[Shot {index}] At {int(start)//60:02}:{start%60:06.3f}, "
                    shots.append(prefix + text)
                segments.append(segment | {"id": f"E{episode['ep']:02}-{len(segments)+1:02}", "cuts": cuts,
                    "h3Prompt": alignment + "\n\nintegrated_multimodal_description:\n" + "\n".join(shots) + "\n\n" + sound})
        episode["segments"] = segments
    return result


def brief_board(board, direction):
    result = deepcopy(board)
    result["style"], result["promptLang"] = "saved-brief", "en"
    expression = "hand-cut paper collage with muted watercolor washes" if direction else "story-informed graphic composition"
    for episode in result["episodes"]:
        for segment in episode["segments"]:
            for cut in segment["cuts"]:
                cut["frame"] = cut["frame"].replace("cinematic film still", f"Saved Brief direction, {expression}")
            segment["h3Prompt"] = segment["h3Prompt"].replace("Cinematic, live-action", expression)
    return result


def real_example_request(direction):
    examples = ROOT / "third_party/shuohao-skills/skills"
    def read(stage, filename):
        return json.loads((examples / f"novel-{stage}/examples/渡口-{filename}.json").read_text())
    script = read("script", "script")
    board = brief_board(read("storyboard", "storyboard"), direction)
    # The upstream storyboard example is E01 only; bind its paired script scope
    # exactly instead of claiming that it covers the six-episode script sample.
    episodes = {episode["ep"] for episode in board["episodes"]}
    script["episodes"] = [episode for episode in script["episodes"] if episode["ep"] in episodes]
    board = canonical_example_schedule(script, board)
    board["params"] = {"minCutSeconds": 2, "maxCutSeconds": 8, "maxSegmentSeconds": 15}
    mapping = [{"sectionId": f"section-{ep['ep']}", "episode": ep["ep"]} for ep in script["episodes"]]
    routes = [[item["sectionId"] for item in mapping]]
    timing_hash = route_budget_hash(target_seconds=1000, section_bindings=mapping, routes=routes, route_only_ids=[])
    parent = freeze_brief_style(direction)
    contract = freeze_storyboard_brief_style(parent)
    script_hash = sha256(canonical_json(script)).hexdigest()
    dialogue_timing = freeze_f5_dialogue_timing(script, script_content_hash=script_hash, language="zh-CN")
    admission = {"scriptRevision": 1, "scriptContentHash": script_hash, "sectionBindings": mapping,
                 "routeBudgetHash": timing_hash, "targetPlaythroughSeconds": 1000,
                 "completeRouteSectionIds": routes, "routeOnlySectionIds": [], "reviewTiming": dict(board["params"])}
    request = CreativeHandoffRequest(job_id="ch_" + "r" * 32, project_id="f5a-example", section_id="pilot-storyboard",
        stage="storyboard", expected_stage_revision=0, source={"acceptedScriptRevision": 1, "acceptedScriptContentHash": script_hash},
        input_artifacts={"script.json": script, "outline.json": read("outline", "outline"),
            "cast.json": read("characters", "cast"), "art.json": read("art", "art"),
            "storyboard-admission.json": admission, CONTRACT_FILENAME: contract,
            TIMING_FILENAME: dialogue_timing.model_dump(mode="json", by_alias=True)},
        creative_brief=storyboard_brief_instructions())
    binding = StoryboardReviewBinding(
        **{f"{stage}_revision": 1 for stage in ("source", "outline", "section_map", "graph", "cast", "art", "script")},
        **{f"{stage}_content_hash": "a" * 64 for stage in ("source", "outline", "section_map", "graph", "cast", "art")},
        script_content_hash=script_hash, section_ids=[item["sectionId"] for item in mapping],
        render_contract=parent, storyboard_render_contract=contract, target_playthrough_seconds=1000,
        route_budget_hash=timing_hash, section_bindings=mapping, complete_route_section_ids=routes,
        route_only_section_ids=[], review_min_cut_seconds=2, review_max_cut_seconds=8, review_max_segment_seconds=15,
        dialogue_timing_contract=dialogue_timing)
    return request, board, binding


def execute_example_package(tmp_path, request, board):
    exchange = CreativeHandoffExchange(tmp_path / "creative-handoff")
    pin = exchange.current_execution_pin("storyboard")
    paths = exchange.write_package(request, pin)
    package, delivery = Path(paths["packagePath"]), Path(paths["deliveryPath"])
    delivery.mkdir()
    candidate = canonical_json(board)
    (delivery / "storyboard.json").write_bytes(candidate)
    commands = request.creative_brief.split("From the Plotloom repository root, run exactly:\n", 1)[1].splitlines()
    assert len(commands) == 2 and all(command.startswith("node scripts/brief-storyboard-style.mjs") for command in commands)
    for command in commands:
        subprocess.run(["bash", "-e", "-c", command], cwd=ROOT,
            env=os.environ | {"PACKAGE_ROOT": str(package), "DELIVERY_ROOT": str(delivery)}, check=True)
    assert {path.name for path in delivery.iterdir()} == {"storyboard.json", "report.html"}
    manifest = json.loads((package / "completion-manifest.example.json").read_text())
    manifest["candidate"]["sha256"] = sha256(candidate).hexdigest()
    manifest["report"]["sha256"] = sha256((delivery / "report.html").read_bytes()).hexdigest()
    manifest["deliveryId"] = "real-example"
    manifest["executorProvenance"]["codeRevision"] = "a" * 40
    manifest["limitations"] = ["disposable test fixture, not native execution"]
    (delivery / "completion.json").write_text(json.dumps(manifest))
    validated = exchange.read_delivery(request, pin)
    assert validated and {path.name for path in delivery.iterdir()} == {"storyboard.json", "report.html", "completion.json"}
    return validated


def invoke_adapter(tmp_path, request, board):
    board_path, request_path = tmp_path / "storyboard.json", tmp_path / "request.json"
    board_path.write_bytes(canonical_json(board))
    request_path.write_bytes(canonical_json(request.model_dump(mode="json", by_alias=True)))
    return subprocess.run(["node", str(ROOT / "scripts/brief-storyboard-style.mjs"), "validate", str(board_path), "--request", str(request_path)], capture_output=True, text=True, check=False)
