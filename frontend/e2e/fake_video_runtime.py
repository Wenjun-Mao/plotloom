"""E2E entrypoint for production composition with a typed offline H3 transport."""
from __future__ import annotations

from pathlib import Path
import sys

import uvicorn

from plotloom.config import PlotloomSettings
from plotloom.codex_image_dispatch import NativeCodexImageDispatcher
from plotloom.runtime import build_runtime_app, select_available_port
from plotloom.video_backends.minimax_h3 import MiniMaxH3GatewayAdapter


H3_FIXTURE_DIRECTORY = Path(__file__).parent / "video_backends" / "minimax_h3"
sys.path.insert(0, str(H3_FIXTURE_DIRECTORY))
from offline_gateway import OfflineH3GatewayFake  # noqa: E402

settings = PlotloomSettings.from_env()
uvicorn.run(
    build_runtime_app(
        settings,
        test_video_provider=OfflineH3GatewayFake(),
        test_video_adapter=MiniMaxH3GatewayAdapter(),
        test_image_dispatcher=NativeCodexImageDispatcher(
            "fixture-specialist",
            settings.application_data_dir / "fixture-native-image-dispatch",
            executable="/usr/bin/true",
        ),
    ),
    host=settings.host,
    port=select_available_port(settings.host, settings.port, settings.port_fallback_count),
)
