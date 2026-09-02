from __future__ import annotations

import re
from pathlib import Path

from fastapi.routing import APIRoute

from plotloom.api import create_app


ROOT = Path(__file__).resolve().parents[2]
TYPES_SOURCE = ROOT / "frontend" / "src" / "types.ts"


def _typescript_interface(name: str) -> tuple[set[str], dict[str, str]]:
    source = TYPES_SOURCE.read_text(encoding="utf-8")
    match = re.search(
        rf"export interface {re.escape(name)}(?:<[^>]+>)?\s*\{{(.*?)\n\}}",
        source,
        re.S,
    )
    assert match is not None, f"missing TypeScript interface {name}"
    declarations: dict[str, str] = {}
    for field, optional, annotation in re.findall(
        r"^\s{2}([A-Za-z][A-Za-z0-9]*)(\?)?:\s*([^;]+);",
        match.group(1),
        re.M,
    ):
        assert optional == "", f"response DTO field {name}.{field} must not be optional"
        declarations[field] = annotation.strip()
    return set(declarations), declarations


def test_handwritten_response_dtos_match_openapi_fields_and_nullability() -> None:
    app = create_app()
    try:
        schemas = app.openapi()["components"]["schemas"]
        response_routes = [
            route
            for route in app.routes
            if isinstance(route, APIRoute)
            and route.path.startswith("/api/v2")
            and route.response_model is not None
        ]
        assert response_routes
        # FastAPI includes model defaults and explicit nulls in these responses.
        # Therefore every OpenAPI property—not only the input-side `required`
        # subset—must be a non-optional TypeScript response field.
        assert all(not route.response_model_exclude_unset for route in response_routes)
        assert all(not route.response_model_exclude_defaults for route in response_routes)
        assert all(not route.response_model_exclude_none for route in response_routes)
    finally:
        app.state.repository.close()

    response_dtos = {
        "ProjectBrief": "ProjectBrief",
        "Character": "CharacterCard",
        "Location": "LocationCard",
        "Prop": "PropCard",
        "StoryBible": "StoryBible",
        "StoryNode": "StoryNode",
        "StoryEdge": "StoryEdge",
        "JoinContract": "JoinContract",
        "StoryGraph": "StoryGraph",
        "ContinuityState": "ContinuityState",
        "DramaticScene": "DramaticScene",
        "Beat": "Beat",
        "SceneBeatPlan": "SceneBeatPlan",
        "Shot": "Shot",
        "ShotBeatLink": "ShotBeatLink",
        "Storyboard": "Storyboard",
        "Project": "ProjectResource",
        "StageHead": "StageHead",
        "StageEnvelope": "StageEnvelope",
        "StageEnvelopesResponse": "StageEnvelopesResponse",
        "CanonicalSnapshot": "CanonicalSnapshot",
        "RepairSource": "RepairSource",
        "GenerationRun": "PipelineRun",
        "GenerationAttempt": "GenerationAttempt",
        "Artifact": "RunArtifact",
        "RunTrace": "RunTrace",
        "ProjectRunsResponse": "ProjectRunsResponse",
        "MediaTask": "MediaTask",
        "ProjectMediaTasksResponse": "ProjectMediaTasksResponse",
        "ProviderSettings": "ProviderSettings",
    }

    for schema_name, interface_name in response_dtos.items():
        fields, declarations = _typescript_interface(interface_name)
        properties = schemas[schema_name]["properties"]
        assert fields == set(properties), (
            f"{interface_name} fields drifted from FastAPI schema {schema_name}"
        )
        for field, schema in properties.items():
            variants = schema.get("anyOf", [])
            backend_nullable = any(item.get("type") == "null" for item in variants)
            frontend_nullable = any(
                variant.strip() == "null" for variant in declarations[field].split("|")
            )
            assert frontend_nullable == backend_nullable, (
                f"{interface_name}.{field} nullability drifted: "
                f"OpenAPI nullable={backend_nullable}, TypeScript={declarations[field]}"
            )
