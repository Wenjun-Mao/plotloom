"""Private MiniMax-H3 gateway for the Spark ComfyUI deployment.

The package deliberately exposes a narrow application contract rather than
passing caller-supplied ComfyUI graphs through to the inference service.
"""

from .contracts import GatewaySettings

__all__ = ["GatewaySettings", "create_app"]


def __getattr__(name):
    # Store/lane imports need only the CPU control plane, not image and HTTP
    # dependencies. Load the application factory only when it is requested.
    if name == "create_app":
        from .api import create_app
        return create_app
    raise AttributeError(name)
