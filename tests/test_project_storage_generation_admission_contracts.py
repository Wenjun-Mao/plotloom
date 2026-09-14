"""HTTP admission regressions owned by the project-folder runtime."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from plotloom.config import PlotloomSettings
from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.runtime import build_runtime_app

from tests.project_storage_fixtures import fixture_profile


class _UnreachableAdapter:
    """A non-generative probe that must reject admission before a run exists."""

    def check_readiness(self, _model: str, _lease: object) -> object:
        raise OSError("offline fixture transport is unavailable")


class _UnreachableResolver:
    def resolve(self, _snapshot: dict[str, object]) -> tuple[_UnreachableAdapter, str]:
        return _UnreachableAdapter(), "fixture-model"


def _settings(tmp_path: Path) -> PlotloomSettings:
    static = tmp_path / "static"
    static.mkdir()
    (static / "index.html").write_text("<main>Plotloom</main>", encoding="utf-8")
    return PlotloomSettings(
        repo_root=tmp_path,
        outputs_dir=tmp_path / "outputs",
        application_data_dir=tmp_path / "application",
        static_dir=static,
        text_auth_mode="none",
    )


def _activate_profile(client: TestClient) -> None:
    catalog = client.get("/api/v2/text-provider-profiles")
    profile = fixture_profile().model_dump(mode="json", by_alias=True)
    created = client.post(
        "/api/v2/text-provider-profiles",
        json={
            "profileId": profile["profileId"],
            "displayName": "Unreachable offline fixture",
            "configuration": profile,
        },
    )
    assert created.status_code == 201, created.text
    activated = client.post(
        f"/api/v2/text-provider-profiles/{profile['profileId']}/activate",
        json={"expectedSelectionRevision": catalog.json()["selectionRevision"]},
    )
    assert activated.status_code == 200, activated.text


def test_unreachable_text_provider_returns_422_before_creating_a_project_run(
    tmp_path: Path,
) -> None:
    """A probe failure is admission failure, never a quarantined placeholder run."""

    app = build_runtime_app(
        _settings(tmp_path), text_provider_resolver=_UnreachableResolver()
    )
    with TestClient(app) as client:
        _activate_profile(client)
        project = client.post(
            "/api/v2/projects",
            json={"brief": FIXED_CHINESE_BRIEF.model_dump(mode="json", by_alias=True)},
        )
        assert project.status_code == 201, project.text
        project_id = project.json()["id"]

        refused = client.post(
            f"/api/v2/projects/{project_id}/pipeline-runs",
            json={"stages": ["story_bible"]},
        )

        assert refused.status_code == 422
        assert "selected text backend is unreachable" in refused.json()["detail"]
        assert client.get(f"/api/v2/projects/{project_id}/runs").json()["runs"] == []
