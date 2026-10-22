"""Build ownership checks; actual installed-artifact execution lives in tools/packaging."""
from pathlib import Path

import pytest
import tomllib
import yaml

SERVICE = Path(__file__).resolve().parents[3] / "services/minimax_h3_gateway"


@pytest.mark.parametrize("dockerfile", ["Dockerfile", "dashboard.Dockerfile"])
def test_images_install_noneditable_from_service_lock(dockerfile):
    source = (SERVICE / dockerfile).read_text()
    assert "COPY pyproject.toml uv.lock" in source
    assert "uv sync --locked --no-dev" in source
    assert "--no-editable" in source
    assert "PYTHONPATH" not in source
    assert "services/minimax_h3_gateway" not in source
    assert "pip install" not in source


@pytest.mark.parametrize("compose,role", [("docker-compose.yml", "gateway"),
                                         ("dashboard-compose.yml", "dashboard")])
def test_build_context_contains_only_the_service(compose, role):
    config = yaml.safe_load((SERVICE / compose).read_text())
    assert config["services"][role]["build"]["context"] == "."
    assert "!src/**" in (SERVICE / ".dockerignore").read_text()


def test_manifest_has_independent_entrypoints_and_no_inference_dependencies():
    manifest = tomllib.loads((SERVICE / "pyproject.toml").read_text())
    assert set(manifest["project"]["scripts"]) == {"plotloom-h3-gateway", "plotloom-h3-dashboard"}
    assert manifest["project"]["optional-dependencies"] == {"gateway": ["pillow==11.3.0"]}
    lock = tomllib.loads((SERVICE / "uv.lock").read_text())
    names = {package["name"] for package in lock["package"]}
    assert not names & {"plotloom", "plotloom-voice-lab", "torch", "transformers", "sglang",
                        "sqlalchemy", "alembic", "jinja2"}
