"""Explicit current source structure fixtures with an immutable planner seed."""

from plotloom.domain import ProjectBrief
from plotloom.source_outline_contracts import SectionMap
from plotloom.source_structures import planned_structure


def letter_section_map(project_id: str, brief: ProjectBrief) -> SectionMap:
    return SectionMap.model_validate({
        "seedTopology": planned_structure(project_id, brief),
        "topologyOrigin": "author",
        "topology": {
            "startNodeId": "opening",
            "nodes": [
                {"id": "opening", "kind": "start"},
                {"id": "choose", "kind": "decision"},
                {"id": "ending-a", "kind": "ending"},
                {"id": "ending-b", "kind": "ending"},
            ],
            "edges": [
                {"id": key, "sourceNodeId": source, "targetNodeId": target,
                 "kind": kind, "stateEffects": {}, "entityStateEffects": []}
                for key, source, target, kind in [
                    ("opening-choice", "opening", "choose", "continuation"),
                    ("sister", "choose", "ending-a", "choice"),
                    ("captain", "choose", "ending-b", "choice"),
                ]
            ],
            "joins": [],
        },
        "sections": [
            {"sectionId": "opening", "title": "渡口", "summary": "船夫收到最后一封信。", "ending": False, "footageMode": "footage"},
            {"sectionId": "choose", "title": "交信", "summary": "船夫选择收信人。", "ending": False, "footageMode": "route_only"},
            {"sectionId": "ending-a", "title": "交给妹妹", "summary": "妹妹在风暴前读到信。", "ending": True, "footageMode": "footage"},
            {"sectionId": "ending-b", "title": "交给船长", "summary": "船长带信离岸。", "ending": True, "footageMode": "footage"},
        ],
        "choices": [{
            "choiceId": "choose", "sectionId": "choose", "prompt": "把信交给谁？",
            "outcomes": [
                {"outcomeId": "sister", "label": "交给妹妹", "consequence": "妹妹留下。", "endingSectionId": "ending-a"},
                {"outcomeId": "captain", "label": "交给船长", "consequence": "船长启航。", "endingSectionId": "ending-b"},
            ],
        }],
        "joinReconciliations": {},
    })
