"""Private MiniMax-H3 gateway backend for Plotloom."""

from .adapter import (
    DEFAULT_NEW_H3_PROFILE_ID,
    H3_PROFILES,
    H3_PROFILES_BY_ID,
    LEGACY_H3_PROFILE,
    MINIMAX_H3_480P,
    MiniMaxH3GatewayAdapter,
)
from .transport import MiniMaxH3GatewayTransport

__all__ = [
    "MINIMAX_H3_480P",
    "DEFAULT_NEW_H3_PROFILE_ID",
    "H3_PROFILES",
    "H3_PROFILES_BY_ID",
    "LEGACY_H3_PROFILE",
    "MiniMaxH3GatewayAdapter",
    "MiniMaxH3GatewayTransport",
]
