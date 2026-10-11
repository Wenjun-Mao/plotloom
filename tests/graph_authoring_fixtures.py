"""Accepted-source graph project seeds and isolated project-copy helpers."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.source_outline_contracts import (
    OutlineAcceptRequest,
    SectionMap,
    SectionMapGraphInstallRequest,
)
from plotloom.source_structures import planned_structure
from tests.source_outline_fixtures import _deliver, _material, _request, _storage


@dataclass(frozen=True)
class AcceptedSourceProjectSeed:
    project_id: str
    home: Path
    database_path: str


def create_accepted_source_project(root: Path):
    storage = _storage(root)
    store = storage.projects.create(
        FIXED_CHINESE_BRIEF.model_copy(
            update={
                "node_budget": 12,
                "decision_points_per_path": 1,
                "ending_count": 1,
                "max_out_degree": 3,
                "desired_join_count": 1,
            }
        )
    )
    try:
        material = _material()
        store.save_source_material(expected_source_revision=0, material=material)
        request = _request(
            store.manifest.project_id, material, brief=store.project().brief
        )
        store.prepare_outline_candidate(request)
        store.admit_outline_delivery(_deliver(store, request))
        store.accept_outline_candidate(
            OutlineAcceptRequest(
                job_id=request.job_id,
                expected_source_revision=1,
                expected_outline_revision=0,
            )
        )
    except BaseException:
        store.close()
        raise
    return store


def build_accepted_source_project_seed(root: Path) -> AcceptedSourceProjectSeed:
    store = create_accepted_source_project(root)
    try:
        seed = AcceptedSourceProjectSeed(
            project_id=store.manifest.project_id,
            home=store.home,
            database_path=store.manifest.database_path,
        )
    finally:
        store.close()

    sidecars = tuple(seed.home.glob(f"{seed.database_path}-*"))
    if sidecars:
        raise RuntimeError("accepted graph seed retained SQLite sidecars after close")
    return seed


def copy_accepted_source_project(seed: AcceptedSourceProjectSeed, root: Path):
    outputs_root = root / "outputs"
    outputs_root.mkdir(parents=True, exist_ok=False)
    copied_home = outputs_root / seed.home.name
    shutil.copytree(seed.home, copied_home)
    store = _storage(root).projects.open(seed.project_id)
    if store.home.resolve() != copied_home.resolve():
        store.close()
        raise AssertionError("graph fixture opened a different project copy")
    return store


def authored_map(store):
    node_kinds = [
        ("opening", "start"),
        ("choose", "decision"),
        ("branch-123", "scene"),
        ("branch-222", "scene"),
        ("branch-333", "scene"),
        ("inserted-step", "scene"),
        ("merge", "join"),
        ("ending", "ending"),
    ]
    connections = [
        ("opening-choice", "opening", "choose", "continuation"),
        ("option-123", "choose", "branch-123", "choice"),
        ("option-222", "choose", "branch-222", "choice"),
        ("option-333", "choose", "branch-333", "choice"),
        ("branch-input", "branch-123", "inserted-step", "continuation"),
        ("new-continuation", "inserted-step", "merge", "continuation"),
        ("second-input", "branch-222", "merge", "continuation"),
        ("third-input", "branch-333", "merge", "continuation"),
        ("merge-ending", "merge", "ending", "continuation"),
    ]
    return SectionMap.model_validate(
        {
            "seedTopology": planned_structure(
                store.manifest.project_id, store.project().brief
            ),
            "topologyOrigin": "author",
            "topology": {
                "startNodeId": "opening",
                "nodes": [{"id": key, "kind": kind} for key, kind in node_kinds],
                "edges": [
                    {
                        "id": key,
                        "sourceNodeId": source,
                        "targetNodeId": target,
                        "kind": kind,
                        "stateEffects": (
                            {"retainedFact": "original traversal"}
                            if key == "branch-input"
                            else {}
                        ),
                        "entityStateEffects": [],
                    }
                    for key, source, target, kind in connections
                ],
                "joins": [
                    {
                        "id": "join-contract",
                        "joinNodeId": "merge",
                        "incomingNodeIds": [
                            "inserted-step",
                            "branch-222",
                            "branch-333",
                        ],
                        "requiredStateKeys": [],
                        "allowedDifferences": [],
                        "notes": "Authored reconciliation.",
                    }
                ],
            },
            "sections": [
                {
                    "sectionId": key,
                    "title": key,
                    "summary": f"Reviewed story at {key}.",
                    "ending": kind == "ending",
                    "footageMode": (
                        "route_only" if kind in {"decision", "join"} else "footage"
                    ),
                }
                for key, kind in node_kinds
            ],
            "choices": [
                {
                    "choiceId": "choose",
                    "sectionId": "choose",
                    "prompt": "Which action?",
                    "outcomes": [
                        {
                            "outcomeId": f"option-{number}",
                            "label": str(number),
                            "consequence": f"Action {number}.",
                            "endingSectionId": f"branch-{number}",
                        }
                        for number in [123, 222, 333]
                    ],
                }
            ],
            "joinReconciliations": {
                "join-contract": "The three actions reconnect at the shared ending."
            },
        }
    )


def install_request(state, draft_revision):
    return SectionMapGraphInstallRequest(
        expected_source_revision=state.source.revision,
        expected_source_content_hash=state.source.content_hash,
        expected_outline_revision=state.accepted_outline.revision,
        expected_outline_content_hash=state.accepted_outline.content_hash,
        expected_section_map_revision=state.accepted_section_map.revision,
        expected_section_map_content_hash=state.accepted_section_map.content_hash,
        expected_graph_revision=(
            state.graph_admission.graph_revision if state.graph_admission else 0
        ),
        expected_graph_draft_revision=draft_revision,
    )
