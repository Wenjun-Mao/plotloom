"""The approved structural shape; semantic/native-check witnesses stay separate."""
from plotloom.brief_contracts import ProjectBrief
from plotloom.source_outline_contracts import (
    SectionMap,
    SourceAuthoredStructure,
    SourceMaterial,
)
from tests.test_source_route_lengths import last_projection_graph


def authored_brief():
    return ProjectBrief(title="放映室最后一夜", synopsis="放映室里的最后一次交接。", decisionPointsPerPath=2,
        endingCount=3, desiredJoinCount=0, nodeBudget=7, maxOutDegree=2)


def authored_material():
    graph = last_projection_graph().model_dump(mode="json", by_alias=True)
    titles = {"n00": "发现", "c01": "第一次选择", "n10": "解释", "c02": "第二次选择",
        "e01": "独自交接", "e02": "共同交接", "e03": "留下旧记录"}
    structure = SourceAuthoredStructure(
        topology={"startNodeId": "n00", "nodes": [{"id": node["id"], "kind": node["kind"]} for node in graph["nodes"]],
            "edges": [{key: edge[key] for key in ("id", "sourceNodeId", "targetNodeId", "kind", "stateEffects", "entityStateEffects")} for edge in graph["edges"]], "joins": []},
        sections=[{"sectionId": node["id"], "title": titles[node["id"]], "summary": titles[node["id"]],
            "ending": node["kind"] == "ending", "footageMode": node["footageMode"]} for node in graph["nodes"]],
        choices=[{"choiceId": identifier, "sectionId": identifier, "prompt": titles[identifier], "outcomes": [
            {"outcomeId": edge["id"], "endingSectionId": edge["targetNodeId"], "label": edge["choiceText"],
                "consequence": titles[edge["targetNodeId"]]} for edge in graph["edges"] if edge["sourceNodeId"] == identifier]}
            for identifier in ("c01", "c02")], joinReconciliations={})
    return SourceMaterial(kind="imported_text", title="放映室最后一夜", text="明确保留七个节点、六条连接和全部选择。",
        adaptationIntent="保留原始结构，不增加选择。", attribution="isolated source-contract fixture",
        authoredStructure=structure)


def authored_mapping(store):
    source = store.source_outline_state().source
    return SectionMap.model_validate({**source.material.authored_structure.model_dump(mode="json", by_alias=True),
        "seedTopology": None, "authorSourceHash": source.content_hash, "topologyOrigin": "author"})
