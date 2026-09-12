"""Owned E2E-only entrypoint: injects an offline Wan port into FastAPI."""
from __future__ import annotations

import uvicorn

from plotloom.config import PlotloomSettings
from plotloom.offline_wan_fake import OfflineWanFake
from plotloom.runtime import build_runtime_app, select_available_port

settings = PlotloomSettings.from_env()
uvicorn.run(build_runtime_app(settings, test_video_provider=OfflineWanFake()), host=settings.host, port=select_available_port(settings.host, settings.port, settings.port_fallback_count))
