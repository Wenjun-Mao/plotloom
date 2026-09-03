from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from plotloom.api import create_app
from plotloom.domain import ProjectBrief, RunKind, StageName
from plotloom.exceptions import InvalidTransitionError, RevisionConflictError
from plotloom.persistence import SQLiteRepository
from plotloom.provider_profiles import (
    PresetId,
    StageMaxOutputTokens,
    TextProviderProfileSnapshot,
)


def _profile(profile_id: str = "default", *, model: str = "model-a") -> TextProviderProfileSnapshot:
    return TextProviderProfileSnapshot.model_validate(
        {
            "profileSchemaVersion": 2,
            "profileId": profile_id,
            "profileVersion": 0,
            "textProvider": "openai-compatible",
            "textBaseUrl": "http://127.0.0.1:8080/v1",
            "textModel": model,
            "textAuthMode": "none",
            "textContextWindowTokens": 32768,
            "textMaxOutputTokens": 8192,
            "textAttemptTimeoutSeconds": 300,
            "stageMaxOutputTokens": StageMaxOutputTokens(
                story_bible=8192,
                story_graph=8192,
                scene_beats=4096,
                storyboard=4096,
            ),
            "presetId": PresetId.COMPATIBLE_V1,
        }
    )


def _bootstrapped_repository() -> SQLiteRepository:
    repository = SQLiteRepository("sqlite://")
    repository.bootstrap_default_text_provider_profile(_profile())
    return repository


def test_profile_control_plane_crud_selection_revision_and_run_snapshot_isolation() -> None:
    repository = _bootstrapped_repository()
    try:
        default = repository.get_text_provider_profile("default")
        assert default.configuration.profile_id == "default"
        assert default.configuration.text_model == "model-a"
        assert repository.get_provider_profile_selection().active_profile_id == "default"

        created = repository.create_text_provider_profile(
            "quality",
            "Quality",
            copy_from_profile_id="default",
        )
        assert created.revision == 1
        assert created.configuration.profile_id == "quality"
        assert created.configuration.profile_version == 1

        updated = repository.update_text_provider_profile(
            "quality",
            created.revision,
            display_name="Quality Qwen",
            configuration=_profile("quality", model="model-b"),
        )
        assert updated.revision == 2
        assert updated.configuration.text_model == "model-b"
        with pytest.raises(RevisionConflictError):
            repository.update_text_provider_profile(
                "quality",
                created.revision,
                display_name="Stale",
                configuration=_profile("quality", model="model-c"),
            )

        selection = repository.get_provider_profile_selection()
        selected = repository.activate_text_provider_profile("quality", selection.revision)
        assert selected.active_profile_id == "quality"
        assert selected.revision == selection.revision + 1
        with pytest.raises(RevisionConflictError):
            repository.activate_text_provider_profile("default", selection.revision)

        project = repository.create_project(
            ProjectBrief(title="隔离", synopsis="一个可靠的生成闭环。")
        )
        run = repository.create_run(
            project.id,
            RunKind.PIPELINE,
            [StageName.STORY_BIBLE],
            provider_snapshot=updated.configuration.model_dump(mode="json", by_alias=True),
        )
        frozen = repository.get_run(run.id).provider_snapshot
        assert frozen["profileId"] == "quality"
        assert frozen["textModel"] == "model-b"

        newer = repository.update_text_provider_profile(
            "quality",
            updated.revision,
            display_name="Quality Qwen",
            configuration=_profile("quality", model="model-c"),
        )
        assert newer.configuration.text_model == "model-c"
        assert repository.get_run(run.id).provider_snapshot == frozen

        with pytest.raises(InvalidTransitionError, match="active"):
            repository.delete_text_provider_profile("quality", newer.revision)
        with pytest.raises(InvalidTransitionError, match="default"):
            repository.delete_text_provider_profile("default", default.revision)

        active = repository.get_provider_profile_selection()
        repository.activate_text_provider_profile("default", active.revision)
        with pytest.raises(InvalidTransitionError, match="non-terminal"):
            repository.delete_text_provider_profile("quality", newer.revision)
    finally:
        repository.close()


def test_profile_configuration_never_accepts_secret_shaped_values() -> None:
    repository = _bootstrapped_repository()
    try:
        raw = _profile("unsafe").model_dump(mode="json", by_alias=True)
        raw["apiKey"] = "not-allowed"
        with pytest.raises(ValueError, match="secrets"):
            repository.create_text_provider_profile("unsafe", "Unsafe", configuration=raw)
    finally:
        repository.close()


def test_profile_api_is_secret_free_and_pipeline_honors_requested_profile() -> None:
    repository = SQLiteRepository("sqlite://")
    try:
        app = create_app(
            repository,
            text_profile_default=_profile(),
            profile_key_available=lambda profile_id: profile_id == "quality",
        )
        client = TestClient(app)
        baseline = client.get("/api/v2/text-provider-profiles")
        assert baseline.status_code == 200
        data = baseline.json()
        assert data["activeProfileId"] == "default"
        assert data["profiles"][0]["serverKeyAvailable"] is False
        assert "apiKey" not in str(data).lower()

        default_config = data["profiles"][0]["configuration"]
        created = client.post(
            "/api/v2/text-provider-profiles",
            json={
                "profileId": "quality",
                "displayName": "Quality",
                "configuration": {**default_config, "textModel": "model-quality"},
            },
        )
        assert created.status_code == 201
        assert created.json()["serverKeyAvailable"] is True

        stale = client.post(
            "/api/v2/text-provider-profiles/quality/activate",
            json={"expectedSelectionRevision": 99},
        )
        assert stale.status_code == 409
        activation = client.post(
            "/api/v2/text-provider-profiles/quality/activate",
            json={"expectedSelectionRevision": 0},
        )
        assert activation.status_code == 200

        project = client.post(
            "/api/v2/projects",
            json={"brief": {"title": "选择", "synopsis": "主角在两条路之间选择。"}},
        ).json()
        run = client.post(
            f"/api/v2/projects/{project['id']}/pipeline-runs",
            json={"stages": ["story_bible"], "providerProfileId": "quality"},
        )
        assert run.status_code == 202
        assert run.json()["providerSnapshot"]["profileId"] == "quality"
        assert run.json()["providerSnapshot"]["textModel"] == "model-quality"
    finally:
        repository.close()
