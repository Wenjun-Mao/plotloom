"""Private MiniMax-H3 gateway backend for Plotloom."""

from .adapter import MINIMAX_H3_480P, MiniMaxH3GatewayAdapter
from .transport import MiniMaxH3GatewayTransport

__all__ = [
    "MINIMAX_H3_480P",
    "MiniMaxH3GatewayAdapter",
    "MiniMaxH3GatewayTransport",
]
