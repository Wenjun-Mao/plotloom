"""Run the private MiniMax-H3 gateway."""
from __future__ import annotations

import os

import uvicorn

from .app import GatewaySettings, create_app


def main() -> None:
    settings = GatewaySettings.from_environment()
    uvicorn.run(
        create_app(settings),
        host=os.environ.get("H3_BIND_ADDRESS", "127.0.0.1"),
        port=int(os.environ.get("H3_PORT", "8090")),
        workers=1,
    )


if __name__ == "__main__":
    main()
