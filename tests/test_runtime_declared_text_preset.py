"""Declared startup presets are validated before installation writes."""

from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from plotloom.config import PlotloomSettings
from plotloom.runtime import build_runtime_app
from tests.test_production_project_folder_runtime import _RuntimeFakeH3


def _settings(root: Path, **overrides: object) -> PlotloomSettings:
    return PlotloomSettings(
        repo_root=root,
        outputs_dir=root / "outputs",
        application_data_dir=root / "application",
        static_dir=root / "static",
        text_auth_mode="none",
        **overrides,
    )


@pytest.mark.parametrize(
    ("overrides", "expected_preset"),
    [({}, "compatible_v1"),
     ({"text_preset_id": "custom", "text_attempt_timeout_seconds": 120}, "custom")],
)
def test_valid_declared_preset_is_retained(tmp_path, overrides, expected_preset):
    app = build_runtime_app(_settings(tmp_path, **overrides), test_video_provider=_RuntimeFakeH3())
    with TestClient(app):
        profile = app.state.application_profile_repository.get_text_provider_profile("default")
        assert profile.configuration.preset_id.value == expected_preset
        assert profile.configuration.text_attempt_timeout_seconds == overrides.get(
            "text_attempt_timeout_seconds", 300
        )


@pytest.mark.parametrize("overrides", [
    {"text_attempt_timeout_seconds": 120},
    {"text_preset_id": "custom", "text_reasoning_mode": "enabled"},
])
def test_invalid_declaration_fails_before_storage_keys_or_bootstrap(tmp_path, overrides):
    with (
        patch("plotloom.project_storage.ProjectFolderStorage") as storage,
        patch("plotloom.pipeline.RunSecretBroker") as secrets,
        patch("plotloom.project_storage.application_profiles.ApplicationProfileRepository.bootstrap_default_text_provider_profile") as bootstrap,
        pytest.raises(ValueError, match="TEXT_PRESET_ID=custom"),
    ):
        build_runtime_app(_settings(tmp_path, **overrides), test_video_provider=_RuntimeFakeH3())
    storage.assert_not_called()
    secrets.assert_not_called()
    bootstrap.assert_not_called()
    assert not (tmp_path / "outputs").exists()
    assert not (tmp_path / "application").exists()


def test_invalid_declaration_does_not_rewrite_retained_profiles(tmp_path):
    app = build_runtime_app(_settings(tmp_path), test_video_provider=_RuntimeFakeH3())
    with TestClient(app):
        before = app.state.application_profile_repository.get_text_provider_profile("default").model_dump()
    retained_files = {
        path.relative_to(tmp_path): path.read_bytes()
        for path in tmp_path.rglob("*") if path.is_file()
    }
    with pytest.raises(ValueError, match="Invalid declared text execution profile"):
        build_runtime_app(_settings(tmp_path, text_attempt_timeout_seconds=120), test_video_provider=_RuntimeFakeH3())
    assert retained_files == {
        path.relative_to(tmp_path): path.read_bytes()
        for path in tmp_path.rglob("*") if path.is_file()
    }
    assert app.state.application_profile_repository.get_text_provider_profile("default").model_dump() == before
