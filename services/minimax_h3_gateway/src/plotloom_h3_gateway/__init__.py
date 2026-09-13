"""Private MiniMax-H3 gateway for the Spark ComfyUI deployment.

The package deliberately exposes a narrow application contract rather than
passing caller-supplied ComfyUI graphs through to the inference service.
"""

from .app import GatewaySettings, create_app

__all__ = ["GatewaySettings", "create_app"]
