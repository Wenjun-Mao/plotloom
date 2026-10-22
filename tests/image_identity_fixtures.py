"""Reusable synthetic identity-review fixtures for collected tests."""

import json
from io import BytesIO

from PIL import Image

from plotloom.canonical_schema import CharacterV2
from plotloom.domain import RunStatus
from plotloom.project_generation_storage import ProjectPipelineExecutor
from plotloom.project_storage import ProjectStore
from tests.project_storage_fixtures import (
    FixtureProvider,
    FixtureResolver,
    fixture_profile,
)


def png(color: tuple[int, int, int]) -> bytes:
    output = BytesIO()
    Image.new("RGB", (24, 16), color).save(output, format="PNG")
    return output.getvalue()


def install_visible_fixture_character(store: ProjectStore) -> None:
    """Make the fixture's first shot require one explicit identity decision."""

    hero = CharacterV2(
        id="fixture-hero",
        name="Fixture hero",
        role="lead",
        description="A deterministic identity-reference fixture.",
        visual_anchors=["red coat"],
        sound_anchors=[],
        allowed_states=["alert"],
        continuity_rules=["The red coat remains visible."],
        goal="Keep the fixture coherent.",
        traits=["steady"],
        voice_anchors=[],
    )

    class VisibleCharacterProvider(FixtureProvider):
        def generate(self, request, secret):
            response = super().generate(request, secret)
            payload = json.loads(response.raw["choices"][0]["message"]["content"])
            if "characters" in payload:
                payload["characters"] = [hero.model_dump(mode="json", by_alias=True)]
            for scene in payload.get("scenes", []):
                scene["characterIds"] = [hero.id]
            for shot in payload.get("shots", []):
                shot["characterIds"] = [hero.id]
            return response.model_copy(
                update={
                    "raw": {
                        "choices": [
                            {
                                "message": {
                                    "role": "assistant",
                                    "content": json.dumps(payload),
                                }
                            }
                        ],
                    }
                }
            )

    resolver = FixtureResolver()
    resolver.provider = VisibleCharacterProvider()
    completed = ProjectPipelineExecutor(resolver).execute(
        store, profile=fixture_profile()
    )
    assert completed.status == RunStatus.SUCCEEDED
