from __future__ import annotations

from fastapi.testclient import TestClient

from plotloom.config import PlotloomSettings
from plotloom import runtime


def test_runtime_lifespan_performs_reconciliation_before_serving(
    tmp_path,
) -> None:
    settings = PlotloomSettings(
        repo_root=tmp_path,
        outputs_dir=tmp_path / "outputs",
        application_data_dir=tmp_path / "application",
        static_dir=tmp_path / "static",
        text_auth_mode="none",
    )
    app = runtime.build_runtime_app(settings)

    with TestClient(app):
        assert app.state.startup_recovery == {}
        assert app.state.project_folder_storage.projects.outputs_root == (
            tmp_path / "outputs"
        ).resolve()
