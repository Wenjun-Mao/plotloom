from __future__ import annotations

import ast
import os
import socket
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import plotloom.config as config_module
from plotloom.config import PlotloomSettings
from plotloom.runtime import build_runtime_app, select_available_port
from plotloom.video_backends.minimax_h3 import MiniMaxH3GatewayAdapter


def test_root_dotenv_and_host_port_precedence(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='standalone-v2'\n", encoding="utf-8")
    (tmp_path / ".env").write_text(
        "PLOTLOOM_OUTPUTS_DIR=dotenv-outputs\nPLOTLOOM_APPLICATION_DATA_DIR=dotenv-application\nPLOTLOOM_PORT=8790\nPORT=8791\n"
        "TEXT_BASE_URL=http://127.0.0.1:8080/v1\nTEXT_AUTH_MODE=none\n"
        "TEXT_MAX_OUTPUT_TOKENS=4096\nTEXT_CONNECT_TIMEOUT_SECONDS=4\n"
        "PLOTLOOM_MANAGED_MEDIA_MAX_IMPORT_BYTES=9000000\n"
        "PLOTLOOM_MANAGED_MEDIA_MAX_IMPORT_PIXELS=25000000\n",
        encoding="utf-8",
    )
    for name in (
        "PLOTLOOM_OUTPUTS_DIR", "PLOTLOOM_APPLICATION_DATA_DIR", "PLOTLOOM_PORT", "PORT", "TEXT_BASE_URL",
        "TEXT_AUTH_MODE", "TEXT_MAX_OUTPUT_TOKENS", "TEXT_CONNECT_TIMEOUT_SECONDS",
        "PLOTLOOM_MANAGED_MEDIA_MAX_IMPORT_BYTES", "PLOTLOOM_MANAGED_MEDIA_MAX_IMPORT_PIXELS",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("PORT", "8899")
    monkeypatch.setenv("TEXT_MAX_OUTPUT_TOKENS", "2048")
    settings = PlotloomSettings.from_env(tmp_path)
    assert settings.port == 8899
    assert settings.port_fallback_count == 0
    assert settings.run_workers == 1
    assert settings.outputs_dir == (tmp_path / "dotenv-outputs").resolve()
    assert settings.application_data_dir == (tmp_path / "dotenv-application").resolve()
    assert settings.static_dir == (Path(__file__).resolve().parents[2] / "src/plotloom/static").resolve()
    assert settings.text_base_url == "http://127.0.0.1:8080/v1"
    assert settings.text_auth_mode == "none"
    assert settings.text_max_output_tokens == 2048
    assert settings.text_connect_timeout_seconds == 4
    assert settings.managed_media_max_import_bytes == 9_000_000
    assert settings.managed_media_max_import_pixels == 25_000_000


def test_installed_runtime_ignores_cwd_dotenv_and_uses_user_data_home(
    tmp_path: Path, monkeypatch
) -> None:
    unrelated = tmp_path / "unrelated-project"
    unrelated.mkdir()
    (unrelated / "pyproject.toml").write_text("[project]\nname='not-plotloom'\n")
    (unrelated / ".env").write_text(
        "PLOTLOOM_DATA_DIR=poison-data\nTEXT_MODEL=cwd-poison-model\n",
        encoding="utf-8",
    )
    user_home = tmp_path / "user-home"
    xdg_home = user_home / "xdg-data"
    monkeypatch.chdir(unrelated)
    monkeypatch.setattr(config_module, "_source_checkout_root", lambda: None)
    monkeypatch.setenv("HOME", str(user_home))
    monkeypatch.setenv("XDG_DATA_HOME", str(xdg_home))
    for name in (
        "PLOTLOOM_DATA_DIR",
        "PLOTLOOM_DATABASE_URL",
        "PLOTLOOM_ARTIFACT_ROOT",
        "PLOTLOOM_LEGACY_ARTIFACT_ROOTS",
        "PLOTLOOM_IMAGE_EXCHANGE_ROOT",
        "PLOTLOOM_ENABLE_WAN_P2",
        "PLOTLOOM_OUTPUTS_DIR",
        "PLOTLOOM_APPLICATION_DATA_DIR",
        "TEXT_MODEL",
    ):
        monkeypatch.delenv(name, raising=False)

    settings = PlotloomSettings.from_env()

    if sys.platform == "darwin":
        expected = user_home / "Library" / "Application Support" / "Plotloom"
    elif os.name == "nt":
        expected = user_home / "AppData" / "Local" / "Plotloom"
    else:
        expected = xdg_home / "plotloom"
    assert settings.repo_root == expected.resolve()
    assert settings.outputs_dir == (expected / "outputs").resolve()
    assert settings.application_data_dir == (expected / "data").resolve()
    assert settings.text_model != "cwd-poison-model"
    assert not settings.outputs_dir.is_relative_to(unrelated)
    assert not settings.application_data_dir.is_relative_to(Path(config_module.__file__).resolve().parent)


def test_obsolete_shared_storage_configuration_is_rejected_before_startup(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("PLOTLOOM_DATABASE_URL", "sqlite:///retained.sqlite3")
    with pytest.raises(ValueError, match="obsolete shared-storage configuration"):
        PlotloomSettings.from_env(tmp_path)


def test_local_port_falls_forward(monkeypatch) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as occupied:
        occupied.bind(("127.0.0.1", 0))
        port = occupied.getsockname()[1]
        assert select_available_port("127.0.0.1", port, 19) == port + 1


def test_local_port_probe_uses_restart_safe_reuseaddr(monkeypatch) -> None:
    calls: list[tuple[int, int, int]] = []

    class ProbeSocket:
        def __enter__(self) -> "ProbeSocket":
            return self

        def __exit__(self, *_: object) -> None:
            return None

        def setsockopt(self, level: int, option: int, value: int) -> None:
            calls.append((level, option, value))

        def bind(self, address: tuple[str, int]) -> None:
            assert address == ("127.0.0.1", 8775)

    monkeypatch.setattr(socket, "socket", lambda *_: ProbeSocket())

    assert select_available_port("127.0.0.1", 8775, 0) == 8775
    assert calls == [(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)]


def test_runtime_wires_text_and_media_workers_without_exposing_keys(tmp_path: Path) -> None:
    static_dir = tmp_path / "static"
    static_dir.mkdir()
    (static_dir / "index.html").write_text("<h1>Plotloom</h1>", encoding="utf-8")
    settings = PlotloomSettings(
        repo_root=tmp_path,
        outputs_dir=tmp_path / "outputs",
        application_data_dir=tmp_path / "application",
        static_dir=static_dir,
        text_api_key="server-text-secret",
        image_api_key="server-image-secret",
    )
    app = build_runtime_app(settings)

    with TestClient(app) as client:
        response = client.get("/api/v2/provider-settings")
        assert response.status_code == 200
        body = response.json()
        assert body["textKeyAvailable"] is True
        assert body["imageKeyAvailable"] is True
        assert body["videoKeyAvailable"] is False
        assert "server-text-secret" not in response.text
        assert "server-image-secret" not in response.text
        assert client.get("/v2/").status_code == 200

    assert hasattr(app.state, "run_runner")
    assert hasattr(app.state, "project_folder_storage")


def test_runtime_exposes_only_the_trusted_h3_capability_without_its_key(tmp_path: Path) -> None:
    static_dir = tmp_path / "static"
    static_dir.mkdir()
    (static_dir / "index.html").write_text("<h1>Plotloom</h1>", encoding="utf-8")
    settings = PlotloomSettings(
        repo_root=tmp_path,
        outputs_dir=tmp_path / "outputs",
        application_data_dir=tmp_path / "application",
        static_dir=static_dir,
        h3_gateway_enabled=True,
        video_provider="minimax_h3_gateway",
        video_base_url="http://100.64.1.2:8090",
        video_model="minimax_h3_gateway_catalog_v3",
        video_api_key="h3-server-only-secret",
    )
    app = build_runtime_app(settings)

    with TestClient(app) as client:
        response = client.get("/api/v2/video-backend")
        assert response.status_code == 200
        assert response.json() == MiniMaxH3GatewayAdapter().public_capability()
        assert "h3-server-only-secret" not in response.text


def test_runtime_rejects_h3_profile_drift_before_serving(tmp_path: Path) -> None:
    settings = PlotloomSettings(
        repo_root=tmp_path,
        outputs_dir=tmp_path / "outputs",
        application_data_dir=tmp_path / "application",
        static_dir=tmp_path,
        h3_gateway_enabled=True,
        video_provider="minimax_h3_gateway",
        video_base_url="http://100.64.1.2:8090",
        video_model="unreviewed-model",
        video_api_key="h3-server-only-secret",
    )
    with pytest.raises(RuntimeError, match="trusted MiniMax H3 catalog"):
        build_runtime_app(settings)


def test_plotloom_has_no_legacy_imports() -> None:
    package_root = Path(__file__).resolve().parents[2] / "src" / "plotloom"
    forbidden_roots = {"app", "backend", "narrative_forge", "static"}
    violations: list[str] = []
    for path in package_root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            imported: list[str] = []
            if isinstance(node, ast.Import):
                imported = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                imported = [node.module]
            for module in imported:
                if module.split(".", 1)[0] in forbidden_roots:
                    violations.append(f"{path.name}: {module}")
    assert violations == []
