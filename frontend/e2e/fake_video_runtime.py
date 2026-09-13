"""Owned E2E-only entrypoint: injects one offline video adapter into FastAPI."""
from __future__ import annotations

import os
from pathlib import Path
import sys

import uvicorn

from plotloom.config import PlotloomSettings
from plotloom.offline_wan_fake import OfflineWanFake
from plotloom.runtime import build_runtime_app, select_available_port
from plotloom.video_backends.minimax_h3 import MiniMaxH3GatewayAdapter


H3_FIXTURE_DIRECTORY = Path(__file__).parent / "video_backends" / "minimax_h3"
sys.path.insert(0, str(H3_FIXTURE_DIRECTORY))
from offline_gateway import OfflineH3GatewayFake  # noqa: E402

settings = PlotloomSettings.from_env()
mode = os.environ.get("PLOTLOOM_E2E_VIDEO_ADAPTER", "wan")
if mode == "wan":
    provider, adapter = OfflineWanFake(), None
elif mode == "h3":
    provider, adapter = OfflineH3GatewayFake(), MiniMaxH3GatewayAdapter()
else:
    raise RuntimeError("PLOTLOOM_E2E_VIDEO_ADAPTER must be wan or h3")
uvicorn.run(
    build_runtime_app(settings, test_video_provider=provider, test_video_adapter=adapter),
    host=settings.host,
    port=select_available_port(settings.host, settings.port, settings.port_fallback_count),
)
