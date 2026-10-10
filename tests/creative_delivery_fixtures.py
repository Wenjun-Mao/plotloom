"""Reusable accepted creator-stage setup for isolated tests."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

from plotloom.art_contracts import (
    ArtAcceptRequest,
    ArtBinding,
)
from plotloom.cast_contracts import CastAcceptRequest, CastConsumerMapping
from plotloom.creative_handoff_contracts import CreativeHandoffRequest
from plotloom.creative_handoff_exchange import canonical_json
from plotloom.outline_settings import OUTLINE_SETTINGS_FILENAME, outline_settings
from plotloom.script_contracts import (
    ScriptAcceptRequest,
)
from plotloom.source_outline_contracts import (
    BranchOutcome,
    OutlineAcceptRequest,
    SectionChoice,
    SectionMap,
    SectionMapGraphInstallRequest,
    SourceMaterial,
    StorySection,
)
from plotloom.source_structures import planned_structure
from tests.art_delivery_fixtures import _deliver
from tests.cast_style_fixtures import style_fixture
from tests.graph_draft_fixtures import graph_draft_revision, graph_map_save_request


def _deliver_stage(
    store: object,
    request: CreativeHandoffRequest,
    filename: str,
    candidate: dict[str, object],
    delivery_id: str,
) -> object:
    exchange = store.creative_handoff_exchange()  # type: ignore[attr-defined]
    pin = store.creative_handoff_execution_pin(request)  # type: ignore[attr-defined]
    paths = exchange.write_package(request, pin)
    package = json.loads((Path(paths["packagePath"]) / "request.json").read_text())
    delivery = Path(paths["deliveryPath"])
    delivery.mkdir()
    content, report = (
        canonical_json(candidate),
        b"<!doctype html><html><body>fixture report</body></html>",
    )
    (delivery / filename).write_bytes(content)
    (delivery / "report.html").write_bytes(report)
    (delivery / "completion.json").write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "jobId": request.job_id,
                "requestHash": package["requestHash"],
                "deliveryId": delivery_id,
                "stage": request.stage,
                "candidate": {
                    "filename": filename,
                    "sha256": sha256(content).hexdigest(),
                },
                "report": {
                    "filename": "report.html",
                    "sha256": sha256(report).hexdigest(),
                },
                "executorProvenance": {
                    "codeRevision": "abcdef0",
                    "skillVersion": "fixture",
                    "skillHash": package["executionPin"]["specialistSkillHash"],
                    "upstreamRevision": package["executionPin"]["upstreamRevision"],
                    "upstreamSkillHash": package["executionPin"]["upstreamSkillHash"],
                    "model": "fixture",
                    "reasoningEffort": "high",
                },
                "limitations": ["fixture"],
            }
        )
    )
    result = exchange.read_delivery(request, pin)
    assert result is not None
    return result


def _prepare_accepted_f4_cast_context(store: object, structure_factory=None) -> None:
    project = store.project()
    if structure_factory is None:
        store.update_brief(
            project.brief.model_copy(
                update={
                    "decision_points_per_path": 1,
                    "ending_count": 2,
                    "desired_join_count": 0,
                }
            ),
            expected_revision=project.revision,
        )
    source = SourceMaterial(
        kind="synopsis",
        title="Tide Light",
        text="Lin chooses the beacon or dock.",
        attribution="fixture",
        rights_declaration="fixture",
        adaptation_intent="fixture",
    )
    store.save_source_material(expected_source_revision=0, material=source)  # type: ignore[attr-defined]
    outline_request = CreativeHandoffRequest(
        job_id="ch_" + "o" * 32,
        project_id=store.manifest.project_id,
        section_id="story",
        stage="outline",
        expected_stage_revision=0,
        source=source.model_dump(mode="json", by_alias=True),
        input_artifacts={
            OUTLINE_SETTINGS_FILENAME: outline_settings(store.project().brief),
            "story-topology.json": planned_structure(
                store.manifest.project_id, store.project().brief
            ).model_dump(mode="json", by_alias=True),
        },
        creative_brief="fixture",
    )  # type: ignore[attr-defined]
    store.prepare_outline_candidate(outline_request)  # type: ignore[attr-defined]
    store.admit_outline_delivery(
        _deliver_stage(
            store,
            outline_request,
            "outline.json",
            {"source": "Tide Light", "episodes": []},
            "outline-fixture",
        )
    )  # type: ignore[attr-defined]
    state = store.accept_outline_candidate(
        OutlineAcceptRequest(
            job_id=outline_request.job_id,
            expected_source_revision=1,
            expected_outline_revision=0,
        )
    )  # type: ignore[attr-defined]
    assert state.source and state.accepted_outline
    mapping = SectionMap(
        seed_topology=planned_structure(
            store.manifest.project_id, store.project().brief
        ),
        topology_origin="author",
        topology={
            "startNodeId": "opening",
            "nodes": [
                {"id": "opening", "kind": "start"},
                {"id": "choose", "kind": "decision"},
                {"id": "ending-a", "kind": "ending"},
                {"id": "ending-b", "kind": "ending"},
            ],
            "edges": [
                {
                    "id": key,
                    "sourceNodeId": source_id,
                    "targetNodeId": target,
                    "kind": kind,
                    "stateEffects": {},
                    "entityStateEffects": [],
                }
                for key, source_id, target, kind in [
                    ("to-choice", "opening", "choose", "continuation"),
                    ("beacon", "choose", "ending-a", "choice"),
                    ("dock", "choose", "ending-b", "choice"),
                ]
            ],
            "joins": [],
        },
        sections=[
            StorySection(
                section_id="opening",
                title="Opening",
                summary="Lin chooses.",
                footage_mode="footage",
            ),
            StorySection(
                section_id="choose",
                title="Choose",
                summary="Lin chooses a route.",
                footage_mode="route_only",
            ),
            StorySection(
                section_id="ending-a",
                title="Beacon",
                summary="Beacon.",
                ending=True,
                footage_mode="footage",
            ),
            StorySection(
                section_id="ending-b",
                title="Dock",
                summary="Dock.",
                ending=True,
                footage_mode="footage",
            ),
        ],
        choices=[
            SectionChoice(
                choice_id="choose",
                section_id="choose",
                prompt="Where?",
                outcomes=[
                    BranchOutcome(
                        outcome_id="beacon",
                        label="Beacon",
                        consequence="Beacon.",
                        ending_section_id="ending-a",
                    ),
                    BranchOutcome(
                        outcome_id="dock",
                        label="Dock",
                        consequence="Dock.",
                        ending_section_id="ending-b",
                    ),
                ],
            )
        ],
        join_reconciliations={},
    )
    if structure_factory is not None:
        mapping = structure_factory(store)
    state = store.save_section_map(
        graph_map_save_request(
            store,
            expected_section_map_revision=0,
            expected_source_revision=1,
            expected_outline_revision=1,
            expected_outline_content_hash=state.accepted_outline.content_hash,
            mapping=mapping,
        )
    )  # type: ignore[attr-defined]
    assert state.accepted_section_map
    store.install_section_map_graph(
        SectionMapGraphInstallRequest(
            expected_source_revision=1,
            expected_source_content_hash=state.source.content_hash,
            expected_outline_revision=1,
            expected_outline_content_hash=state.accepted_outline.content_hash,
            expected_section_map_revision=1,
            expected_section_map_content_hash=state.accepted_section_map.content_hash,
            expected_graph_revision=0,
            expected_graph_draft_revision=graph_draft_revision(store),
        )
    )  # type: ignore[attr-defined]
    _candidate, cast_request = store.prepare_cast_candidate(
        "ch_" + "c" * 32, render_style="realistic"
    )  # type: ignore[attr-defined]
    cast = style_fixture(
        {
            "source": "Tide Light",
            "summary": "Lin chooses.",
            "characters": [
                {
                    "id": "lin",
                    "name": "Lin",
                    "reviewNotes": {
                        "sourceNotes": "Rain coat is proposed",
                        "performanceGuidance": "",
                    },
                    "persona": {
                        "personality": ["Careful"],
                        "motivation": "Choose",
                        "appearance": "Rain coat",
                        "arc": "Acts",
                    },
                    "voice": {"timbre": "Calm"},
                }
            ],
        },
        cast_request.input_artifacts["cast-style-contract.json"],
    )
    ready_cast = store.admit_cast_delivery(
        _deliver_stage(store, cast_request, "cast.json", cast, "cast-fixture")
    )  # type: ignore[attr-defined]
    store.accept_cast_candidate(
        CastAcceptRequest(
            job_id=cast_request.job_id,
            expected_cast_revision=0,
            binding=ready_cast.binding,
            consumer_mappings=[
                CastConsumerMapping(
                    cast_character_id="lin", consumer_character_id="lin"
                )
            ],
        )
    )  # type: ignore[attr-defined]


def _prepare_art_context(store: object, structure_factory=None) -> ArtBinding:
    """Seed accepted Art prerequisites and retain the explicit cancel history."""
    _prepare_accepted_f4_cast_context(store, structure_factory)
    candidate, _request = store.prepare_art_candidate(
        "ch_" + "z" * 32, render_style="realistic"
    )  # type: ignore[attr-defined]
    store.cancel_art_candidate(candidate.job_id)  # type: ignore[attr-defined]
    return candidate.binding


def _pilot_script() -> dict[str, object]:
    """A valid tiny three-section F4 fixture, not a second graph representation."""

    def episode(number: int) -> dict[str, object]:
        return {
            "ep": number,
            "targetSeconds": 25,
            "hook": f"Section {number} begins in motion",
            "cliff": f"Section {number} leaves a consequence open",
            "hookBeat": [1, 1],
            "beatsClaimed": [],
            "scenes": [
                {
                    "sceneId": "S01",
                    "lighting": "dawn",
                    "characters": [],
                    "props": [],
                    "flow": [
                        {"action": f"Lin crosses the beacon room, action {index}."}
                        for index in range(10)
                    ],
                }
            ],
        }

    return {
        "source": "Tide Light",
        "sectionBindings": [
            {"sectionId": "opening", "episode": 1},
            {"sectionId": "ending-a", "episode": 2},
            {"sectionId": "ending-b", "episode": 3},
        ],
        "episodes": [episode(1), episode(2), episode(3)],
    }


def _accepted_f4_script(store: object, structure_factory=None) -> None:
    _prepare_accepted_f4_cast_context(store, structure_factory)
    art_candidate, art_request = store.prepare_art_candidate(
        "ch_" + "k" * 32, render_style="realistic"
    )  # type: ignore[attr-defined]
    binding = art_candidate.binding
    art_ready = store.admit_art_delivery(_deliver(store, art_request))  # type: ignore[attr-defined]
    store.accept_art_candidate(
        ArtAcceptRequest(
            job_id=art_candidate.job_id,
            expected_art_revision=0,
            binding=binding,
            art=art_ready.art,
        )
    )  # type: ignore[attr-defined]
    candidate, request = store.prepare_script_candidate("ch_" + "l" * 32)  # type: ignore[attr-defined]
    script = _pilot_script()
    if structure_factory is not None:
        from copy import deepcopy

        script["sectionBindings"] = [
            item.model_dump(mode="json", by_alias=True)
            for item in candidate.binding.section_bindings
        ]
        template = script["episodes"][0]
        script["episodes"] = [
            dict(deepcopy(template), ep=item.episode)
            for item in candidate.binding.section_bindings
        ]
    ready = store.admit_script_delivery(
        _deliver_stage(store, request, "script.json", script, "script-for-storyboard")
    )  # type: ignore[attr-defined]
    store.accept_script_candidate(
        ScriptAcceptRequest(
            job_id=candidate.job_id,
            expected_script_revision=0,
            binding=ready.binding,
            script=ready.script,
        )
    )  # type: ignore[attr-defined]
