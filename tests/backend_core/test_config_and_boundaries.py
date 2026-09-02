from __future__ import annotations

import ast
import os
import socket
import sys
from pathlib import Path

from fastapi.testclient import TestClient

import plotloom.config as config_module
from plotloom.config import PlotloomSettings
from plotloom.runtime import build_runtime_app, select_available_port


def test_root_dotenv_and_host_port_precedence(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='standalone-v2'\n", encoding="utf-8")
    (tmp_path / ".env").write_text(
        "PLOTLOOM_DATA_DIR=dotenv-data\nPLOTLOOM_PORT=8790\nPORT=8791\n",
        encoding="utf-8",
    )
    for name in ("PLOTLOOM_DATA_DIR", "PLOTLOOM_PORT", "PORT"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("PORT", "8899")
    settings = PlotloomSettings.from_env(tmp_path)
    assert settings.port == 8899
    assert settings.port_fallback_count == 0
    assert settings.run_workers == 1
    assert settings.data_dir == (tmp_path / "dotenv-data").resolve()
    assert settings.database_url.endswith("/dotenv-data/plotloom.sqlite3")
    assert settings.artifact_root == (tmp_path / "dotenv-data" / "artifacts").resolve()
    assert settings.static_dir == (Path(__file__).resolve().parents[2] / "src/plotloom/static").resolve()


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
    assert settings.data_dir == expected.resolve()
    assert settings.artifact_root == (expected / "artifacts").resolve()
    assert settings.text_model != "cwd-poison-model"
    assert not settings.data_dir.is_relative_to(unrelated)
    assert not settings.data_dir.is_relative_to(Path(config_module.__file__).resolve().parent)


def test_local_port_falls_forward(monkeypatch) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as occupied:
        occupied.bind(("127.0.0.1", 0))
        port = occupied.getsockname()[1]
        assert select_available_port("127.0.0.1", port, 19) == port + 1


def test_runtime_wires_text_and_media_workers_without_exposing_keys(tmp_path: Path) -> None:
    static_dir = tmp_path / "static"
    static_dir.mkdir()
    (static_dir / "index.html").write_text("<h1>Plotloom</h1>", encoding="utf-8")
    settings = PlotloomSettings(
        repo_root=tmp_path,
        data_dir=tmp_path / "data",
        database_url=f"sqlite:///{tmp_path / 'data' / 'state.sqlite3'}",
        artifact_root=tmp_path / "data" / "artifacts",
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
    assert hasattr(app.state, "media_runner")


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
