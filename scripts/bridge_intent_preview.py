"""Development-only retained F5 bridge preview with a labelled fake text transport.

Run from the checkout with `uv run python -m scripts.bridge_intent_preview`.
This script never contacts a model provider and never touches the U4 lighthouse
project. It reopens the first project in its own isolated root on restart.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import uvicorn

from plotloom.config import PlotloomSettings
from plotloom.runtime import build_runtime_app
from tests.test_production_bridge_intent import FakeAdapter, FakeResolver, _pending_project


class PreviewFakeAdapter(FakeAdapter):
    """The first attempt is known-not-sent; a deliberate retry succeeds."""

    def generate(self, request: Any, secret: Any):
        self.mode = "not_sent" if self.calls == 0 else "success"
        return super().generate(request, secret)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(".local/relay/bridge-intent-preview"))
    parser.add_argument("--port", type=int, default=8810)
    args = parser.parse_args()
    root = args.root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    if not (root / "outputs").exists() or not any((root / "outputs").iterdir()):
        storage, project_id, _revision, _digest = _pending_project(root)
        del storage
    else:
        from plotloom.project_storage.composition import ProjectFolderStorage
        storage = ProjectFolderStorage(outputs_root=root / "outputs", application_data_root=root / "application")
        homes = storage.projects.discover()
        if not homes:
            raise RuntimeError("preview root has no discoverable project; inspect it before creating a new one")
        project_id = homes[0].manifest.project_id
    settings = PlotloomSettings(
        repo_root=Path(__file__).resolve().parents[1],
        outputs_dir=root / "outputs", application_data_dir=root / "application",
        static_dir=Path(__file__).resolve().parents[1] / "src/plotloom/static",
        text_provider="deterministic_fake", text_base_url="http://127.0.0.1:9",
        text_model="bridge_fixture", text_auth_mode="none", text_supports_json_schema=True,
        host="127.0.0.1", port=args.port,
    )
    app = build_runtime_app(settings, text_provider_resolver=FakeResolver(PreviewFakeAdapter()))
    print(f"DETERMINISTIC FAKE TEXT TRANSPORT — no provider calls. Project: {project_id}", flush=True)
    print(f"Preview: http://127.0.0.1:{args.port}/v2/?project={project_id}&stage=source#storyboard-review", flush=True)
    uvicorn.run(app, host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
