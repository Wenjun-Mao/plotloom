"""Compatibility exports for the MiniMax-H3 gateway package.

Runtime responsibilities live in focused modules: HTTP presentation in
``api``, orchestration in ``gateway``, durable records in ``store``, ComfyUI
transport in ``comfy``, and filesystem lifecycle in ``media``.
"""
from .api import create_app
from .contracts import CreateImageJobRequest, CreateTextJobRequest, GatewayError, GatewaySettings
from .gateway import H3Gateway
from .store import GatewayStore

__all__ = [
    "CreateImageJobRequest",
    "CreateTextJobRequest",
    "GatewayError",
    "GatewaySettings",
    "GatewayStore",
    "H3Gateway",
    "create_app",
]
