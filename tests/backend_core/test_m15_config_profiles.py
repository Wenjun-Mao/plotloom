from __future__ import annotations

from pathlib import Path

import pytest

from plotloom.config import PlotloomSettings, resolve_text_provider_api_key
from plotloom.domain import ProviderAuthMode
from plotloom.generation.exceptions import SecretLeaseError
from plotloom.pipeline import RunSecretBroker


def test_repo_root_dotenv_is_non_overriding_and_profile_keys_do_not_cross(monkeypatch, tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'fixture'\n", encoding="utf-8")
    (tmp_path / ".env").write_text(
        "TEXT_MODEL=dotenv-model\n"
        "TEXT_MODEL_API_KEY=dotenv-default\n"
        "PLOTLOOM_PROFILE_QUALITY_TEXT_API_KEY=dotenv-quality\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("TEXT_MODEL", "host-model")
    monkeypatch.setenv("PLOTLOOM_PROFILE_QUALITY_TEXT_API_KEY", "host-quality")
    monkeypatch.delenv("TEXT_MODEL_API_KEY", raising=False)
    monkeypatch.delenv("ATLASCLOUD_API_KEY", raising=False)
    monkeypatch.delenv("PLOTLOOM_PROFILE_OTHER_TEXT_API_KEY", raising=False)

    settings = PlotloomSettings.from_env(tmp_path)

    assert settings.text_model == "host-model"
    assert resolve_text_provider_api_key("default") == "dotenv-default"
    assert resolve_text_provider_api_key("quality") == "host-quality"
    assert resolve_text_provider_api_key("other") is None


def test_session_override_is_scoped_to_one_profile_and_auth_none_never_leases_a_key() -> None:
    broker = RunSecretBroker(server_profile_keys={"default": "default-server", "quality": "quality-server"})
    broker.register_run_override("run-1", "quality-session", profile_id="quality")
    override = broker.lease_for_run("run-1", profile_id="quality")
    assert override is not None
    with override.reveal() as value:
        assert value == "quality-session"
    with pytest.raises(SecretLeaseError, match="different provider profile"):
        broker.lease_for_run("run-1", profile_id="default")

    server = broker.lease_for_run("run-2", profile_id="default")
    assert server is not None
    with server.reveal() as value:
        assert value == "default-server"
    assert broker.lease_for_run(
        "run-3", profile_id="quality", auth_mode=ProviderAuthMode.NONE
    ) is None
    broker.release_run("run-1")
    broker.close()
