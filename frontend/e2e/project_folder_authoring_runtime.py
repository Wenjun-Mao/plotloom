"""E2E-only FastAPI entrypoint for the unwired project-folder authoring slice."""
from __future__ import annotations

import os
from pathlib import Path
import sys

import uvicorn

from plotloom.api import create_project_folder_authoring_app
from plotloom.project_storage import ProjectFolderStorage
from plotloom.video_backends.minimax_h3 import MiniMaxH3GatewayAdapter


H3_FIXTURE_DIRECTORY = Path(__file__).parent / "video_backends" / "minimax_h3"
sys.path.insert(0, str(H3_FIXTURE_DIRECTORY))
from offline_gateway import OfflineH3GatewayFake  # noqa: E402


outputs_root = Path(os.environ["PLOTLOOM_E2E_OUTPUTS_DIR"])
application_root = Path(os.environ["PLOTLOOM_E2E_APPLICATION_DATA_DIR"])
app = create_project_folder_authoring_app(
    ProjectFolderStorage(
        outputs_root=outputs_root,
        application_data_root=application_root,
    ),
    video_provider=OfflineH3GatewayFake(),
    video_adapter=MiniMaxH3GatewayAdapter(),
)

uvicorn.run(
    app,
    host=os.environ.get("PLOTLOOM_HOST", "127.0.0.1"),
    port=int(os.environ["PLOTLOOM_PORT"]),
)
