"""Real upstream examples and confined packages for F5A Brief authority checks."""
from __future__ import annotations

import json
import os
import subprocess
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

from plotloom.authored_route_timing import route_budget_hash
from plotloom.autopilot_brief_style import freeze_brief_style
from plotloom.creative_handoff_contracts import CreativeHandoffRequest
from plotloom.creative_handoff_exchange import CreativeHandoffExchange, canonical_json
from plotloom.storyboard_brief_style import (
    CONTRACT_FILENAME,
    freeze_storyboard_brief_style,
    storyboard_brief_instructions,
)
from plotloom.storyboard_review_contracts import StoryboardReviewBinding

ROOT = Path(__file__).parents[1]


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
    board["params"] = {"minCutSeconds": 2, "maxCutSeconds": 8, "maxSegmentSeconds": 15}
    mapping = [{"sectionId": f"section-{ep['ep']}", "episode": ep["ep"]} for ep in script["episodes"]]
    routes = [[item["sectionId"] for item in mapping]]
    timing_hash = route_budget_hash(target_seconds=1000, section_bindings=mapping, routes=routes, route_only_ids=[])
    parent = freeze_brief_style(direction)
    contract = freeze_storyboard_brief_style(parent)
    script_hash = sha256(canonical_json(script)).hexdigest()
    admission = {"scriptRevision": 1, "scriptContentHash": script_hash, "sectionBindings": mapping,
                 "routeBudgetHash": timing_hash, "targetPlaythroughSeconds": 1000,
                 "completeRouteSectionIds": routes, "routeOnlySectionIds": [], "reviewTiming": dict(board["params"])}
    request = CreativeHandoffRequest(job_id="ch_" + "r" * 32, project_id="f5a-example", section_id="pilot-storyboard",
        stage="storyboard", expected_stage_revision=0, source={"acceptedScriptRevision": 1, "acceptedScriptContentHash": script_hash},
        input_artifacts={"script.json": script, "outline.json": read("outline", "outline"),
            "cast.json": read("characters", "cast"), "art.json": read("art", "art"),
            "storyboard-admission.json": admission, CONTRACT_FILENAME: contract},
        creative_brief=storyboard_brief_instructions())
    binding = StoryboardReviewBinding(
        **{f"{stage}_revision": 1 for stage in ("source", "outline", "section_map", "graph", "cast", "art", "script")},
        **{f"{stage}_content_hash": "a" * 64 for stage in ("source", "outline", "section_map", "graph", "cast", "art")},
        script_content_hash=script_hash, section_ids=[item["sectionId"] for item in mapping],
        render_contract=parent, storyboard_render_contract=contract, target_playthrough_seconds=1000,
        route_budget_hash=timing_hash, section_bindings=mapping, complete_route_section_ids=routes,
        route_only_section_ids=[], review_min_cut_seconds=2, review_max_cut_seconds=8, review_max_segment_seconds=15)
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
