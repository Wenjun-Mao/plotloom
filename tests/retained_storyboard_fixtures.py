"""Small frozen Storyboard wire examples; no project or provider authority."""
from copy import deepcopy
from hashlib import sha256

from plotloom.autopilot_brief_style import freeze_brief_style
from plotloom.creative_handoff_contracts import CreativeHandoffRequest
from plotloom.creative_handoff_identity import canonical_json
from plotloom.production_dialogue_timing import TIMING_FILENAME, freeze_f5_dialogue_timing
from plotloom.storyboard_brief_style import freeze_storyboard_brief_style

PIN = {"upstreamRevision": "a" * 40, "upstreamSkillHash": "b" * 64, "specialistSkillHash": "c" * 64}
REVISION = "d" * 40
STYLE = "storyboard-style-contract.json"


def seal(value):
    value["contentHash"] = sha256(canonical_json({k: v for k, v in value.items() if k != "contentHash"})).hexdigest()


def storyboard_request(*, typed=False, historical=False):
    inherited = freeze_brief_style("preserve literal author direction")
    style = freeze_storyboard_brief_style(inherited)
    if historical:
        style["validatorHashes"].update(
            adapter="f94b0e31a2432c5fe608276261c8bf29e04496a550a42b3f618dbb0bf3cef704",
            dialogueTiming="82b7893b1fc4829f5990ed816e81a2dc755cd34b955834c84920bed13965e27d")
        seal(style)
    script = {"episodes": []}
    inputs = {STYLE: style, "script.json": script, "outline.json": {"episodes": []},
        "cast.json": {"characters": []}, "art.json": {"scenes": []},
        TIMING_FILENAME: freeze_f5_dialogue_timing(script, script_content_hash="a" * 64,
            language="zh-CN").model_dump(mode="json", by_alias=True)}
    data = {"jobId": "ch_" + "a" * 20, "projectId": "project-demo", "sectionId": "section-opening",
        "stage": "storyboard", "expectedStageRevision": 4,
        "source": {"kind": "synopsis", "text": "A choice has an irreversible consequence."},
        "inputArtifacts": inputs, "creativeBrief": "Preserve all frozen source facts."}
    if typed:
        data["contentValidationContract"] = "plotloom.typed-content-result.v1"
    return CreativeHandoffRequest.model_validate(data)


def replace_style(request, style):
    artifacts = deepcopy(request.input_artifacts)
    artifacts[STYLE] = style
    return request.model_copy(update={"input_artifacts": artifacts})
