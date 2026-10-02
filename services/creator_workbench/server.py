"""Persistent composition of the existing local creator walkthrough."""

import os
from pathlib import Path

import uvicorn

from plotloom.api import create_project_folder_authoring_app
from plotloom.project_storage.composition import ProjectFolderStorage


def create_app():
    repository = Path(os.environ["PLOTLOOM_CHECKOUT"]).resolve()
    data = Path(os.environ["PLOTLOOM_CREATOR_DATA"]).resolve()
    for directory in (data / "outputs", data / "application"):
        if not directory.is_dir():
            raise RuntimeError(
                f"existing creator data directory is missing: {directory}"
            )
    storage = ProjectFolderStorage(
        outputs_root=data / "outputs",
        application_data_root=data / "application",
    )
    # Installation-local specialist settings and leases are already durable.
    # Both roles use the same codex CLI bridge supplied on the container PATH.
    app = create_project_folder_authoring_app(
        storage,
        video_provider=None,
        video_adapter=None,
        static_dir=repository / "src" / "plotloom" / "static",
    )

    @app.get("/healthz")
    def health():
        return {"status": "ok"}

    return app


if __name__ == "__main__":
    uvicorn.run(create_app(), host="0.0.0.0", port=8841)
