"""Compatibility exports for the shared H3 and Qwen generation gateway.

Runtime responsibilities live in focused modules: HTTP presentation in
``api``, orchestration in ``gateway``, durable records in ``store``, ComfyUI
transport in ``comfy``, and filesystem lifecycle in ``media``.
"""
from .api import create_app
from .contracts import (
    CreateImageJobRequest,
    CreateQwenEditImageJobRequest,
    CreateQwenTextImageJobRequest,
    CreateTextJobRequest,
    GatewayError,
    GatewaySettings,
)
from .gateway import H3Gateway
from .store import GatewayStore

__all__ = [
    "CreateImageJobRequest",
    "CreateQwenEditImageJobRequest",
    "CreateQwenTextImageJobRequest",
    "CreateTextJobRequest",
    "GatewayError",
    "GatewaySettings",
    "GatewayStore",
    "H3Gateway",
    "create_app",
]
